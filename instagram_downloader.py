import os
import re
import json
import logging
import tempfile
import requests
import asyncio
from datetime import datetime
from collections import defaultdict
import yt_dlp
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

def sanitize_text(text: str) -> str:
    """Clean text for Telegram caption"""
    if not text:
        return ""
    
    # Remove excessive whitespace and newlines
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove or replace problematic characters
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove URLs to save space
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    return text.strip()

# Pola URL Instagram
INSTAGRAM_URL_PATTERN = re.compile(
    r'https?://(www\.)?instagram\.com/([a-zA-Z0-9_\.]+/)?([p|reel|stories]/)?([^/?#&]+)'
)

class InstagramDownloader:
    def __init__(self):
        self.download_dir = tempfile.gettempdir()
        
        # yt-dlp configuration for Instagram
        self.ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'http_chunk_size': 10485760,  # 10MB chunks
        }
    
    def is_instagram_url(self, url: str) -> bool:
        """Check if URL is Instagram URL"""
        return bool(INSTAGRAM_URL_PATTERN.match(url))
    
    def extract_post_id(self, url: str) -> Optional[str]:
        """Extract Instagram post ID from URL"""
        match = INSTAGRAM_URL_PATTERN.match(url)
        if match:
            return match.group(4)
        return None
    
    def get_original_filename(self, info_dict, url, index=0):
        """Get appropriate filename from info_dict or URL"""
        # Try to get username if available
        username = None
        if info_dict:
            username = info_dict.get('uploader', info_dict.get('channel', info_dict.get('uploader_id')))
        
        # Get post ID
        post_id = self.extract_post_id(url)
        
        # Try to get upload date
        upload_date = None
        if info_dict and 'upload_date' in info_dict:
            try:
                upload_date = info_dict['upload_date']
                # Format YYYYMMDD to YYYY-MM-DD
                if len(upload_date) == 8:
                    upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            except:
                pass
        
        # Build descriptive filename
        components = []
        if username:
            # Remove invalid characters for filename
            username = re.sub(r'[\\/*?:"<>|]', "", username)
            components.append(username)
        
        if post_id:
            components.append(post_id)
        
        if upload_date:
            components.append(upload_date)
        
        # If there are multiple files in post (e.g., carousel)
        if index > 0:
            components.append(f"part_{index}")
        
        # Join components
        if components:
            return "_".join(components)
        
        # Fallback to current time if no sufficient info
        return f"instagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def download_carousel(self, url: str) -> List[str]:
        """Special function to download Instagram carousel posts"""
        logger.info(f"Starting Instagram carousel download: {url}")
        
        carousel_media_paths = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            image_urls = []
            
            # Try to extract username from page
            username = None
            for meta in soup.find_all('meta', property='og:title'):
                if meta.get('content'):
                    content = meta.get('content')
                    if ' on Instagram' in content:
                        username = content.split(' on Instagram')[0].strip()
                        break
            
            # Extract from JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                script_content = script.string if hasattr(script, 'string') else None
                if script_content:
                    try:
                        data = json.loads(script_content)
                        if isinstance(data, dict) and 'image' in data:
                            if isinstance(data['image'], list):
                                for img in data['image']:
                                    if isinstance(img, str):
                                        image_urls.append(img)
                                    elif isinstance(img, dict) and 'url' in img:
                                        image_urls.append(img['url'])
                            elif isinstance(data['image'], str):
                                image_urls.append(data['image'])
                            
                            # Try to get author if username not found yet
                            if not username and 'author' in data and 'name' in data['author']:
                                username = data['author']['name']
                    except Exception as e:
                        logger.error(f"Error parsing JSON LD: {e}")
            
            # Regex patterns to find media URLs
            carousel_patterns = [
                r'"display_url":"(https:\\\/\\\/[^"]+)"',
                r'"display_resources":\[.*?"src":"(https:\\\/\\\/[^"]+)"',
                r'"carousel_media":\[.*?"url":"(https:\\\/\\\/[^"]+)"',
                r'"image_versions2":\{.*?"url":"(https:\\\/\\\/[^"]+)"'
            ]
            
            # Extract from scripts containing carousel data
            for script in soup.find_all('script'):
                script_content = script.string if hasattr(script, 'string') else None
                if script_content and ('carousel_media' in script_content or 'edge_sidecar_to_children' in script_content):
                    for pattern in carousel_patterns:
                        matches = re.findall(pattern, script_content)
                        for match in matches:
                            clean_url = match.replace('\\u0026', '&').replace('\\/', '/')
                            if clean_url not in image_urls:
                                image_urls.append(clean_url)
            
            # Remove duplicates
            image_urls = list(set(image_urls))
            valid_image_urls = []
            
            # Normalize URLs
            for img_url in image_urls:
                normalized_url = img_url.replace('\\', '')
                if normalized_url.startswith('http'):
                    valid_image_urls.append(normalized_url)
            
            # Get post ID from URL
            post_id = self.extract_post_id(url)
            
            # Download each image
            for i, img_url in enumerate(valid_image_urls):
                # Create filename based on username, post ID, and index
                if username:
                    base_filename = f"{username}_{post_id}_part_{i+1}"
                else:
                    base_filename = f"instagram_{post_id}_part_{i+1}"
                
                # Get file extension from URL
                extension = ".jpg"  # Default extension
                if "." in img_url.split("?")[0].split("/")[-1]:
                    extension = "." + img_url.split("?")[0].split("/")[-1].split(".")[-1]
                    if extension.lower() not in ['.jpg', '.jpeg', '.png', '.mp4', '.webp']:
                        extension = '.jpg'
                
                image_path = os.path.join(self.download_dir, f"{base_filename}{extension}")
                try:
                    image_response = requests.get(img_url, headers=headers, timeout=15)
                    if image_response.status_code == 200:
                        with open(image_path, 'wb') as f:
                            f.write(image_response.content)
                        carousel_media_paths.append(image_path)
                except Exception as e:
                    logger.error(f"Error downloading carousel image {i+1}: {e}")
            
            # If manual method failed, try with yt-dlp
            if not carousel_media_paths:
                logger.info("Manual method failed, trying with yt-dlp...")
                try:
                    # Create filename format with username and post_id
                    if username:
                        output_template = os.path.join(self.download_dir, f'{username}_{post_id}_part_%(autonumber)02d.%(ext)s')
                    else:
                        output_template = os.path.join(self.download_dir, f'instagram_{post_id}_part_%(autonumber)02d.%(ext)s')
                    
                    ydl_opts = {
                        'outtmpl': output_template,
                        'format': 'best',
                        'quiet': False,
                        'noplaylist': False,
                        'extract_flat': False,
                        'ignoreerrors': True,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.extract_info(url, download=True)
                        
                    # Get all files starting with username or instagram_
                    carousel_files = []
                    prefix = f"{username}_{post_id}" if username else f"instagram_{post_id}"
                    for file in os.listdir(self.download_dir):
                        if file.startswith(prefix) and os.path.isfile(os.path.join(self.download_dir, file)):
                            carousel_files.append(file)
                    
                    carousel_files.sort()
                    
                    for file in carousel_files:
                        carousel_media_paths.append(os.path.join(self.download_dir, file))
                except Exception as e:
                    logger.error(f"Error yt-dlp: {e}")
            
            return carousel_media_paths if carousel_media_paths else []
        
        except Exception as e:
            logger.error(f"General carousel error: {e}")
            return []
    
    async def download(self, url: str) -> Dict:
        """Main download method for Instagram content"""
        try:
            # Check if it's carousel/post first
            is_instagram_post = 'instagram.com' in url and '/p/' in url
            
            if is_instagram_post:
                # Try carousel download first
                media_paths = await self.download_carousel(url)
                
                if media_paths:
                    # Try to extract caption from carousel
                    caption_text = ""
                    try:
                        # Try to get info from yt-dlp for caption
                        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                            info = ydl.extract_info(url, download=False)
                            if info and (info.get('description') or info.get('title')):
                                original_caption = info.get('description') or info.get('title') or ''
                                if original_caption:
                                    cleaned_caption = sanitize_text(original_caption)
                                    caption_text = f"<i>{cleaned_caption[:500]}...</i>" if len(cleaned_caption) > 500 else f"<i>{cleaned_caption}</i>"
                    except Exception as e:
                        logger.warning(f"Could not extract caption: {e}")
                    
                    return {
                        "success": True,
                        "type": "carousel",
                        "files": media_paths,
                        "count": len(media_paths),
                        "caption": caption_text
                    }
            
            # Fallback to regular yt-dlp download
            try:
                # Try multiple format configurations
                format_options = [
                    'best[ext=mp4]',
                    'best[height<=720][ext=mp4]',
                    'best[height<=480][ext=mp4]',
                    'best',
                    'worst'
                ]
                
                for format_opt in format_options:
                    try:
                        # Update format option
                        opts = self.ydl_opts.copy()
                        opts['format'] = format_opt
                        
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            # Extract info first
                            info = ydl.extract_info(url, download=False)
                            if not info:
                                continue
                            
                            title = info.get('title', 'Instagram Media')
                            media_id = info.get('id', 'unknown')
                            
                            # Download the media
                            ydl.download([url])
                            
                            # Find the downloaded file
                            expected_filename = ydl.prepare_filename(info)
                            
                            if os.path.exists(expected_filename):
                                file_path = expected_filename
                            else:
                                # Try to find file by pattern
                                for file in os.listdir(self.download_dir):
                                    if media_id in file and (file.endswith('.mp4') or file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.png')):
                                        file_path = os.path.join(self.download_dir, file)
                                        break
                                else:
                                    continue
                            
                            logger.info(f"Downloaded Instagram media with format {format_opt}: {file_path}")
                            
                            # Determine media type
                            media_type = "video" if file_path.endswith(('.mp4', '.mov', '.avi')) else "photo"
                            
                            # Extract caption for single media
                            caption_text = ""
                            if info:
                                original_caption = (
                                    info.get('description') or 
                                    info.get('title') or 
                                    info.get('alt_title') or ''
                                )
                                
                                if original_caption and original_caption.strip():
                                    cleaned_caption = sanitize_text(original_caption.strip())
                                    if len(cleaned_caption) > 300:
                                        cleaned_caption = cleaned_caption[:300] + "..."
                                    caption_text = f"`{cleaned_caption}`"
                            
                            return {
                                "success": True,
                                "type": media_type,
                                "file_path": file_path,
                                "title": title,
                                "caption": caption_text
                            }
                            
                    except yt_dlp.DownloadError as e:
                        logger.warning(f"Format {format_opt} failed: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error with format {format_opt}: {e}")
                        continue
                
                # If all formats failed
                return {"success": False, "error": "Ora iso download Instagram cok! Mungkin private utawa wis dihapus."}
                
            except Exception as e:
                logger.error(f"Error downloading Instagram: {e}")
                return {"success": False, "error": str(e)}
                
        except Exception as e:
            logger.error(f"General Instagram download error: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_downloads(self):
        """Clean up old download files"""
        try:
            for filename in os.listdir(self.download_dir):
                if filename.startswith('instagram_') or 'Instagram' in filename:
                    file_path = os.path.join(self.download_dir, filename)
                    if os.path.isfile(file_path):
                        # Delete files older than 1 hour
                        file_age = os.path.getctime(file_path)
                        import time
                        if (time.time() - file_age) > 3600:
                            os.remove(file_path)
                            logger.info(f"Cleaned up old file: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up downloads: {e}")
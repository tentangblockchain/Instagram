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
    
    text = re.sub(r'\s+', ' ', text.strip())
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    return text.strip()

INSTAGRAM_URL_PATTERN = re.compile(
    r'https?://(www\.)?instagram\.com/([a-zA-Z0-9_\.]+/)?([p|reel|stories]/)?([^/?#&]+)'
)

class InstagramDownloader:
    def __init__(self):
        self.download_dir = tempfile.gettempdir()
        
        # OPTIMIZED yt-dlp configuration
        self.ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'format': 'best',  # Single best format
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'socket_timeout': 10,  # CRITICAL: 10 second timeout
            'retries': 2,  # Max 2 retries
            'fragment_retries': 2,
            'http_chunk_size': 10485760,
            'concurrent_fragment_downloads': 3,  # Parallel downloads
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
    
    def _is_rate_limit_error(self, error_msg: str) -> bool:
        """Detect rate limit or auth errors for fast-fail"""
        rate_limit_indicators = [
            'rate-limit',
            '429',
            'Too Many Requests',
            'login required',
            'not available',
            'Requested content is not available'
        ]
        return any(indicator.lower() in str(error_msg).lower() for indicator in rate_limit_indicators)
    
    async def download_carousel(self, url: str) -> List[str]:
        """Special function to download Instagram carousel posts"""
        logger.info(f"Starting Instagram carousel download: {url}")
        
        carousel_media_paths = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            image_urls = []
            username = None
            
            # Extract username
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
                            
                            if not username and 'author' in data and 'name' in data['author']:
                                username = data['author']['name']
                    except Exception as e:
                        logger.error(f"Error parsing JSON LD: {e}")
            
            # Regex patterns
            carousel_patterns = [
                r'"display_url":"(https:\\\/\\\/[^"]+)"',
                r'"display_resources":\[.*?"src":"(https:\\\/\\\/[^"]+)"',
            ]
            
            for script in soup.find_all('script'):
                script_content = script.string if hasattr(script, 'string') else None
                if script_content and 'carousel_media' in script_content:
                    for pattern in carousel_patterns:
                        matches = re.findall(pattern, script_content)
                        for match in matches:
                            clean_url = match.replace('\\u0026', '&').replace('\\/', '/')
                            if clean_url not in image_urls:
                                image_urls.append(clean_url)
            
            # Remove duplicates and normalize
            image_urls = list(set(image_urls))
            valid_image_urls = [img_url.replace('\\', '') for img_url in image_urls if img_url.replace('\\', '').startswith('http')]
            
            post_id = self.extract_post_id(url)
            
            # Download each image
            for i, img_url in enumerate(valid_image_urls):
                base_filename = f"{username}_{post_id}_part_{i+1}" if username else f"instagram_{post_id}_part_{i+1}"
                extension = ".jpg"
                
                if "." in img_url.split("?")[0].split("/")[-1]:
                    ext = "." + img_url.split("?")[0].split("/")[-1].split(".")[-1]
                    if ext.lower() in ['.jpg', '.jpeg', '.png', '.mp4', '.webp']:
                        extension = ext
                
                image_path = os.path.join(self.download_dir, f"{base_filename}{extension}")
                try:
                    image_response = requests.get(img_url, headers=headers, timeout=10)
                    if image_response.status_code == 200:
                        with open(image_path, 'wb') as f:
                            f.write(image_response.content)
                        carousel_media_paths.append(image_path)
                except Exception as e:
                    logger.error(f"Error downloading carousel image {i+1}: {e}")
            
            return carousel_media_paths if carousel_media_paths else []
        
        except Exception as e:
            logger.error(f"General carousel error: {e}")
            return []
    
    async def download(self, url: str) -> Dict:
        """OPTIMIZED main download method for Instagram content"""
        try:
            # Check if it's carousel/post first
            is_instagram_post = 'instagram.com' in url and '/p/' in url
            
            if is_instagram_post:
                # Try carousel download first
                media_paths = await self.download_carousel(url)
                
                if media_paths:
                    caption_text = ""
                    try:
                        with yt_dlp.YoutubeDL({'quiet': True, 'socket_timeout': 5}) as ydl:
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
            
            # OPTIMIZED: Try only ONE best format with fast-fail
            try:
                opts = self.ydl_opts.copy()
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    # Extract info first
                    try:
                        info = ydl.extract_info(url, download=False)
                    except yt_dlp.DownloadError as e:
                        error_msg = str(e)
                        # FAST-FAIL: Check for rate limit immediately
                        if self._is_rate_limit_error(error_msg):
                            logger.warning(f"Instagram rate limit detected, failing fast")
                            return {
                                "success": False, 
                                "error": "Instagram lagi rate-limit. Tunggu 30-60 menit atau gunakan link lain."
                            }
                        raise
                    
                    if not info:
                        return {"success": False, "error": "Ora iso extract info dari Instagram."}
                    
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
                            if media_id in file and file.endswith(('.mp4', '.jpg', '.jpeg', '.png')):
                                file_path = os.path.join(self.download_dir, file)
                                break
                        else:
                            return {"success": False, "error": "File download ora ketemu."}
                    
                    logger.info(f"Downloaded Instagram media: {file_path}")
                    
                    # Determine media type
                    media_type = "video" if file_path.endswith(('.mp4', '.mov', '.avi')) else "photo"
                    
                    # Extract caption
                    caption_text = ""
                    if info:
                        original_caption = info.get('description') or info.get('title') or info.get('alt_title') or ''
                        
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
                error_msg = str(e)
                if self._is_rate_limit_error(error_msg):
                    return {
                        "success": False,
                        "error": "Instagram rate-limit. Coba lagi 30-60 menit atau pake link lain."
                    }
                logger.error(f"yt-dlp error: {e}")
                return {"success": False, "error": "Ora iso download Instagram. Mungkin private atau dihapus."}
            except Exception as e:
                logger.error(f"Error downloading Instagram: {e}")
                return {"success": False, "error": str(e)}
                
        except Exception as e:
            logger.error(f"General Instagram download error: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_downloads(self):
        """Clean up old download files"""
        try:
            import time
            for filename in os.listdir(self.download_dir):
                if filename.startswith('instagram_') or 'Instagram' in filename:
                    file_path = os.path.join(self.download_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = os.path.getctime(file_path)
                        if (time.time() - file_age) > 3600:
                            os.remove(file_path)
                            logger.info(f"Cleaned up old file: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up downloads: {e}")

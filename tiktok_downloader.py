import os
import requests
import yt_dlp
import logging
import tempfile
import re
import time
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs

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

class TikTokDownloader:
    def __init__(self):
        self.download_dir = tempfile.gettempdir()
        
        # yt-dlp configuration for TikTok videos
        self.ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'format': 'best',  # Use best available format
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'http_chunk_size': 10485760,  # 10MB chunks for better download
        }
    
    def is_photo_url(self, url: str) -> bool:
        """Check if TikTok URL is a photo/slideshow"""
        return '/photo/' in url or 'photo' in url.lower()
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL"""
        patterns = [
            r'/video/(\d+)',
            r'/photo/(\d+)', 
            r'@[\w.-]+/video/(\d+)',
            r'@[\w.-]+/photo/(\d+)',
            r'/v/(\d+)',
            r'vm\.tiktok\.com/(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def download_photo(self, url: str) -> Dict:
        """Download TikTok photo using oEmbed API"""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return {"success": False, "error": "Ora iso extract video ID"}
            
            # Convert photo URL to video URL for oEmbed
            if '/photo/' in url:
                # Extract username and video ID
                username_match = re.search(r'@([\w.-]+)', url)
                if username_match:
                    username = username_match.group(1)
                    oembed_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                else:
                    oembed_url = url.replace('/photo/', '/video/')
            else:
                oembed_url = url
            
            # Get oEmbed data
            oembed_api_url = f"https://www.tiktok.com/oembed?url={oembed_url}"
            
            response = requests.get(oembed_api_url, timeout=10)
            response.raise_for_status()
            
            oembed_data = response.json()
            
            # Extract thumbnail URL
            thumbnail_url = oembed_data.get('thumbnail_url')
            if not thumbnail_url:
                return {"success": False, "error": "Ora ketemu thumbnail URL"}
            
            # Download the image
            img_response = requests.get(thumbnail_url, timeout=30)
            img_response.raise_for_status()
            
            # Save to temporary file
            filename = f"tiktok_photo_{video_id}.jpg"
            file_path = os.path.join(self.download_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(img_response.content)
            
            logger.info(f"Downloaded TikTok photo: {file_path}")
            
            # Try to extract caption from oembed title
            caption_text = ""
            if oembed_data.get('title'):
                original_caption = oembed_data.get('title', '')
                if original_caption and original_caption.strip():
                    cleaned_caption = sanitize_text(original_caption.strip())
                    if len(cleaned_caption) > 300:
                        cleaned_caption = cleaned_caption[:300] + "..."
                    caption_text = f"`{cleaned_caption}`"
            
            return {
                "success": True,
                "type": "photo",
                "file_path": file_path,
                "title": oembed_data.get('author_name', 'TikTok Photo'),
                "caption": caption_text
            }
            
        except requests.RequestException as e:
            logger.error(f"Network error downloading photo: {e}")
            return {"success": False, "error": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error downloading photo: {e}")
            return {"success": False, "error": str(e)}
    
    async def download_video(self, url: str) -> Dict:
        """Download TikTok video using yt-dlp with fallback formats"""
        
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
                    
                    title = info.get('title', 'TikTok Video')
                    video_id = info.get('id', 'unknown')
                    
                    # Download the video
                    ydl.download([url])
                    
                    # Find the downloaded file
                    expected_filename = ydl.prepare_filename(info)
                    
                    if os.path.exists(expected_filename):
                        file_path = expected_filename
                    else:
                        # Try to find file by pattern
                        for file in os.listdir(self.download_dir):
                            if video_id in file and (file.endswith('.mp4') or file.endswith('.webm') or file.endswith('.mov')):
                                file_path = os.path.join(self.download_dir, file)
                                break
                        else:
                            continue
                    
                    logger.info(f"Downloaded TikTok video with format {format_opt}: {file_path}")
                    
                    # Extract caption for TikTok video
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
                        "type": "video",
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
        
        # If all formats failed, return error
        return {"success": False, "error": "Ora iso download video cok! TikTok-e mungkin wis dihapus utawa diblokir."}
    
    def resolve_url(self, url: str) -> str:
        """Resolve shortened TikTok URLs"""
        try:
            if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
                resolved_url = response.url
                logger.info(f"Resolved short URL: {url} -> {resolved_url}")
                return resolved_url
            return url
        except Exception as e:
            logger.error(f"Error resolving URL: {e}")
            return url
    
    async def download(self, url: str) -> Dict:
        """Main download method - determines type and downloads accordingly"""
        try:
            logger.info(f"Starting TikTok download: {url}")
            
            # Resolve shortened URLs first
            resolved_url = self.resolve_url(url)
            logger.info(f"Using URL for download: {resolved_url}")
            
            # If resolution failed for short URLs, try alternative method
            if ('vm.tiktok.com' in url or 'vt.tiktok.com' in url) and resolved_url == url:
                logger.warning(f"URL resolution failed, trying alternative headers")
                try:
                    alt_headers = {
                        'User-Agent': 'TikTok 26.2.0 rv:262018 (iPhone; iOS 14.4.2; en_US) Cronet',
                        'Accept': '*/*',
                        'Accept-Language': 'en-US,en;q=0.9',
                    }
                    session = requests.Session()
                    session.headers.update(alt_headers)
                    resp = session.get(url, allow_redirects=True, timeout=15)
                    if resp.url != url:
                        resolved_url = resp.url
                        logger.info(f"Alternative resolution successful: {resolved_url}")
                    else:
                        logger.warning(f"Could not resolve short URL, attempting direct download")
                except Exception as alt_error:
                    logger.error(f"Alternative resolution failed: {alt_error}")
            
            # Determine if it's photo or video
            if self.is_photo_url(resolved_url):
                return await self.download_photo(resolved_url)
            else:
                return await self.download_video(resolved_url)
                
        except Exception as e:
            logger.error(f"General download error: {e}")
            return {"success": False, "error": f"Ora iso download TikTok cok! Error: {str(e)}"}
    
    def cleanup_downloads(self):
        """Clean up old download files"""
        try:
            for filename in os.listdir(self.download_dir):
                if filename.startswith('tiktok_') or 'TikTok' in filename:
                    file_path = os.path.join(self.download_dir, filename)
                    if os.path.isfile(file_path):
                        # Delete files older than 1 hour
                        file_age = os.path.getctime(file_path)
                        if (time.time() - file_age) > 3600:
                            os.remove(file_path)
                            logger.info(f"Cleaned up old file: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up downloads: {e}")

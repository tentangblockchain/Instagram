import os
import requests
import yt_dlp
import logging
import tempfile
import re
import time
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs
from ..utils import sanitize_text

logger = logging.getLogger(__name__)

class TikTokDownloader:
    def __init__(self):
        # dedicated subfolder for TikTok downloads
        self.download_dir = os.path.join(tempfile.gettempdir(), "jawanese_bot_tiktok")
        os.makedirs(self.download_dir, exist_ok=True)

        # OPTIMIZED yt-dlp configuration
        self.ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'socket_timeout': 10,  # CRITICAL: 10 second timeout
            'retries': 2,  # Max 2 retries
            'fragment_retries': 2,
            'http_chunk_size': 10485760,
            'postprocessor_args': [
                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1',
                '-pix_fmt', 'yuv420p',
                '-c:v', 'libx264',
                '-profile:v', 'main',
                '-movflags', '+faststart',
            ],
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

    def _is_fatal_error(self, error_msg: str) -> bool:
        """Detect fatal errors that shouldn't retry multiple formats"""
        fatal_indicators = [
            'Unsupported URL',
            'not found',
            'removed',
            'deleted',
            'private',
            'unavailable'
        ]
        return any(indicator.lower() in str(error_msg).lower() for indicator in fatal_indicators)

    async def download_photo(self, url: str) -> Dict:
        """Download TikTok photo using oEmbed API"""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return {"success": False, "error": "Ora iso extract video ID"}

            # Convert photo URL to video URL for oEmbed
            if '/photo/' in url:
                username_match = re.search(r'@([\w.-]+)', url)
                if username_match:
                    username = username_match.group(1)
                    oembed_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                else:
                    oembed_url = url.replace('/photo/', '/video/')
            else:
                oembed_url = url

            # Get oEmbed data with timeout
            oembed_api_url = f"https://www.tiktok.com/oembed?url={oembed_url}"
            response = requests.get(oembed_api_url, timeout=10)
            response.raise_for_status()

            oembed_data = response.json()
            thumbnail_url = oembed_data.get('thumbnail_url')

            if not thumbnail_url:
                return {"success": False, "error": "Ora ketemu thumbnail URL"}

            # Download the image with timeout
            img_response = requests.get(thumbnail_url, timeout=15)
            img_response.raise_for_status()

            # Save to temporary file
            filename = f"tiktok_photo_{video_id}.jpg"
            file_path = os.path.join(self.download_dir, filename)

            with open(file_path, 'wb') as f:
                f.write(img_response.content)

            logger.info(f"Downloaded TikTok photo: {file_path}")

            # Extract caption
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

    async def _download_via_tikwm(self, url: str) -> Optional[Dict]:
        """Fallback: download TikTok via tikwm API when yt-dlp fails"""
        try:
            logger.info(f"Trying tikwm API fallback for: {url}")
            api_url = f"https://www.tikwm.com/api/?url={url}"
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get('code') != 0:
                logger.warning(f"tikwm API error: {data}")
                return None

            video_data = data['data']
            video_url = video_data.get('hdplay') or video_data.get('play')
            if not video_url:
                return None

            title = video_data.get('title', 'TikTok Video')
            video_id = str(video_data.get('id', 'unknown'))

            # Download video file
            filename = f"tiktok_{video_id}.mp4"
            file_path = os.path.join(self.download_dir, filename)

            vid_resp = requests.get(video_url, timeout=30, stream=True)
            vid_resp.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in vid_resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            if not self._validate_video_file(file_path):
                os.remove(file_path)
                return None

            logger.info(f"tikwm download success: {file_path}")

            caption_text = ""
            if title and title.strip():
                cleaned = sanitize_text(title.strip())
                if len(cleaned) > 300:
                    cleaned = cleaned[:300] + "..."
                caption_text = f"`{cleaned}`"

            return {
                "success": True,
                "type": "video",
                "file_path": file_path,
                "title": title,
                "caption": caption_text
            }
        except Exception as e:
            logger.error(f"tikwm fallback error: {e}")
            return None

    async def download_video(self, url: str) -> Dict:
        """OPTIMIZED: Download TikTok video using yt-dlp with tikwm API fallback"""

        try:
            # --- Step 1: Try yt-dlp ---
            file_path = None
            title = 'TikTok Video'
            video_id = 'unknown'
            caption_text = ""

            try:
                opts = self.ydl_opts.copy()
                with yt_dlp.YoutubeDL(opts) as ydl:
                    try:
                        info = ydl.extract_info(url, download=False)
                    except yt_dlp.DownloadError as e:
                        error_msg = str(e)
                        if self._is_fatal_error(error_msg):
                            logger.warning(f"Fatal TikTok error detected: {error_msg}")
                            return {"success": False, "error": "TikTok video wis dihapus, private, atau link salah."}
                        raise

                    if not info:
                        raise Exception("No info extracted")

                    title = info.get('title', 'TikTok Video')
                    video_id = info.get('id', 'unknown')

                    ydl.download([url])

                    expected_filename = ydl.prepare_filename(info)
                    if os.path.exists(expected_filename):
                        file_path = expected_filename
                    else:
                        for file in os.listdir(self.download_dir):
                            if video_id in file and file.endswith(('.mp4', '.webm', '.mov')):
                                file_path = os.path.join(self.download_dir, file)
                                break

                    # Validate video stream exists
                    if file_path and not self._validate_video_file(file_path):
                        os.remove(file_path)
                        file_path = None

                    # Extract caption
                    if info:
                        original_caption = info.get('description') or info.get('title') or info.get('alt_title') or ''
                        if original_caption and original_caption.strip():
                            cleaned_caption = sanitize_text(original_caption.strip())
                            if len(cleaned_caption) > 300:
                                cleaned_caption = cleaned_caption[:300] + "..."
                            caption_text = f"`{cleaned_caption}`"

            except Exception as e:
                logger.warning(f"yt-dlp failed: {e}, trying tikwm API")

            # --- Step 2: Fallback to tikwm API ---
            if not file_path:
                result = await self._download_via_tikwm(url)
                if result and result.get('success'):
                    return result
                return {"success": False, "error": "Ora iso download TikTok video."}

            logger.info(f"Downloaded TikTok video: {file_path}")
            return {
                "success": True,
                "type": "video",
                "file_path": file_path,
                "title": title,
                "caption": caption_text
            }

        except Exception as e:
            logger.error(f"TikTok download error: {e}")
            return {
                "success": False,
                "error": f"Maaf kak, ada kendala saat download: {str(e)}"
            }

    def _validate_video_file(self, file_path: str) -> bool:
        """Check if downloaded file actually has video stream (not audio-only)"""
        try:
            import subprocess
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', file_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return True  # ffprobe failed, assume OK
            import json
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            has_video = any(s.get('codec_type') == 'video' for s in streams)
            has_audio = any(s.get('codec_type') == 'audio' for s in streams)
            if not has_video:
                logger.warning(f"No video stream found in {file_path} (audio-only)")
                return False
            if not has_audio:
                logger.warning(f"No audio stream found in {file_path} (video-only), still OK")
            return True
        except Exception as e:
            logger.debug(f"Validation check skipped: {e}")
            return True  # skip validation on error

    def resolve_url(self, url: str) -> str:
        """Resolve shortened TikTok URLs with optimized timeout"""
        try:
            if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
                resolved_url = response.url
                logger.info(f"Resolved short URL: {url} -> {resolved_url}")
                return resolved_url
            return url
        except Exception as e:
            logger.error(f"Error resolving URL: {e}")
            return url

    async def download(self, url: str) -> Dict:
        """OPTIMIZED main download method"""
        try:
            logger.info(f"Starting TikTok download: {url}")

            # Resolve shortened URLs first
            resolved_url = self.resolve_url(url)
            logger.info(f"Using URL for download: {resolved_url}")

            # FAST-FAIL: Check if resolution failed to notfound page
            # NOTE: don't fail just because resolve_url returned the same short URL —
            # yt-dlp can handle short URLs directly, so only fail on explicit notfound.
            if 'notfound' in resolved_url.lower():
                logger.warning(f"URL resolved to notfound page")
                return {"success": False, "error": "Link TikTok salah, wis dihapus, atau expired."}

            # Determine if it's photo or video
            if self.is_photo_url(resolved_url):
                return await self.download_photo(resolved_url)
            else:
                return await self.download_video(resolved_url)

        except Exception as e:
            logger.error(f"General download error: {e}")
            return {"success": False, "error": f"Ora iso download TikTok. Error: {str(e)}"}

    def cleanup_downloads(self):
        """Clean up old download files (remove anything in our subfolder older than an hour)"""
        try:
            import time
            for filename in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, filename)
                if os.path.isfile(file_path):
                    file_age = os.path.getctime(file_path)
                    if (time.time() - file_age) > 3600:
                        try:
                            os.remove(file_path)
                            logger.info(f"Cleaned up old file: {filename}")
                        except Exception as ee:
                            logger.error(f"Failed to remove {file_path}: {ee}")
        except Exception as e:
            logger.error(f"Error cleaning up downloads: {e}")

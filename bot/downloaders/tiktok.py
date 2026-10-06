import os
import requests
import yt_dlp
import logging
import tempfile
import re
import time
import html as html_lib
import threading
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs, quote_plus
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..utils import sanitize_text

logger = logging.getLogger(__name__)

# --- TikTok rate-limit handling -------------------------------------------------
# TikTok memblokir IP dengan HTTP 429 pada endpoint oEmbed. Memakai response
# acak tanpa User-Agent membuat pola Picking-Bot gampang di-fingerprint, dan
# retry buta tanpa jeda memperpanjang ban. Solusinya: satu Session dengan UA
# browser + retry backoff yang menghormati Retry-After, lalu cooldown global
# supaya request berikutnya langsung ditolak dengan pesan jelas (bukan retry
# sia-sia yang memperpanjang ban).
_TIKTOK_COOLDOWN_SECONDS = 300  # 5 menit
_tiktok_cooldown_until = 0.0
_cooldown_lock = threading.Lock()

_BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.tiktok.com/',
}


class TikTokRateLimited(Exception):
    """TikTok membalas 429 — IP kita sedang di rate-limit."""


def _cooldown_remaining() -> int:
    """Sisa cooldown dalam detik (0 = boleh request)."""
    global _tiktok_cooldown_until
    with _cooldown_lock:
        remaining = _tiktok_cooldown_until - time.time()
        return int(remaining) if remaining > 0 else 0


def _trigger_cooldown(seconds: int = _TIKTOK_COOLDOWN_SECONDS) -> None:
    global _tiktok_cooldown_until
    with _cooldown_lock:
        _tiktok_cooldown_until = time.time() + seconds


def _clear_cooldown() -> None:
    global _tiktok_cooldown_until
    with _cooldown_lock:
        _tiktok_cooldown_until = 0.0


class TikTokDownloader:
    def __init__(self):
        # dedicated subfolder for TikTok downloads
        self.download_dir = os.path.join(tempfile.gettempdir(), "jawanese_bot_tiktok")
        os.makedirs(self.download_dir, exist_ok=True)

        # Shared Session: UA + retry backoff. Satu session dipakai untuk semua
        # request TikTok supaya tidak terlihat seperti robot yang bikin koneksi
        # baru tiap panggilan. raise_on_status=False → response 429 dikembalikan
        # (bukan exception) supaya kita yang memutuskan handler-nya.
        self.session = requests.Session()
        self.session.headers.update(_BROWSER_HEADERS)
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD"]),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

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

    # --- Rate-limit aware HTTP helpers -------------------------------------------

    def _ensure_not_cooling_down(self) -> None:
        """Tolak request baru saat masih cooldown — jangan retry sia-sia."""
        remaining = _cooldown_remaining()
        if remaining > 0:
            raise TikTokRateLimited(
                f"TikTok sedang rate-limit. Coba lagi dalam {remaining} detik."
            )

    @staticmethod
    def _retry_after_seconds(response, cap: int = _TIKTOK_COOLDOWN_SECONDS) -> int:
        """Baca header Retry-After kalau ada, else pakai default cooldown."""
        header = (response.headers.get('Retry-After') or '').strip()
        if header.isdigit():
            return max(1, min(int(header), cap))
        return _TIKTOK_COOLDOWN_SECONDS

    def _tiktok_get(self, url: str, *, timeout: int = 10, stream: bool = False,
                    check: bool = True, bypass_cooldown: bool = False):
        """GET lewat shared session; 429 → cooldown + exception, bukan error kabur.

        ``bypass_cooldown`` dipakai HANYA oleh fallback HTML: endpoint halaman
        berbeda dari oEmbed, jadi layak satu percobaan meski oEmbed kena 429 —
        tanpa ini, cooldown baru aktif akan memblokir fallback-nya sendiri.
        """
        if not bypass_cooldown:
            self._ensure_not_cooling_down()
        try:
            response = self.session.get(url, timeout=timeout, stream=stream)
        except requests.RequestException as e:
            logger.error(f"Network error GET {url[:80]}: {e}")
            raise
        if response.status_code == 429:
            cooldown = self._retry_after_seconds(response)
            _trigger_cooldown(cooldown)
            logger.warning(
                f"TikTok 429 (rate limit) — cooldown {cooldown} detik setelah {url[:80]}"
            )
            raise TikTokRateLimited(
                f"TikTok sedang rate-limit. Coba lagi dalam {cooldown} detik."
            )
        if check:
            response.raise_for_status()
        return response

    # --- Fallback: ambil thumbnail dari HTML halaman ----------------------------

    @staticmethod
    def _extract_thumbnail_from_html(page_html: str) -> Optional[str]:
        """TikTok sering memblokir oEmbed tapi masih melayani HTML halaman.
        Ambil URL gambar pertama yang muncul di markup."""
        if not page_html:
            return None
        # Normalisasi escape dulu: JSON di dalam <script> sering ditulis
        # "https:\/\/p16.tiktokcdn.com\/a.jpg" atau \u002F. Tanpa ini semua
        # pola di bawah gagal karena regex-nya cari "//" literal.
        normalized = page_html.replace('\\u002F', '/').replace('\\/', '/')
        for pattern in (
            r'<img[^>]+src="(https://[^"]*tiktokcdn[^"]*?\.(?:jpe?g|png|webp)[^"]*)"',
            r'<img[^>]+src="(https://[^"]*tiktokcdn[^"]*?)"',
            r'"displayImage"\s*:\s*"(https://[^"]+)"',
            r'"cover"\s*:\s*"(https://[^"]+)"',
            r'"thumbnail"\s*:\s*"(https://[^"]+)"',
        ):
            match = re.search(pattern, normalized)
            if match:
                return html_lib.unescape(match.group(1))
        # fallback terakhir: srcset berisi beberapa ukuran
        match = re.search(r'srcset="(https://[^"]+?\.(?:jpe?g|png|webp)[^"]*)"', normalized)
        if match:
            return html_lib.unescape(match.group(1))
        return None

    def _fetch_photo_via_tikwm(self, url: str) -> Optional[Dict]:
        """Jalur kedua untuk FOTO: TikTok memblokir oEmbed (429) dari IP datacenter,
        dan halaman HTML-nya tidak menyertakan data konten (itemStruct/playAddr/
        imagePost kosong), jadi scrape HTML tidak berguna. tikwm.com tetap melayani
        request dan mengembalikan URL foto asli di `data.images[]`.

        yt-dlp juga tidak mendukung URL /photo/ ("Unsupported URL"), jadi untuk foto
        inilah satu-satunya jalur yang benar-benar hidup.
        """
        try:
            api_url = f"https://www.tikwm.com/api/?url={quote_plus(url)}"
            logger.info(f"Trying tikwm photo fallback: {url[:70]}")
            resp = self.session.get(api_url, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            if data.get('code') != 0:
                logger.warning(
                    f"tikwm photo API error: code={data.get('code')} msg={str(data.get('msg'))[:80]}"
                )
                return None

            payload = data.get('data') or {}
            images = payload.get('images') or []
            if not images:
                # Beberapa konten hanya punya cover/origin_cover
                for key in ('origin_cover', 'cover'):
                    candidate = payload.get(key)
                    if candidate:
                        images = [candidate]
                        break
            if not images:
                logger.warning("tikwm tidak mengembalikan images[] (foto?)")
                return None

            img_url = images[0]
            img_response = self.session.get(img_url, timeout=20)
            img_response.raise_for_status()
            content_type = img_response.headers.get('Content-Type', '')
            if 'image' not in content_type.lower():
                logger.warning(f"tikwm image bukan gambar (Content-Type: {content_type})")
                return None

            title = payload.get('title') or payload.get('author_name') or 'TikTok Photo'
            return {
                'content': img_response.content,
                'title': title,
                'caption': payload.get('content_desc') or payload.get('title') or '',
                'source': 'tikwm',
            }
        except Exception as e:
            logger.warning(f"tikwm photo fallback gagal: {e}")
            return None

    def _fetch_photo_via_page(self, oembed_url: str, page_url: str) -> Optional[Dict]:
        """Cadangan terakhir: scrape thumbnail dari HTML halaman.

        Catatan: dari IP datacenter TikTok sering menyajikan halaman shell tanpa
        data konten, jadi ini LAZY gagal. Dipakai hanya setelah tikwm gagal.
        """
        candidates = [oembed_url.replace('/video/', '/photo/'), page_url, oembed_url]
        for candidate in dict.fromkeys(candidates):
            try:
                logger.info(f"Trying HTML thumbnail fallback: {candidate[:80]}")
                # bypass_cooldown=True: halaman bukan oEmbed, satu percobaan
                # tetap bernilai walau oEmbed baru saja kena 429.
                response = self._tiktok_get(candidate, timeout=12, bypass_cooldown=True)
                thumb = self._extract_thumbnail_from_html(response.text)
                if not thumb:
                    continue
                img_response = self._tiktok_get(thumb, timeout=15, bypass_cooldown=True)
                content_type = img_response.headers.get('Content-Type', '')
                if 'image' not in content_type.lower():
                    logger.warning(f"Fallback bukan gambar (Content-Type: {content_type})")
                    continue
                return {'content': img_response.content, 'source_url': thumb}
            except TikTokRateLimited:
                raise
            except requests.RequestException as e:
                logger.warning(f"Fallback HTML gagal untuk {candidate[:60]}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Fallback HTML error untuk {candidate[:60]}: {e}")
                continue
        return None

    async def download_photo(self, url: str) -> Dict:
        """Download TikTok photo: oEmbed dulu, fallback scrape HTML saat 429."""
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

            # Get oEmbed data with timeout (session + backoff + 429 handling).
            # Kalau cooldown masih aktif, LEWATI oEmbed sama sekali — request itu
            # pasti 429 dan hanya membuang ~10 detik. Langsung ke fallback.
            oembed_api_url = f"https://www.tiktok.com/oembed?url={oembed_url}"
            oembed_data = None
            skip_oembed = _cooldown_remaining() > 0
            if skip_oembed:
                logger.info(
                    f"Cooldown TikTok aktif — skip oEmbed, langsung ke fallback "
                    f"(sisa {_cooldown_remaining()} detik)"
                )
            else:
                try:
                    response = self._tiktok_get(oembed_api_url, timeout=10)
                    oembed_data = response.json()
                    _clear_cooldown()
                except TikTokRateLimited:
                    oembed_data = None
                except ValueError as e:
                    logger.warning(f"oEmbed balas bukan JSON: {e}")
                    oembed_data = None

            thumbnail_url = oembed_data.get('thumbnail_url') if oembed_data else None
            img_content = None
            meta_source = 'oembed'
            fallback_title = None
            fallback_caption = None

            if thumbnail_url:
                # Download the image with timeout
                img_response = self._tiktok_get(thumbnail_url, timeout=15)
                img_content = img_response.content
            else:
                # oEmbed kena 429 / tidak ada thumbnail → tikwm (jalur yang hidup
                # untuk foto; HTML TikTok dari IP datacenter tidak berisi data).
                logger.warning("oEmbed tidak ada thumbnail — coba fallback tikwm")
                fallback = self._fetch_photo_via_tikwm(url)
                if fallback:
                    img_content = fallback['content']
                    meta_source = fallback.get('source', 'tikwm')
                    fallback_title = fallback.get('title')
                    fallback_caption = fallback.get('caption')
                else:
                    logger.warning("tikwm gagal — coba fallback HTML (scope terbatas)")
                    html_fallback = self._fetch_photo_via_page(oembed_url, url)
                    if html_fallback:
                        img_content = html_fallback['content']
                        meta_source = 'html'

            if not img_content:
                remaining = _cooldown_remaining()
                if remaining > 0:
                    return {
                        "success": False,
                        "error": (
                            f"TikTok sedang rate-limit. Coba lagi dalam {remaining} detik."
                        )
                    }
                return {"success": False, "error": "Ora ketemu thumbnail URL"}

            # Save to temporary file
            filename = f"tiktok_photo_{video_id}.jpg"
            file_path = os.path.join(self.download_dir, filename)

            with open(file_path, 'wb') as f:
                f.write(img_content)

            logger.info(f"Downloaded TikTok photo: {file_path}")

            # Extract caption
            caption_text = ""
            raw_caption = (oembed_data or {}).get('title') if oembed_data else None
            if not raw_caption and meta_source == 'tikwm':
                raw_caption = fallback_caption
            if raw_caption and raw_caption.strip():
                cleaned_caption = sanitize_text(raw_caption.strip())
                if len(cleaned_caption) > 300:
                    cleaned_caption = cleaned_caption[:300] + "..."
                caption_text = f"`{cleaned_caption}`"

            title_value = (oembed_data or {}).get('author_name')
            if not title_value and meta_source == 'tikwm':
                title_value = fallback_title

            return {
                "success": True,
                "type": "photo",
                "file_path": file_path,
                "title": title_value or 'TikTok Photo',
                "caption": caption_text,
                "source": meta_source
            }

        except TikTokRateLimited as e:
            return {"success": False, "error": str(e)}
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
            # tikwm = domain pihak ketiga; 429 di sini milik rate limit tikwm,
            # jadi pakai session tapi TANPA cooldown TikTok (authorship berbeda).
            resp = self.session.get(api_url, timeout=15)
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

            vid_resp = self.session.get(video_url, timeout=30, stream=True)
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
        """Resolve shortened TikTok URLs dengan session + UA browser"""
        try:
            if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
                # Pakai session yang sama (UA + retry) supaya resolve dan download
                # terlihat sebagai satu klien konsisten, bukan request tanpa UA.
                response = self.session.get(url, allow_redirects=True, timeout=10)
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

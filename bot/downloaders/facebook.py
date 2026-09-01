import os
import re
import json
import logging
import tempfile
import asyncio
from typing import Dict, List, Optional
import yt_dlp
import requests

logger = logging.getLogger(__name__)

# Pattern untuk semua link facebook yang bisa di-download
FACEBOOK_URL_PATTERN = re.compile(
    r'https?://(?:www\.|m\.|web\.)?(?:facebook\.com|fb\.com|fb\.watch)/\S+',
    re.IGNORECASE
)

# Pattern khusus untuk profile reels_tab
PROFILE_REELS_PATTERN = re.compile(
    r'https?://(?:www\.|m\.)?facebook\.com/(?:people/[^/]+/\d+|[^/]+|profile\.php\?id=\d+).*[\?&]sk=reels_tab',
    re.IGNORECASE
)

# Pattern untuk extract ID reel tunggal
REEL_ID_PATTERNS = [
    r'/reel/(\d+)',
    r'/watch/?\?v=(\d+)',
    r'/videos/(\d+)',
    r'/share/r/([^/?#&]+)',
    r'/share/v/([^/?#&]+)',
    r'fb\.watch/([^/?#&]+)',
    r'story\.php\?story_fbid=(\d+)',
]


class FacebookDownloader:
    def __init__(self, cookies_path: str = ""):
        self.download_dir = os.path.join(tempfile.gettempdir(), "jawanese_bot_facebook")
        os.makedirs(self.download_dir, exist_ok=True)
        self.cookies_path = cookies_path if cookies_path and os.path.exists(cookies_path) else ""

        self.ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 15,
            'retries': 2,
            'fragment_retries': 2,
            'http_chunk_size': 10485760,
            'concurrent_fragment_downloads': 3,
            'postprocessor_args': [
                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1',
                '-pix_fmt', 'yuv420p',
                '-c:v', 'libx264',
                '-profile:v', 'main',
                '-movflags', '+faststart',
            ],
        }
        if self.cookies_path:
            self.ydl_opts['cookiefile'] = self.cookies_path

        self._browser = None
        self._page = None
        self._pw = None

    def is_facebook_url(self, url: str) -> bool:
        return bool(FACEBOOK_URL_PATTERN.search(url))

    def is_profile_reels_url(self, url: str) -> bool:
        return bool(PROFILE_REELS_PATTERN.search(url)) or 'sk=reels_tab' in url

    def extract_reel_id(self, url: str) -> Optional[str]:
        for pat in REEL_ID_PATTERNS:
            m = re.search(pat, url)
            if m:
                return m.group(1)
        return None

    # ── Playwright tanpa Docker ────────────────────────────────
    async def _ensure_browser(self):
        if self._page:
            try:
                await self._page.evaluate("1")
                return
            except Exception:
                pass
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("playwright belum terinstall: pip install playwright")

        self._pw = await async_playwright().start()
        chromium = self._pw.chromium

        # Replit sudah provide chromium via env
        executable = os.getenv("REPLIT_PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        launch_kwargs = dict(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
        )
        if executable and os.path.exists(executable):
            launch_kwargs['executable_path'] = executable

        self._browser = await chromium.launch(**launch_kwargs)
        context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'
        )
        # Inject cookies Facebook jika ada (netscape format)
        if self.cookies_path and os.path.exists(self.cookies_path):
            try:
                cookies = self._parse_netscape_cookies(self.cookies_path)
                if cookies:
                    await context.add_cookies(cookies)
                    logger.info(f"Injected {len(cookies)} Facebook cookies ke Playwright")
            except Exception as e:
                logger.warning(f"Gagal inject cookies: {e}")
        self._page = await context.new_page()

    async def scrape_profile_reels(self, profile_url: str, max_reels: int = 20) -> List[str]:
        """
        Scrape semua link reel dari halaman profile ?sk=reels_tab
        Tanpa Docker - pakai Playwright langsung (pengganti FlareSolverr)
        Returns: list URL reel tunggal
        """
        logger.info(f"Scraping Facebook profile reels: {profile_url} (max={max_reels})")

        # PAKAI www.facebook.com + desktop UA — TERBUKTI tanpa login bisa!
        # m.facebook & mbasic redirect ke login untuk reels_tab (sudah di-test)
        # www.facebook dengan desktop UA return 10 reels tanpa cookies (verified 2025-08-31)
        target_url = profile_url
        if "m.facebook.com" in target_url or "mbasic.facebook.com" in target_url:
            target_url = target_url.replace("m.facebook.com", "www.facebook.com").replace("mbasic.facebook.com", "www.facebook.com")
        # Pastikan pakai www.facebook.com
        if "facebook.com" not in target_url:
            target_url = profile_url

        await self._ensure_browser()
        page = self._page

        try:
            await page.goto(target_url, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(5000)

            # Untuk www.facebook, tidak perlu cek login wall strict — public reels tetap tampil
            # Hanya cek jika redirect ke login.php tanpa konten reel sama sekali

            # Scroll untuk trigger lazy load (Facebook load reels via XHR)
            collected = set()
            for i in range(5):
                # Ambil semua href yang mengandung /reel/
                hrefs = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(h => h.includes('/reel/') || h.includes('/share/r/') || h.includes('/videos/'));
                }""")
                for h in hrefs:
                    # Clean URL: buang param tracking
                    clean = h.split('?')[0] if '/reel/' in h else h
                    # Normalisasi share/r ke reel id jika bisa
                    collected.add(clean)
                    if len(collected) >= max_reels:
                        break
                if len(collected) >= max_reels:
                    break

                # scroll
                await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                await page.wait_for_timeout(2500)

                # Juga coba cek page.content via regex sebagai fallback
                html = await page.content()
                for pat in REEL_ID_PATTERNS:
                    for mid in re.findall(pat, html):
                        # Buat URL reel standar
                        if mid.isdigit():
                            collected.add(f"https://www.facebook.com/reel/{mid}")
                        else:
                            collected.add(f"https://www.facebook.com/reel/{mid}")
                        if len(collected) >= max_reels:
                            break

            # Fallback: jika playwright tidak dapat apa-apa, coba request mbasic
            if not collected:
                logger.warning("Playwright tidak dapat reels, fallback ke mbasic.facebook.com")
                try:
                    mbasic_url = profile_url.replace("www.facebook.com", "mbasic.facebook.com").replace("m.facebook.com", "mbasic.facebook.com")
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36',
                        'Accept-Language': 'en-US,en;q=0.9',
                    }
                    resp = requests.get(mbasic_url, headers=headers, timeout=15)
                    html = resp.text
                    for mid in re.findall(r'/reel/(\d+)', html):
                        collected.add(f"https://www.facebook.com/reel/{mid}")
                except Exception as e:
                    logger.debug(f"mbasic fallback error: {e}")

            result = list(collected)[:max_reels]
            logger.info(f"Scraped {len(result)} reels dari profil")
            return result

        except Exception as e:
            logger.error(f"scrape_profile_reels error: {e}")
            return []

    async def download(self, url: str) -> Dict:
        """Download single Facebook reel/video via yt-dlp"""
        # Jika URL adalah profile reels_tab, scrape dulu
        if self.is_profile_reels_url(url):
            reel_urls = await self.scrape_profile_reels(url, max_reels=10)
            if not reel_urls:
                return {
                    "success": False,
                    "error": "Tidak ada Reels yang terdeteksi di profil ini. Coba kirim link Reels tunggal (contoh: facebook.com/reel/123...)"
                }
            # Untuk profil, kita return list reels untuk dipilih user / download batch
            # Download reel pertama sebagai preview, sisanya kasih list
            first_url = reel_urls[0]
            logger.info(f"Profile contains {len(reel_urls)} reels, downloading first: {first_url}")
            single_result = await self._download_single(first_url)
            if single_result["success"]:
                single_result["profile_reels"] = reel_urls
                single_result["profile_count"] = len(reel_urls)
                single_result["type"] = "profile"
            return single_result

        return await self._download_single(url)

    async def _download_single(self, url: str) -> Dict:
        try:
            opts = self.ydl_opts.copy()

            # Resolve fb.watch short link
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            if 'fb.watch' in url:
                try:
                    r = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
                    url = r.url
                except Exception:
                    pass

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except yt_dlp.DownloadError as e:
                    msg = str(e).lower()
                    if 'login required' in msg or 'cookies' in msg:
                        return {"success": False, "error": "Video Facebook ini butuh login. Kirim link yang public atau hubungi admin untuk set cookies Facebook."}
                    if 'unsupported url' in msg:
                        return {"success": False, "error": f"URL tidak didukung yt-dlp: {url}. Pakai format facebook.com/reel/ID atau fb.watch/ID"}
                    if 'not available' in msg or 'removed' in msg:
                        return {"success": False, "error": "Video tidak tersedia / sudah dihapus."}
                    raise

                if not info:
                    return {"success": False, "error": "Gagal extract info dari Facebook."}

                title = info.get('title', 'Facebook Video')
                media_id = info.get('id', 'unknown')

                ydl.download([url])

                expected = ydl.prepare_filename(info)
                if os.path.exists(expected):
                    file_path = expected
                else:
                    file_path = None
                    for f in os.listdir(self.download_dir):
                        if media_id in f and f.endswith(('.mp4', '.mkv', '.webm')):
                            file_path = os.path.join(self.download_dir, f)
                            break
                    if not file_path:
                        # cari file terbaru yang baru dibuat
                        candidates = [os.path.join(self.download_dir, x) for x in os.listdir(self.download_dir)]
                        if candidates:
                            candidates.sort(key=lambda x: os.path.getctime(x), reverse=True)
                            file_path = candidates[0]
                        else:
                            return {"success": False, "error": "File download tidak ditemukan."}

                # caption
                caption_text = ""
                raw_caption = info.get('description') or info.get('title') or ""
                if raw_caption:
                    from ..utils import sanitize_text
                    clean = sanitize_text(raw_caption.strip())
                    if len(clean) > 300:
                        clean = clean[:300] + "..."
                    caption_text = f"{clean}"

                media_type = "video"
                return {
                    "success": True,
                    "type": media_type,
                    "file_path": file_path,
                    "title": title,
                    "caption": caption_text,
                    "id": media_id
                }

        except yt_dlp.DownloadError as e:
            logger.error(f"Facebook yt-dlp error: {e}")
            return {"success": False, "error": f"Gagal download Facebook: {str(e)[:200]}"}
        except Exception as e:
            logger.error(f"Facebook download error: {e}")
            return {"success": False, "error": str(e)}

    def cleanup_downloads(self):
        try:
            import time
            for fn in os.listdir(self.download_dir):
                fp = os.path.join(self.download_dir, fn)
                if os.path.isfile(fp) and (time.time() - os.path.getctime(fp)) > 3600:
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
        except Exception:
            pass

    def _parse_netscape_cookies(self, path: str):
        """Parse netscape cookies.txt ke format playwright"""
        cookies = []
        try:
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) != 7:
                        continue
                    domain, _, cpath, secure, expires, name, value = parts
                    try:
                        cookies.append({
                            "name": name,
                            "value": value,
                            "domain": domain.lstrip('.'),
                            "path": cpath,
                            "expires": int(expires) if expires.isdigit() else -1,
                            "secure": secure == "TRUE",
                            "httpOnly": False,
                            "sameSite": "Lax"
                        })
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"parse cookies error: {e}")
        return cookies

    async def close(self):
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass

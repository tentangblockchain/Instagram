import os
import re
import time
import json
import logging
import tempfile
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class FastDLDownloader:
    def __init__(self):
        self.download_dir = os.path.join(tempfile.gettempdir(), "jawanese_bot_fastdl")
        os.makedirs(self.download_dir, exist_ok=True)
        self._browser = None
        self._page = None

    async def _ensure_browser(self):
        if self._page:
            try:
                await self._page.evaluate("1")
                return
            except Exception:
                pass
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        chromium = self._pw.chromium
        self._browser = await chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0'
        )
        self._page = await context.new_page()

    async def download(self, url: str) -> Dict:
        """Download Instagram content via fastdl.app"""
        try:
            await self._ensure_browser()
            page = self._page
            await page.goto('https://fastdl.app/en2', wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(1000)
            input_field = await page.query_selector('input[type="text"]')
            if not input_field:
                return {"success": False, "error": "Elemen input fastdl.app ora ketemu"}
            await input_field.fill(url)
            await page.wait_for_timeout(500)
            submit_btn = await page.query_selector('button[type="submit"]')
            if not submit_btn:
                return {"success": False, "error": "Tombol submit fastdl.app ora ketemu"}
            await submit_btn.click()
            import asyncio
            download_url = None
            for _ in range(20):
                await asyncio.sleep(1)
                html = await page.content()
                all_links = re.findall(r'https?://media\.fastdl\.app/get[^"\'<\s)]*', html)
                # prefer mp4 link over jpg
                for link in all_links:
                    clean = link.replace('&amp;', '&')
                    filename = re.search(r'filename=([^&]+)', clean)
                    if filename and '.mp4' in filename.group(1):
                        download_url = clean
                        break
                if not download_url and all_links:
                    download_url = all_links[0].replace('&amp;', '&')
                if download_url:
                    break
            if not download_url:
                return {"success": False, "error": "Link download ora ketemu dari fastdl.app"}
            return await self._download_file(download_url, url)
        except Exception as e:
            logger.error(f"FastDL error: {e}")
            return {"success": False, "error": f"FastDL error: {str(e)}"}

    async def _download_file(self, download_url: str, original_url: str) -> Dict:
        import asyncio
        vid_id = re.search(r'filename=([^&]+)', download_url)
        filename = vid_id.group(1) if vid_id else f"instagram_{int(time.time())}"
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        file_path = os.path.join(self.download_dir, filename)

        def _sync_download():
            resp = requests.get(download_url, timeout=120, stream=True, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}")
            with open(file_path, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            return file_path

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_download)

        logger.info(f"FastDL downloaded: {file_path}")
        return {
            "success": True,
            "type": "video",
            "file_path": file_path,
            "title": "Instagram Video",
            "caption": ""
        }

    async def cleanup(self):
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if hasattr(self, '_pw'):
            try:
                await self._pw.stop()
            except Exception:
                pass

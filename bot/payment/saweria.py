import asyncio
import json
import logging
import os
import qrcode

logger = logging.getLogger(__name__)

SAWERIA_API = "https://backend.saweria.co"

# Browser headers untuk bypass Cloudflare TLS fingerprinting
CURL_HEADERS = [
    "-H", "Accept: */*",
    "-H", "Accept-Encoding: gzip, deflate, br, zstd",
    "-H", "Accept-Language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "DNT: 1",
    "-H", "Origin: https://saweria.co",
    "-H", "Priority: u=1, i",
    "-H", "Referer: https://saweria.co/",
    "-H", "Sec-Fetch-Dest: empty",
    "-H", "Sec-Fetch-Mode: cors",
    "-H", "Sec-Fetch-Site: same-site",
    "-H", 'sec-ch-ua: "Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "-H", "sec-ch-ua-mobile: ?0",
    "-H", 'sec-ch-ua-platform: "Windows"',
    "-H", (
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    ),
]


async def _curl_post(url: str, body: dict) -> dict:
    args = [
        "curl", "-s", "--compressed", "-m", "30",
        "-X", "POST", url,
        "-H", "Content-Type: application/json",
        *CURL_HEADERS,
        "-d", json.dumps(body),
    ]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    try:
        return json.loads(stdout.decode())
    except json.JSONDecodeError as e:
        raise ValueError(f"Respons tidak valid dari Saweria: {stdout[:200]}") from e


async def _curl_get(url: str) -> dict:
    args = ["curl", "-s", "--compressed", "-m", "30", url, *CURL_HEADERS]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    try:
        return json.loads(stdout.decode())
    except json.JSONDecodeError as e:
        raise ValueError(f"Respons tidak valid dari Saweria: {stdout[:200]}") from e


async def _with_retry(fn, retries: int = 3, delay_ms: int = 2000):
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as err:
            if attempt == retries - 1:
                raise
            wait = delay_ms * (2 ** attempt) / 1000
            logger.warning(f"Retry {attempt + 1}/{retries} setelah {wait:.1f}s: {err}")
            await asyncio.sleep(wait)


class SaweriaAPI:
    SUCCESS_STATUSES = {"SUCCESS", "SETTLEMENT", "PAID", "CAPTURE"}
    FAILED_STATUSES  = {"FAILED", "EXPIRED", "CANCEL", "FAILURE", "DENY"}

    def __init__(self, username: str, user_id: str):
        self.username = username
        self.user_id = user_id

    async def calculate_amount(self, amount: int) -> dict:
        """Hitung total yang dibayar user termasuk biaya PG."""
        async def _call():
            payload = {
                "agree": True, "notUnderage": True,
                "message": "-", "amount": amount,
                "payment_type": "qris", "vote": "", "giphy": None,
                "yt": "", "ytStart": 0, "mediaType": None,
                "image_guess": None, "image_guess_answer": "",
                "amountToPay": "", "currency": "IDR",
                "pgFee": "", "platformFee": "",
                "customer_info": {"first_name": "bot", "email": "bot@bot.bot", "phone": ""},
            }
            res = await _curl_post(
                f"{SAWERIA_API}/donations/{self.username}/calculate_pg_amount",
                payload
            )
            if not res.get("data", {}).get("amount_to_pay"):
                raise ValueError(f"calculate_amount: respons tidak valid — {res}")
            return res["data"]

        return await _with_retry(_call)

    async def create_donation(self, amount: int, telegram_user_id: int, days: int) -> dict:
        """
        Buat transaksi donasi QRIS dan kembalikan {id, qr_string, amount_raw}.
        Message donasi diformatkan sebagai 'VIP {user_id} {days}' agar mudah dilacak.
        """
        async def _call():
            payload = {
                "agree": True, "notUnderage": True,
                "message": f"VIP {telegram_user_id} {days}",
                "amount": amount,
                "payment_type": "qris", "vote": "", "currency": "IDR",
                "customer_info": {
                    "first_name": f"user{telegram_user_id}",
                    "email": f"user{telegram_user_id}@vip.bot",
                    "phone": "",
                },
            }
            res = await _curl_post(
                f"{SAWERIA_API}/donations/snap/{self.user_id}",
                payload
            )
            data = res.get("data")
            if not data or not data.get("qr_string"):
                raise ValueError(res.get("message") or f"create_donation: respons tidak valid — {res}")
            return {
                "id": data["id"],
                "qr_string": data["qr_string"],
                "amount_raw": data.get("amount_raw", amount),
            }

        return await _with_retry(_call)

    async def check_payment_status(self, donation_id: str) -> dict | None:
        """Cek status pembayaran. Kembalikan dict {id, status} atau None jika gagal."""
        try:
            res = await _curl_get(f"{SAWERIA_API}/donations/qris/snap/{donation_id}")
            data = res.get("data")
            if data:
                return {
                    "id": data.get("id"),
                    "status": data.get("transaction_status", ""),
                    "amount": data.get("amount_raw"),
                }
            logger.warning(f"check_payment_status: tidak ada data — {str(res)[:200]}")
        except Exception as e:
            logger.warning(f"check_payment_status error: {e}")
        return None

    async def generate_qr_image(self, qr_string: str, donation_id: str) -> str:
        """Generate QR code PNG dari qr_string, simpan ke /tmp. Kembalikan path file."""
        def _make():
            img = qrcode.make(qr_string)
            path = f"/tmp/qr_{donation_id}.png"
            img.save(path)
            return path

        return await asyncio.get_event_loop().run_in_executor(None, _make)

    @staticmethod
    def delete_qr_file(donation_id: str) -> None:
        path = f"/tmp/qr_{donation_id}.png"
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

import logging
import traceback
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GroqMonitor:
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL   = "llama-3.1-8b-instant"

    SYSTEM_PROMPT = (
        "Kamu adalah AI monitoring assistant untuk Telegram bot downloader (TikTok & Instagram). "
        "Tugasmu menganalisa error/bug yang terjadi dan memberikan laporan singkat dalam Bahasa Indonesia. "
        "Selalu jawab dengan format terstruktur dan to the point."
    )

    def __init__(self, api_key: str, admin_ids: list, bot):
        self.api_key   = api_key
        self.admin_ids = admin_ids
        self.bot       = bot

    async def _call_groq(self, prompt: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    self.API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.MODEL,
                        "messages": [
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user",   "content": prompt},
                        ],
                        "max_tokens": 600,
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

    async def analyze_and_notify(
        self,
        error: Exception,
        context_info: str = "",
    ):
        tb_full  = traceback.format_exc()
        tb_short = tb_full[-1500:] if len(tb_full) > 1500 else tb_full
        err_type = type(error).__name__
        err_msg  = str(error)[:300]

        prompt = f"""Analisa error berikut dari Telegram bot downloader dan berikan laporan singkat:

Error Type : {err_type}
Error Msg  : {err_msg}
Context    : {context_info or '-'}
Traceback  :
{tb_short}

Berikan dalam format ini (WAJIB):
🔴 TINGKAT: [LOW / MEDIUM / HIGH / CRITICAL]
📌 PENYEBAB: (1-2 kalimat, apa penyebab error ini)
🛠 SOLUSI: (langkah konkret untuk memperbaiki, maks 3 poin)
⚡ DAMPAK: (apakah bot masih berjalan normal atau tidak)"""

        analysis = await self._call_groq(prompt)

        now      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ai_block = analysis if analysis else "⚠️ Groq tidak tersedia saat ini."

        text = (
            f"🚨 <b>BOT ERROR ALERT</b>\n"
            f"<code>🕐 {now}</code>\n\n"
            f"<b>Error:</b> <code>{err_type}</code>\n"
            f"<b>Pesan:</b> <code>{err_msg[:200]}</code>\n"
        )

        if context_info:
            text += f"<b>Konteks:</b> <code>{context_info[:200]}</code>\n"

        text += (
            f"\n<b>📋 Traceback:</b>\n"
            f"<pre>{tb_short[-800:]}</pre>\n\n"
            f"<b>🤖 Analisa AI (Groq):</b>\n"
            f"{ai_block}"
        )

        for chunk in _split_message(text):
            for admin_id in self.admin_ids:
                try:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=chunk,
                        parse_mode="HTML",
                    )
                except Exception as send_err:
                    logger.error(f"Gagal kirim alert ke admin {admin_id}: {send_err}")


def _split_message(text: str, limit: int = 4000):
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts

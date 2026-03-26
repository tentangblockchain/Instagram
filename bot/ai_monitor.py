import logging
import traceback
from collections import defaultdict
from datetime import date
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GroqMonitor:
    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    SYSTEM_PROMPT = (
        "Kamu adalah AI monitoring assistant untuk Telegram bot downloader (TikTok & Instagram). "
        "Tugasmu menganalisa error/bug yang terjadi dan memberikan laporan singkat dalam Bahasa Indonesia. "
        "Selalu jawab dengan format terstruktur dan to the point."
    )

    MODEL_TIERS = [
        {"name": "llama-3.3-70b-versatile",                  "daily_limit": 1000,  "quality": 10, "label": "Premium (10/10)"},
        {"name": "moonshotai/kimi-k2-instruct",               "daily_limit": 1000,  "quality": 9,  "label": "High (9/10)"},
        {"name": "groq/compound",                             "daily_limit": 250,   "quality": 8,  "label": "Good (8/10)"},
        {"name": "meta-llama/llama-4-scout-17b-16e-instruct", "daily_limit": 1000,  "quality": 7,  "label": "Scout (7/10)"},
        {"name": "llama-3.1-8b-instant",                      "daily_limit": 14400, "quality": 6,  "label": "Standard (6/10)"},
    ]

    def __init__(self, api_key: str, admin_ids: list, bot):
        self.api_key    = api_key
        self.admin_ids  = admin_ids
        self.bot        = bot
        self._usage: dict[str, dict] = defaultdict(lambda: {"date": None, "count": 0})

    def _can_use(self, tier: dict) -> bool:
        name  = tier["name"]
        today = date.today()
        entry = self._usage[name]
        if entry["date"] != today:
            entry["date"]  = today
            entry["count"] = 0
        return entry["count"] < tier["daily_limit"]

    def _record_use(self, name: str) -> None:
        entry = self._usage[name]
        entry["count"] += 1

    async def _try_model(self, model_name: str, prompt: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    self.API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user",   "content": prompt},
                        ],
                        "max_tokens": 600,
                        "temperature": 0.2,
                    },
                )
                if resp.status_code == 429:
                    logger.warning(f"Groq rate limit hit: {model_name}")
                    return None
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Groq model {model_name} gagal: {e}")
            return None

    async def _call_cascade(self, prompt: str) -> tuple[Optional[str], Optional[str]]:
        for tier in self.MODEL_TIERS:
            if not self._can_use(tier):
                logger.info(f"Groq tier '{tier['label']}' skip — limit harian tercapai")
                continue
            result = await self._try_model(tier["name"], prompt)
            if result:
                self._record_use(tier["name"])
                logger.info(f"Groq cascade sukses dengan: {tier['label']}")
                return result, tier["label"]
            logger.info(f"Groq cascade fallback dari: {tier['label']}")
        return None, None

    async def analyze_and_notify(self, error: Exception, context_info: str = ""):
        tb_full  = traceback.format_exc()
        tb_short = tb_full[-1500:] if len(tb_full) > 1500 else tb_full
        err_type = type(error).__name__
        err_msg  = str(error)[:300]

        from datetime import datetime
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

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

        analysis, model_label = await self._call_cascade(prompt)

        ai_block = analysis if analysis else "⚠️ Semua model Groq tidak tersedia saat ini."
        ai_footer = f"\n<i>Model: {model_label}</i>" if model_label else ""

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
            f"{ai_block}{ai_footer}"
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

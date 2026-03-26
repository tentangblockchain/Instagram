import json
import logging
import os
import traceback
import uuid
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PENDING_FIXES_FILE  = "pending_fixes.json"
ROLLBACK_STORE_FILE = "rollback_store.json"


# ── Pending fix storage ───────────────────────────────────────────────────────

def _load_fixes() -> dict:
    if os.path.exists(PENDING_FIXES_FILE):
        try:
            with open(PENDING_FIXES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_fixes(fixes: dict) -> None:
    with open(PENDING_FIXES_FILE, "w") as f:
        json.dump(fixes, f, indent=2)


def get_pending_fix(fix_id: str) -> Optional[dict]:
    return _load_fixes().get(fix_id)


def remove_pending_fix(fix_id: str) -> None:
    fixes = _load_fixes()
    fixes.pop(fix_id, None)
    _save_fixes(fixes)


# ── Rollback storage ──────────────────────────────────────────────────────────

def _load_rollbacks() -> dict:
    if os.path.exists(ROLLBACK_STORE_FILE):
        try:
            with open(ROLLBACK_STORE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_rollbacks(data: dict) -> None:
    with open(ROLLBACK_STORE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_rollback(rollback_id: str, file_path: str, backup_path: str, description: str) -> None:
    data = _load_rollbacks()
    data[rollback_id] = {
        "file_path":   file_path,
        "backup_path": backup_path,
        "description": description,
        "applied_at":  datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }
    _save_rollbacks(data)


def get_rollback(rollback_id: str) -> Optional[dict]:
    return _load_rollbacks().get(rollback_id)


def remove_rollback(rollback_id: str) -> None:
    data = _load_rollbacks()
    data.pop(rollback_id, None)
    _save_rollbacks(data)


def list_rollbacks() -> list:
    data = _load_rollbacks()
    return [{"id": k, **v} for k, v in data.items()]


# ── Groq Monitor ─────────────────────────────────────────────────────────────

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
        self.api_key   = api_key
        self.admin_ids = admin_ids
        self.bot       = bot
        self._usage: dict[str, dict] = defaultdict(lambda: {"date": None, "count": 0})

    # ── Usage tracking ────────────────────────────────────────────────────────

    def _can_use(self, tier: dict) -> bool:
        name  = tier["name"]
        today = date.today()
        entry = self._usage[name]
        if entry["date"] != today:
            entry["date"]  = today
            entry["count"] = 0
        return entry["count"] < tier["daily_limit"]

    def _record_use(self, name: str) -> None:
        self._usage[name]["count"] += 1

    # ── API call ──────────────────────────────────────────────────────────────

    async def _try_model(self, model_name: str, messages: list) -> Optional[str]:
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
                        "messages": messages,
                        "max_tokens": 800,
                        "temperature": 0.2,
                    },
                )
                if resp.status_code == 429:
                    logger.warning(f"Groq rate limit: {model_name}")
                    return None
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Groq model {model_name} gagal: {e}")
            return None

    async def _call_cascade(self, messages: list) -> tuple[Optional[str], Optional[str]]:
        for tier in self.MODEL_TIERS:
            if not self._can_use(tier):
                logger.info(f"Groq tier '{tier['label']}' skip — limit harian tercapai")
                continue
            result = await self._try_model(tier["name"], messages)
            if result:
                self._record_use(tier["name"])
                logger.info(f"Groq cascade sukses: {tier['label']}")
                return result, tier["label"]
        return None, None

    # ── Analysis ──────────────────────────────────────────────────────────────

    async def _analyze(self, err_type: str, err_msg: str, tb: str, context: str) -> tuple[Optional[str], Optional[str]]:
        prompt = f"""Analisa error berikut dari Telegram bot downloader:

Error Type : {err_type}
Error Msg  : {err_msg}
Context    : {context or '-'}
Traceback  :
{tb}

Berikan dalam format ini (WAJIB):
🔴 TINGKAT: [LOW / MEDIUM / HIGH / CRITICAL]
📌 PENYEBAB: (1-2 kalimat, apa penyebab error ini)
🛠 SOLUSI: (langkah konkret untuk memperbaiki, maks 3 poin)
⚡ DAMPAK: (apakah bot masih berjalan normal atau tidak)"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        return await self._call_cascade(messages)

    async def _generate_fix(self, err_type: str, err_msg: str, tb: str, context: str) -> Optional[dict]:
        # Baca file-file bot yang relevan untuk konteks
        source_ctx = _read_source_for_context(tb)
        if not source_ctx:
            return None

        prompt = f"""Kamu adalah Python developer ahli. Buat patch kode untuk memperbaiki error berikut.

Error Type : {err_type}
Error Msg  : {err_msg}
Context    : {context or '-'}
Traceback  :
{tb}

Source code terkait:
{source_ctx}

WAJIB balas HANYA dengan JSON valid (tanpa penjelasan, tanpa markdown), format persis seperti ini:
{{
  "file_path": "bot/main.py",
  "description": "penjelasan singkat apa yang diperbaiki",
  "old_code": "kode lama yang PERSIS ada di file (minimal 3 baris untuk keunikan)",
  "new_code": "kode baru penggantinya"
}}

Jika tidak yakin bisa fix dengan aman, balas: {{"fixable": false}}"""

        messages = [
            {"role": "system", "content": "Kamu adalah Python developer expert. Balas hanya dengan JSON valid, tanpa teks lain."},
            {"role": "user",   "content": prompt},
        ]
        raw, model_label = await self._call_cascade(messages)
        if not raw:
            return None

        try:
            raw_clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(raw_clean)
            if data.get("fixable") is False:
                return None
            if all(k in data for k in ("file_path", "old_code", "new_code")):
                data["model_label"] = model_label
                return data
        except Exception as e:
            logger.warning(f"Gagal parse fix JSON: {e} | raw: {raw[:300]}")
        return None

    # ── Main entry point ──────────────────────────────────────────────────────

    async def analyze_and_notify(self, error: Exception, context_info: str = ""):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        tb_full  = traceback.format_exc()
        tb_short = tb_full[-1500:] if len(tb_full) > 1500 else tb_full
        err_type = type(error).__name__
        err_msg  = str(error)[:300]
        now      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # 1. Analisa error
        analysis, model_label = await self._analyze(err_type, err_msg, tb_short, context_info)
        ai_block  = analysis if analysis else "⚠️ Groq tidak tersedia saat ini."
        ai_footer = f"\n<i>Model: {model_label}</i>" if model_label else ""

        # 2. Generate patch fix
        fix_data  = await self._generate_fix(err_type, err_msg, tb_short, context_info)
        fix_id    = None
        keyboard  = None

        if fix_data:
            fix_id = str(uuid.uuid4())[:8]
            fixes  = _load_fixes()
            fixes[fix_id] = {
                "file_path":   fix_data["file_path"],
                "description": fix_data.get("description", "-"),
                "old_code":    fix_data["old_code"],
                "new_code":    fix_data["new_code"],
                "model_label": fix_data.get("model_label", "-"),
                "created_at":  now,
                "error":       f"{err_type}: {err_msg}",
            }
            _save_fixes(fixes)

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Terapkan Fix & Restart", callback_data=f"apply_fix_{fix_id}"),
                    InlineKeyboardButton("❌ Abaikan",                callback_data=f"dismiss_fix_{fix_id}"),
                ]
            ])

        # 3. Susun pesan
        text = (
            f"🚨 <b>BOT ERROR ALERT</b>\n"
            f"<code>🕐 {now}</code>\n\n"
            f"<b>Error:</b> <code>{err_type}</code>\n"
            f"<b>Pesan:</b> <code>{err_msg[:200]}</code>\n"
        )
        if context_info:
            text += f"<b>Konteks:</b> <code>{context_info[:200]}</code>\n"

        text += (
            f"\n<b>📋 Traceback:</b>\n<pre>{tb_short[-700:]}</pre>\n\n"
            f"<b>🤖 Analisa AI:</b>\n{ai_block}{ai_footer}"
        )

        if fix_data:
            fix_preview = fix_data["new_code"][:300]
            text += (
                f"\n\n<b>🔧 AI Patch Tersedia</b> <code>[{fix_id}]</code>\n"
                f"📝 {fix_data.get('description', '-')}\n"
                f"<pre>{fix_preview}</pre>"
            )

        # 4. Kirim ke admin
        for chunk in _split_message(text):
            for admin_id in self.admin_ids:
                try:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=chunk,
                        parse_mode="HTML",
                        reply_markup=keyboard if chunk == _split_message(text)[-1] else None,
                    )
                except Exception as send_err:
                    logger.error(f"Gagal kirim alert ke admin {admin_id}: {send_err}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_source_for_context(tb: str, max_chars: int = 2000) -> str:
    import re
    files_mentioned = re.findall(r'File "([^"]+\.py)"', tb)
    bot_files = [f for f in dict.fromkeys(files_mentioned) if "bot/" in f or f.startswith("bot/")]

    result = []
    total  = 0
    for path in bot_files[:3]:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r") as f:
                content = f.read()
            snippet = content[:max_chars - total]
            result.append(f"# {path}\n{snippet}")
            total += len(snippet)
            if total >= max_chars:
                break
        except Exception:
            pass
    return "\n\n".join(result)


def _split_message(text: str, limit: int = 4000) -> list:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts

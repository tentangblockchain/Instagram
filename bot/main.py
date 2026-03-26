import asyncio
import logging
import os
import re
import sys
from datetime import datetime, timedelta

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

from bot.config import Config
from bot.constants import MESSAGES, VIP_PACKAGES
from bot.database import Database
from bot.downloaders import InstagramDownloader, TikTokDownloader
from bot.payment import SaweriaAPI

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

TIKTOK_RE    = re.compile(r"https?://(?:www\.)?(?:vm\.|vt\.)?tiktok\.com/\S+")
INSTAGRAM_RE = re.compile(r"https?://(?:www\.)?instagram\.com/\S+")


# ── Keyboard builders ───────────────────────────────────────────────────────────

def _kb_main(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("💎 Upgrade VIP",  callback_data="menu_vip"),
            InlineKeyboardButton("👑 Status VIP",   callback_data="menu_status"),
        ],
        [
            InlineKeyboardButton("🎁 VIP Gratis",   callback_data="menu_free_vip"),
            InlineKeyboardButton("📥 Cara Download", callback_data="menu_cara_dl"),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="menu_admin")])
    return InlineKeyboardMarkup(rows)


def _kb_channels(channels: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        if ch.startswith("@"):
            rows.append([InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch[1:]}")])
    rows.append([InlineKeyboardButton("✅ Sudah Join — Klaim VIP Gratis!", callback_data="free_vip_claim")])
    rows.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_main")])
    return InlineKeyboardMarkup(rows)


def _kb_vip() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{info['name']} — Rp {info['price']:,}", callback_data=f"vip_{days}")]
        for days, info in VIP_PACKAGES.items()
    ]
    rows.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_main")])
    return InlineKeyboardMarkup(rows)


def _kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_main")]])


def _kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 List VIP",   callback_data="admin_listvip"),
            InlineKeyboardButton("📊 Statistik",  callback_data="admin_stats"),
        ],
        [InlineKeyboardButton("🔙 Kembali", callback_data="menu_main")],
    ])


# ── Bot ─────────────────────────────────────────────────────────────────────────

class DownloaderBot:

    def __init__(self):
        self.config    = Config()
        self.db        = Database(self.config.DATABASE_PATH)
        self.tiktok    = TikTokDownloader()
        self.instagram = InstagramDownloader()
        self.saweria   = SaweriaAPI(
            username=self.config.SAWERIA_USERNAME,
            user_id=self.config.SAWERIA_USER_ID,
        )
        self._polling_tasks: dict[str, asyncio.Task] = {}

    # ── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )

    @staticmethod
    def _strip_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text or "")

    def _clean_caption(self, text: str) -> str:
        cleaned = self._strip_html(text).strip("` \n")
        return f"<code>{self._esc(cleaned)}</code>" if cleaned else ""

    async def _check_membership(self, user_id: int, bot: Bot) -> bool:
        if not self.config.REQUIRED_CHANNELS:
            return True
        for channel in self.config.REQUIRED_CHANNELS:
            try:
                member = await bot.get_chat_member(channel, user_id)
                if member.status not in ("member", "administrator", "creator"):
                    return False
            except Exception:
                return False
        return True

    def _vip_status_text(self, user_id: int) -> str:
        is_admin  = user_id in self.config.ADMIN_IDS
        vip_info  = self.db.get_vip_status(user_id)
        downloads = self.db.get_daily_downloads(user_id)

        if is_admin:
            return f"👑 ADMIN — Unlimited access\nDownload hari ini: {downloads}/∞"
        if vip_info and vip_info["is_active"]:
            limit = self.config.VIP_DAILY_LIMIT
            return (
                f"✅ Status: <b>VIP Aktif</b>\n"
                f"📅 Berlaku sampai: <code>{vip_info['expires_at']}</code>\n"
                f"📥 Download hari ini: {downloads}/{limit}"
            )
        limit = self.config.FREE_DAILY_LIMIT
        return (
            f"❌ Status: <b>Gratis</b>\n"
            f"📥 Download hari ini: {downloads}/{limit}\n\n"
            f"<i>Upgrade VIP untuk download lebih banyak! 💎</i>"
        )

    # ── Commands (/start dan /help saja) ────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user     = update.effective_user
        is_admin = user.id in self.config.ADMIN_IDS
        self.db.register_user(user.id, user.username or "Unknown")
        await update.message.reply_text(
            MESSAGES["welcome"],
            reply_markup=_kb_main(is_admin),
            parse_mode="HTML",
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        key     = "help_admin" if user_id in self.config.ADMIN_IDS else "help_user"
        await update.message.reply_text(MESSAGES[key], parse_mode="HTML")

    # ── Text handler (URL download + !delvip admin) ──────────────────────────────

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text    = update.message.text.strip()
        user_id = update.effective_user.id

        # Satu-satunya teks admin yang tetap dipertahankan karena butuh argumen
        if text.startswith("!delvip ") and user_id in self.config.ADMIN_IDS:
            return await self._admin_del_vip(update, text)

        # Download URL
        await self._handle_url(update, context)

    # ── URL Download ─────────────────────────────────────────────────────────────

    async def _handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text    = update.message.text
        user_id = update.effective_user.id

        tiktok_match    = TIKTOK_RE.search(text)
        instagram_match = INSTAGRAM_RE.search(text)

        if not tiktok_match and not instagram_match:
            return

        url      = (tiktok_match or instagram_match).group()
        platform = "tiktok" if tiktok_match else "instagram"
        is_vip   = self.db.is_user_vip(user_id)
        is_admin = user_id in self.config.ADMIN_IDS

        # Channel membership
        if not is_vip and not is_admin:
            if not await self._check_membership(user_id, context.bot):
                channels = "\n".join(f"• {ch}" for ch in self.config.REQUIRED_CHANNELS)
                await update.message.reply_text(
                    MESSAGES["not_member"].format(channels=channels),
                    parse_mode="HTML",
                )
                return

        # Daily limit
        if not is_admin:
            limit   = self.config.VIP_DAILY_LIMIT if is_vip else self.config.FREE_DAILY_LIMIT
            current = self.db.get_daily_downloads(user_id)
            if current >= limit:
                await update.message.reply_text(
                    MESSAGES["daily_limit"].format(current=current, limit=limit),
                    parse_mode="HTML",
                )
                return

        proc_msg = await update.message.reply_text(MESSAGES["processing"], parse_mode="HTML")

        try:
            if platform == "tiktok":
                await self._send_tiktok(update, context, url, user_id, proc_msg)
            else:
                await self._send_instagram(update, context, url, user_id, proc_msg)
        except Exception as e:
            logger.error(f"Download error: {e}")
            await proc_msg.edit_text(
                MESSAGES["download_error"].format(error=str(e)),
                parse_mode="HTML",
            )

    async def _send_tiktok(self, update, context, url, user_id, proc_msg):
        result = await self.tiktok.download(url)
        if not result["success"]:
            await proc_msg.edit_text(
                MESSAGES["download_error"].format(error=result["error"]),
                parse_mode="HTML",
            )
            return

        self.db.record_download(user_id)
        caption = self._clean_caption(result.get("caption", "")) or MESSAGES["download_success"]
        chat_id = update.effective_chat.id

        if result["type"] == "photo":
            await context.bot.send_photo(chat_id=chat_id, photo=result["file_path"],
                                         caption=caption, parse_mode="HTML")
        else:
            with open(result["file_path"], "rb") as f:
                await context.bot.send_video(chat_id=chat_id, video=f,
                                             caption=caption, parse_mode="HTML")

        _safe_delete(result["file_path"])
        await proc_msg.delete()

    async def _send_instagram(self, update, context, url, user_id, proc_msg):
        result = await self.instagram.download(url)
        if not result["success"]:
            await proc_msg.edit_text(
                MESSAGES["download_error"].format(error=result["error"]),
                parse_mode="HTML",
            )
            return

        chat_id = update.effective_chat.id

        if result["type"] == "carousel":
            await proc_msg.edit_text(
                MESSAGES["carousel_success"].format(count=result["count"]),
                parse_mode="HTML",
            )
            base_caption = self._clean_caption(result.get("caption", ""))[:1024]
            for i, path in enumerate(result["files"]):
                self.db.record_download(user_id)
                caption = f"<b>Part {i + 1}/{result['count']}</b>"
                if base_caption and i == 0:
                    caption += f"\n\n{base_caption}"
                try:
                    if path.endswith((".mp4", ".mov", ".avi")):
                        with open(path, "rb") as f:
                            await context.bot.send_video(chat_id=chat_id, video=f,
                                                         caption=caption, parse_mode="HTML")
                    else:
                        await context.bot.send_photo(chat_id=chat_id, photo=path,
                                                     caption=caption, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Error kirim carousel {i + 1}: {e}")
                _safe_delete(path)
        else:
            self.db.record_download(user_id)
            caption = self._clean_caption(result.get("caption", "")) or MESSAGES["download_success"]
            if result["type"] == "photo":
                await context.bot.send_photo(chat_id=chat_id, photo=result["file_path"],
                                             caption=caption, parse_mode="HTML")
            else:
                with open(result["file_path"], "rb") as f:
                    await context.bot.send_video(chat_id=chat_id, video=f,
                                                 caption=caption, parse_mode="HTML")
            _safe_delete(result["file_path"])
            await proc_msg.delete()

    # ── Menu callbacks ──────────────────────────────────────────────────────────

    async def cb_menu_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query    = update.callback_query
        await query.answer()
        is_admin = query.from_user.id in self.config.ADMIN_IDS
        await query.edit_message_text(
            MESSAGES["main_menu"],
            reply_markup=_kb_main(is_admin),
            parse_mode="HTML",
        )

    async def cb_menu_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            MESSAGES["vip_info"],
            reply_markup=_kb_vip(),
            parse_mode="HTML",
        )

    async def cb_menu_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query   = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        await query.edit_message_text(
            MESSAGES["vip_status"].format(status=self._vip_status_text(user_id)),
            reply_markup=_kb_back(),
            parse_mode="HTML",
        )

    async def cb_menu_cara_dl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            MESSAGES["cara_dl"],
            reply_markup=_kb_back(),
            parse_mode="HTML",
        )

    async def cb_menu_free_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query   = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if self.db.is_user_vip(user_id):
            vip_info = self.db.get_vip_status(user_id)
            await query.edit_message_text(
                MESSAGES["free_vip_already_active"].format(expires=vip_info["expires_at"]),
                reply_markup=_kb_back(),
                parse_mode="HTML",
            )
            return

        if not self.config.REQUIRED_CHANNELS:
            await query.edit_message_text(
                MESSAGES["free_vip_no_channels"],
                reply_markup=_kb_back(),
                parse_mode="HTML",
            )
            return

        channels_text = "\n".join(f"• {ch}" for ch in self.config.REQUIRED_CHANNELS)
        await query.edit_message_text(
            MESSAGES["free_vip_join_channels"].format(channels=channels_text),
            reply_markup=_kb_channels(self.config.REQUIRED_CHANNELS),
            parse_mode="HTML",
        )

    async def cb_free_vip_claim(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query   = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if self.db.is_user_vip(user_id):
            vip_info = self.db.get_vip_status(user_id)
            await query.edit_message_text(
                MESSAGES["free_vip_already_active"].format(expires=vip_info["expires_at"]),
                reply_markup=_kb_back(),
                parse_mode="HTML",
            )
            return

        if self.config.REQUIRED_CHANNELS and not await self._check_membership(user_id, context.bot):
            channels_text = "\n".join(f"• {ch}" for ch in self.config.REQUIRED_CHANNELS)
            await query.edit_message_text(
                MESSAGES["free_vip_not_member"].format(channels=channels_text),
                reply_markup=_kb_channels(self.config.REQUIRED_CHANNELS),
                parse_mode="HTML",
            )
            return

        expires_at = datetime.now() + timedelta(days=1)
        self.db.activate_vip(user_id, expires_at)
        logger.info(f"VIP gratis diklaim: user {user_id}, sampai {expires_at}")
        await query.edit_message_text(
            MESSAGES["free_vip_success"].format(expires=expires_at.strftime("%d %B %Y %H:%M")),
            reply_markup=_kb_back(),
            parse_mode="HTML",
        )

    async def cb_menu_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query   = update.callback_query
        user_id = query.from_user.id
        await query.answer()
        if user_id not in self.config.ADMIN_IDS:
            await query.answer(MESSAGES["not_admin"], show_alert=True)
            return
        await query.edit_message_text(
            "🔐 <b>Admin Panel</b>\n\nPilih aksi di bawah:",
            reply_markup=_kb_admin(),
            parse_mode="HTML",
        )

    async def cb_admin_listvip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query   = update.callback_query
        user_id = query.from_user.id
        await query.answer()
        if user_id not in self.config.ADMIN_IDS:
            await query.answer(MESSAGES["not_admin"], show_alert=True)
            return

        vip_users = self.db.get_vip_users()
        if not vip_users:
            text = "📭 <b>Tidak ada VIP aktif saat ini</b>"
        else:
            lines = ["👑 <b>Daftar VIP Aktif:</b>\n"]
            for i, u in enumerate(vip_users[:25], 1):
                badge = "✅" if u["is_active"] else "❌"
                lines.append(
                    f"<b>#{i}</b> <code>{u['user_id']}</code> "
                    f"{badge} sampai <code>{u['vip_expires_at']}</code>"
                )
            if len(vip_users) > 25:
                lines.append(f"\n<i>Menampilkan 25 dari {len(vip_users)}</i>")
            lines.append("\n<i>Hapus VIP: ketik <code>!delvip &lt;user_id&gt;</code></i>")
            text = "\n".join(lines)

        await query.edit_message_text(
            text,
            reply_markup=_kb_admin(),
            parse_mode="HTML",
        )

    async def cb_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query   = update.callback_query
        user_id = query.from_user.id
        await query.answer()
        if user_id not in self.config.ADMIN_IDS:
            await query.answer(MESSAGES["not_admin"], show_alert=True)
            return

        stats = self.db.get_user_stats()
        pay   = stats["payment_stats"]
        text  = (
            "📊 <b>Statistik Bot</b>\n\n"
            f"👥 Total user: <b>{stats['total_users']}</b>\n"
            f"👑 VIP aktif: <b>{stats['vip_users']}</b>\n"
            f"📥 Download hari ini: <b>{stats['downloads_today']}</b>\n\n"
            "<b>💳 Pembayaran:</b>\n"
            + ("\n".join(f"• {k}: {v}" for k, v in pay.items()) if pay else "• Belum ada data")
        )
        await query.edit_message_text(
            text,
            reply_markup=_kb_admin(),
            parse_mode="HTML",
        )

    # ── VIP purchase callback ────────────────────────────────────────────────────

    async def cb_vip_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query   = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        days    = int(query.data.split("_")[1])
        package = VIP_PACKAGES[days]
        price   = package["price"]

        await query.edit_message_text(MESSAGES["qr_generating"], parse_mode="HTML")

        try:
            calc        = await self.saweria.calculate_amount(price)
            amount_pay  = calc["amount_to_pay"]

            donation    = await self.saweria.create_donation(price, user_id, days)
            donation_id = donation["id"]
            amount_raw  = donation["amount_raw"]

            qr_path = await self.saweria.generate_qr_image(donation["qr_string"], donation_id)

            payment_id = self.db.record_payment(
                user_id=user_id, days=days, amount=price,
                status="pending", donation_id=donation_id,
            )

            caption = MESSAGES["qr_caption"].format(days=days, amount=amount_pay)
            with open(qr_path, "rb") as f:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=f, caption=caption, parse_mode="HTML",
                )
            SaweriaAPI.delete_qr_file(donation_id)

            task = asyncio.create_task(self._poll_payment(
                bot=context.bot, user_id=user_id, donation_id=donation_id,
                payment_id=payment_id, days=days, amount_raw=amount_raw,
                chat_id=query.message.chat_id,
            ))
            self._polling_tasks[donation_id] = task

        except Exception as e:
            logger.error(f"Error membuat pembayaran Saweria: {e}")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=MESSAGES["qr_error"].format(error=str(e)),
                parse_mode="HTML",
            )

    # ── Payment polling ──────────────────────────────────────────────────────────

    async def _poll_payment(
        self, bot: Bot, user_id: int, donation_id: str,
        payment_id: int, days: int, amount_raw: int, chat_id: int,
    ):
        max_seconds = 15 * 60
        interval    = 7
        start       = asyncio.get_event_loop().time()

        try:
            while True:
                if asyncio.get_event_loop().time() - start >= max_seconds:
                    self.db.update_payment_status(payment_id, "expired")
                    await bot.send_message(chat_id=chat_id,
                                           text=MESSAGES["payment_expired"], parse_mode="HTML")
                    break

                data = await self.saweria.check_payment_status(donation_id)
                if data:
                    status = data["status"].upper()
                    if status in SaweriaAPI.SUCCESS_STATUSES:
                        expires_at = datetime.now() + timedelta(days=days)
                        self.db.activate_vip(user_id, expires_at)
                        self.db.update_payment_status(payment_id, "approved")
                        await bot.send_message(
                            chat_id=chat_id,
                            text=MESSAGES["payment_success"].format(
                                days=days,
                                expires=expires_at.strftime("%d %B %Y %H:%M"),
                            ),
                            parse_mode="HTML",
                        )
                        logger.info(f"VIP aktif: user {user_id}, {days} hari, sampai {expires_at}")
                        break
                    elif status in SaweriaAPI.FAILED_STATUSES:
                        self.db.update_payment_status(payment_id, "rejected")
                        await bot.send_message(chat_id=chat_id,
                                               text=MESSAGES["payment_failed"], parse_mode="HTML")
                        break

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info(f"Polling dibatalkan: {donation_id}")
        except Exception as e:
            logger.error(f"Error polling {donation_id}: {e}")
        finally:
            self._polling_tasks.pop(donation_id, None)

    # ── Admin text command (!delvip) ─────────────────────────────────────────────

    async def _admin_del_vip(self, update: Update, text: str):
        user_id = update.effective_user.id
        try:
            target_id = int(text.split()[1])
        except (IndexError, ValueError):
            await update.message.reply_text(
                "❌ Format: <code>!delvip &lt;user_id&gt;</code>", parse_mode="HTML"
            )
            return

        vip = self.db.get_vip_status(target_id)
        if not vip or not vip.get("is_active"):
            await update.message.reply_text(
                f"❌ User <code>{target_id}</code> tidak punya VIP aktif.", parse_mode="HTML"
            )
            return

        self.db.remove_vip(target_id)
        await update.message.reply_text(
            f"✅ VIP user <code>{target_id}</code> berhasil dihapus.", parse_mode="HTML"
        )
        logger.info(f"Admin {user_id} menghapus VIP user {target_id}")

    # ── Job queue ────────────────────────────────────────────────────────────────

    async def _job_cleanup_vip(self, context: ContextTypes.DEFAULT_TYPE):
        self.db.cleanup_expired_vip()

    # ── Run ──────────────────────────────────────────────────────────────────────

    def run(self):
        logger.info("🤖 Memulai Bot Downloader...")

        app = Application.builder().token(self.config.BOT_TOKEN).build()

        # Commands
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help",  self.cmd_help))

        # Text (URL download + !delvip)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

        # Menu callbacks
        app.add_handler(CallbackQueryHandler(self.cb_menu_main,      pattern=r"^menu_main$"))
        app.add_handler(CallbackQueryHandler(self.cb_menu_vip,       pattern=r"^menu_vip$"))
        app.add_handler(CallbackQueryHandler(self.cb_menu_status,    pattern=r"^menu_status$"))
        app.add_handler(CallbackQueryHandler(self.cb_menu_cara_dl,   pattern=r"^menu_cara_dl$"))
        app.add_handler(CallbackQueryHandler(self.cb_menu_free_vip,  pattern=r"^menu_free_vip$"))
        app.add_handler(CallbackQueryHandler(self.cb_free_vip_claim, pattern=r"^free_vip_claim$"))
        app.add_handler(CallbackQueryHandler(self.cb_menu_admin,     pattern=r"^menu_admin$"))
        app.add_handler(CallbackQueryHandler(self.cb_admin_listvip,  pattern=r"^admin_listvip$"))
        app.add_handler(CallbackQueryHandler(self.cb_admin_stats,    pattern=r"^admin_stats$"))

        # VIP purchase
        app.add_handler(CallbackQueryHandler(self.cb_vip_select, pattern=r"^vip_\d+$"))

        if app.job_queue:
            app.job_queue.run_repeating(self._job_cleanup_vip, interval=3600)

        logger.info("🚀 Bot siap melayani!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _safe_delete(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ── Entry point ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        DownloaderBot().run()
    except ValueError as e:
        logger.error(f"Konfigurasi error: {e}")
        print(f"❌ Konfigurasi error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error kritis: {e}")
        sys.exit(1)

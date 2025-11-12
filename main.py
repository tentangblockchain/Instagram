# Auto-install telegram library jika belum ada
import sys
import subprocess

def ensure_telegram_installed():
    try:
        import telegram
        from telegram import Update
        print("✅ Telegram library OK")
        return True
    except ImportError as e:
        print(f"❌ Telegram library missing: {e}")
        try:
            print("🔄 Installing python-telegram-bot...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot[job-queue]==20.7", "--no-cache-dir"])
            print("✅ Installation complete! Please restart the repl manually.")
            return False
        except Exception as install_error:
            print(f"❌ Installation failed: {install_error}")
            return False

# Pastikan telegram terinstall
if not ensure_telegram_installed():
    print("❌ Cannot start bot - telegram library installation failed")
    sys.exit(1)

import os
import logging
import asyncio
import re
import html
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError
from database import Database
from tiktok_downloader import TikTokDownloader
from instagram_downloader import InstagramDownloader
from trakteer_api import TrakteerAPI
from config import Config

# Setup logging hanya ke console, level INFO
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,  # GANTI DEBUG → INFO
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Admin log juga biar ga ribut
admin_logger = logging.getLogger('admin_commands')
admin_logger.setLevel(logging.INFO)  # GANTI DEBUG → INFO

class JawaneseTikTokBot:
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.tiktok_dl = TikTokDownloader()
        self.instagram_dl = InstagramDownloader()
        self.trakteer = TrakteerAPI()

        # VIP packages in IDR - matching Trakteer quantity system

        self.vip_packages = {
            3: {"price": 5000, "name": "3 dina", "quantity": 1},
            7: {"price": 10000, "name": "7 dina", "quantity": 2},
            15: {"price": 20000, "name": "15 dina", "quantity": 4},
            30: {"price": 35000, "name": "30 dina", "quantity": 7},
            60: {"price": 60000, "name": "60 dina", "quantity": 12},
            90: {"price": 80000, "name": "90 dina", "quantity": 16}
        }


        # Javanese messages (bahasa Jawa kasar) - HTML formatted
        # Enhanced Javanese Bot Messages with Modern HTML Styling
        self.messages = {
            # Welcome & Status Messages
            "welcome": """
        🎭 <b>SUGENG RAWUH NENG BOT DOWNLOADER!</b> 🎭

        <code>✨ TikTok &amp; Instagram Downloader Pro ✨</code>

        <blockquote>Kirim link TikTok utawa Instagram, utawa ketik <code>/vip</code> kanggo upgrade akun cok!</blockquote>

        <i>⚡ Gratis tapi terbatas • 💎 VIP unlimited</i>
        """,

            "not_member": """
        🚫 <b>EH GOBLOK! KUDU JOIN CHANNEL SIK!</b>

        <blockquote>📢 Wajib join kabeh channel iki:
        {channels}</blockquote>

        <i>Join kabeh channel sik baru iso ngunduh cok!</i>
        """,

            "daily_limit": """
        ⏰ <b>WIS TEKAN LIMIT DOWNLOAD!</b>

        <blockquote>📊 Limit dina iki: <code>{current}/{limit}</code></blockquote>

        <i>💎 Upgrade VIP kanggo unlimited download utawa enteni sesuk!</i>
        """,

            "invalid_url": """
        ❌ <b>LINK MU SALAH COK!</b>

        <blockquote>🔗 Kirim link sing bener:
        • <code>TikTok</code> (tiktok.com, vt.tiktok.com, vm.tiktok.com)
        • <code>Instagram</code> (instagram.com, instagr.am)</blockquote>
        """,

            # Processing Messages
            "processing": """
        ⏳ <b>SABAR COK... LAGI DIPROSES...</b>

        <blockquote><code>🔄 Downloading content...</code></blockquote>

        <i>Tunggu sebentar ya, lagi ngambil file mu!</i>
        """,

            "download_success": """
        ✅ <b>SUKSES COK!</b>

        <blockquote><code>📁 File mu wis siap!</code></blockquote>

        <i>Enjoy konten mu! 🎉</i>
        """,

            "carousel_success": """
        ✅ <b>SUKSES COK!</b>

        <blockquote><code>📸 Carousel/Album berhasil diunduh!</code>
        <b>Total file:</b> {count}</blockquote>

        <i>Semua file carousel wis dikirim! 🎊</i>
        """,

            "download_error": """
        ❌ <b>ERROR COK!</b>

        <blockquote><code>⚠️ Ora iso download:</code>
        {error}</blockquote>

        <i>Coba lagi utawa ganti link lain!</i>
        """,

            # VIP System Messages
            "vip_info": """
        💎 <b>PAKET VIP PREMIUM</b> 💎

        <blockquote><code>🌟 Pilih paket sing cocok kanggo kowe:</code></blockquote>

        • <code>3 hari</code> - <b>Rp 5,000</b>
        • <code>7 hari</code> - <b>Rp 10,000</b> <tg-spoiler>(Recommended)</tg-spoiler>
        • <code>15 hari</code> - <b>Rp 20,000</b>
        • <code>30 hari</code> - <b>Rp 35,000</b> <tg-spoiler>(Best Value)</tg-spoiler>
        • <code>60 hari</code> - <b>Rp 60,000</b>
        • <code>90 hari</code> - <b>Rp 80,000</b> <tg-spoiler>(Super Saver)</tg-spoiler>


        <i>⚡ VIP = Download unlimited + priority support!</i>
        """,

            "vip_status": """
        👑 <b>STATUS VIP MU COK</b>

        <blockquote>{status}</blockquote>

        <i>Makasih wis dadi VIP member! 🙏</i>
        """,

            "payment_generated": """
        💳 <b>LINK BAYAR WIS DIGAWE COK!</b>

        <blockquote><code>🔗 Klik link iki kanggo bayar:</code>
        {url}</blockquote>

        <b>⚠️ PENTING BANGET:</b>
        <i>Pembayaran bakal otomatis terdeteksi sawise kowe bener² bayar. Ojo cuma klik link tok!</i>

        <tg-spoiler>Biasane proses 1-24 jam</tg-spoiler>
        """,

            "payment_pending": """
        ⏳ <b>PEMBAYARAN LAGI PENDING COK</b>

        <blockquote><code>🔄 Status: Waiting for admin approval</code></blockquote>

        <i>Sabar ya, admin lagi ngecek pembayaran mu!</i>
        """,

            "payment_approved": """
        🎉 <b>SELAMAT COK!</b>

        <blockquote><code>✅ Pembayaran mu wis diapprove!</code>
        <b>VIP Status:</b> <u>AKTIF SEKARANG</u></blockquote>

        <i>Selamat menikmati fitur VIP unlimited! 🚀</i>
        """,

            "payment_rejected": """
        ❌ <b>PEMBAYARAN DITOLAK</b>

        <blockquote><code>⚠️ Alasan: Pembayaran tidak valid</code></blockquote>

        <i>Pastikan wis bener² mbayar po durung cok!</i>
        """,

            "payment_detected": """
        💰 <b>PEMBAYARAN TERDETEKSI!</b>

        <blockquote><code>🔍 Status: Pending approval admin</code></blockquote>

        <i>Pembayaran mu wis masuk, tunggu admin approve ya!</i>
        """,

            # Admin Messages
            "admin_check": """
        🔍 <b>NGECEK TRAKTEER API...</b>

        <blockquote><code>⏳ Scanning for new payments...</code></blockquote>
        """,

            "admin_no_payments": """
        📊 <b>HASIL SCAN TRAKTEER</b>

        <blockquote><code>ℹ️ Ora ana pembayaran anyar cok.</code></blockquote>
        """,

            "admin_sync_success": """
        📊 <b>HASIL SCAN TRAKTEER</b>

        <blockquote><code>✅ Ketemu {count} pembayaran anyar!</code></blockquote>

        <i>Cek daftar pending kanggo approve/reject!</i>
        """,

            "admin_approved": """
        ✅ <b>PEMBAYARAN DIAPPROVE!</b>

        <blockquote><code>👑 User VIP baru wis aktif!</code></blockquote>
        """,

            "admin_rejected": """
        ❌ <b>PEMBAYARAN DITOLAK!</b>

        <blockquote><code>⚠️ User wis dinotifikasi.</code></blockquote>
        """,

            "not_admin": """
        🚫 <b>KOWE ORA ADMIN COK!</b>

        <blockquote><code>⛔ Access denied - Admin only command</code></blockquote>
        """,

            "pending_list": """
        📋 <b>DAFTAR PEMBAYARAN PENDING</b>

        <blockquote><code>⏳ Review &amp; approve pembayaran iki:</code></blockquote>
        """,

            # Help Messages
            "help_user": """
        🤖 <b>PANDUAN LENGKAP BOT DOWNLOADER</b>

        <blockquote><code>📖 Baca panduan iki ben paham cara nggunakake bot!</code></blockquote>

        <b>🎯 COMMAND DASAR:</b>
        • <code>/start</code> - <i>Mulai bot &amp; lihat welcome message</i>
        • <code>/vip</code> - <i>Lihat paket VIP &amp; beli subscription</i>
        • <code>/status</code> - <i>Cek status VIP kamu saat ini</i>
        • <code>/help</code> - <i>Tampilkan bantuan lengkap</i>

        <b>📥 CARA DOWNLOAD:</b>
        <blockquote><u>Kirim link langsung ke bot:</u>
        • <code>TikTok</code> - vt.tiktok.com, vm.tiktok.com, tiktok.com
        • <code>Instagram</code> - Post, carousel, album</blockquote>

        <b>💎 PAKET VIP PREMIUM:</b>
        <pre>
        ⚡ 3 hari    → Rp 5,000
        🔥 7 hari    → Rp 10,000  (Recommended)
        ⭐ 15 hari   → Rp 20,000
        💯 30 hari   → Rp 35,000  (Best Value)
        🚀 60 hari   → Rp 60,000
        👑 90 hari   → Rp 80,000  (Super Saver)
        </pre>


        <b>⚠️ SISTEM LIMIT:</b>
        <blockquote>• <code>User Gratis:</code> 10 download/hari
        • <code>User VIP:</code> 100 download/hari <tg-spoiler>(Unlimited)</tg-spoiler></blockquote>

        <b>💳 PANDUAN BAYAR VIP:</b>
        <blockquote><code>1.</code> Ketik <code>/vip</code> pilih paket
        <code>2.</code> Klik link pembayaran Trakteer
        <code>3.</code> Bayar sesuai nominal
        <code>4.</code> Tunggu admin approve (1-24 jam)</blockquote>

        <i>🎉 Selamat menggunakan bot! Ada pertanyaan? Chat admin.</i>
        """,

            "help_admin": """
        🔐 <b>PANDUAN ADMIN BOT DOWNLOADER</b>

        <blockquote><code>⚡ Command khusus admin - rahasia!</code></blockquote>

        <b>🛠️ COMMAND ADMIN EKSKLUSIF:</b>
        • <code>!cek</code> - <i>Sync &amp; cek pembayaran baru dari Trakteer API</i>
        • <code>!pend</code> - <i>Lihat daftar pembayaran pending manual</i>
        • <code>!listvip</code> - <i>Lihat daftar semua user VIP aktif</i>
        • <code>!delvip &lt;user_id&gt;</code> - <i>Hapus VIP user tertentu</i>

        <b>👥 AKSES ADMIN:</b>
        <blockquote><code>🔑 Admin ID:</code> 6185398749, 7027694923</blockquote>

        <b>🔄 FLOW PEMBAYARAN SEMI-OTOMATIS:</b>
        <blockquote>
        1️⃣ User request VIP (/vip)
        2️⃣ User bayar via Trakteer 
           Format: VIP_{user_id}_{days}days
        3️⃣ Admin ketik !cek → Bot poll Trakteer API
        4️⃣ Bot parse &amp; validate payment data
        5️⃣ Admin approve/reject via tombol
        6️⃣ User dapat notifikasi &amp; VIP aktif
        </blockquote>

        <i>🎯 Sistem berjalan optimal dengan monitoring admin!</i>
        """
        }
        
    def clean_caption(self, text):
        """Bersihkan, escape, dan format dalam <code>...</code>"""
        text = self.strip_html_tags(text).strip("` \n")
        if not text:
            return ""
        return f"<code>{self.escape_html(text)}</code>"

    def strip_html_tags(self, text):
        """Hapus semua tag HTML dari caption user"""
        return re.sub(r'<.*?>', '', text or '')

    def escape_html(self, text):
        """Safely escape HTML entities in text"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
                    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        username = user.username or "Unknown"
    
        # Register user to database
        self.db.register_user(user_id, username)
    
        await update.message.reply_text(
            self.messages["welcome"],
            parse_mode="HTML"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id
        is_admin = user_id in self.config.ADMIN_IDS
    
        help_text = self.messages["help_admin"] if is_admin else self.messages["help_user"]
    
        await update.message.reply_text(
            help_text,
            parse_mode="HTML"
        )

    async def check_channel_membership(self, user_id: int, bot: Bot) -> bool:
        """Check if user is member of all required channels"""
        if not self.config.REQUIRED_CHANNELS:
            return True

        for channel in self.config.REQUIRED_CHANNELS:
            try:
                member = await bot.get_chat_member(channel, user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
            except Exception:
                return False
        return True

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all text messages with debugging"""
        message_text = update.message.text
        user_id = update.effective_user.id

        # Log all messages for debugging
        logger.info(f"Received message from {user_id}: '{message_text}'")

        # Check if it's an admin command
        if message_text.strip() in ['!cek', '!cp']:
            logger.info(f"Detected admin check command: {message_text}")
            await self.admin_check_payments(update, context)
            return
        elif message_text.strip() in ['!pend', '!pa']:
            logger.info(f"Detected admin pending command: {message_text}")
            await self.admin_pending_list(update, context)
            return
        elif message_text.strip() == '!listvip':
            logger.info(f"Detected admin list VIP command: {message_text}")
            await self.admin_list_vip(update, context)
            return
        elif message_text.strip().startswith('!delvip '):
            logger.info(f"Detected admin delete VIP command: {message_text}")
            await self.admin_delete_vip(update, context)
            return
        elif message_text.strip() == '!debug':
            logger.info(f"Detected admin debug command: {message_text}")
            await self.admin_debug(update, context)
            return

        # Otherwise handle as media URL
        await self.handle_media_url(update, context)

    async def handle_media_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle TikTok and Instagram URL downloads"""
        user_id = update.effective_user.id
        message_text = update.message.text

        # Check if message contains TikTok or Instagram URL
        tiktok_pattern = r'https?://(?:www\.)?(?:vm\.|vt\.)?tiktok\.com/[^\s]+'
        instagram_pattern = r'https?://(?:www\.)?instagram\.com/[^\s]+'

        url_match = None
        platform = None

        if re.search(tiktok_pattern, message_text):
            url_match = re.search(tiktok_pattern, message_text)
            platform = "tiktok"
        elif re.search(instagram_pattern, message_text):
            url_match = re.search(instagram_pattern, message_text)
            platform = "instagram"
        else:
            return  # Not a supported URL

        if not url_match:
            await update.message.reply_text(self.messages["invalid_url"], parse_mode='HTML')
            return

        url = url_match.group()

        # Check VIP status and admin status
        is_vip = self.db.is_user_vip(user_id)
        is_admin = user_id in self.config.ADMIN_IDS

        # Check channel membership for non-VIP and non-admin users
        if not is_vip and not is_admin:
            is_member = await self.check_channel_membership(user_id, context.bot)
            if not is_member:
                channels_list = ", ".join(self.config.REQUIRED_CHANNELS)
                await update.message.reply_text(
                    self.messages["not_member"].format(channels=channels_list),
                    parse_mode='HTML'
                )
                return

        # Check daily limit (admins get unlimited downloads)
        if not is_admin:
            daily_limit = self.config.VIP_DAILY_LIMIT if is_vip else self.config.FREE_DAILY_LIMIT
            current_downloads = self.db.get_daily_downloads(user_id)

            if current_downloads >= daily_limit:
                await update.message.reply_text(
                    self.messages["daily_limit"].format(current=current_downloads, limit=daily_limit),
                    parse_mode='HTML'
                )
                return

        # Process download
        processing_msg = await update.message.reply_text(self.messages["processing"], parse_mode='HTML')

        try:
            if platform == "tiktok":
                # TikTok download
                result = await self.tiktok_dl.download(url)

                if result["success"]:
                    self.db.record_download(user_id)
                
                    caption = self.clean_caption(result.get("caption", ""))
                    if not caption:
                        caption = self.messages["download_success"]
                
                    if result["type"] == "photo":
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=result["file_path"],
                            caption=caption,
                            parse_mode='HTML'
                        )
                    else:  # video
                        with open(result["file_path"], 'rb') as video_file:
                            await context.bot.send_video(
                                chat_id=update.effective_chat.id,
                                video=video_file,
                                caption=caption,
                                parse_mode='HTML'
                            )
                
                    if os.path.exists(result["file_path"]):
                        os.remove(result["file_path"])

                else:
                    await processing_msg.edit_text(
                        self.messages["download_error"].format(error=result["error"]),
                        parse_mode='HTML'
                    )


            elif platform == "instagram":
                # Instagram download
                result = await self.instagram_dl.download(url)

                if result["success"]:
                    if result["type"] == "carousel":
                        await processing_msg.edit_text(
                            self.messages["carousel_success"].format(count=result["count"]),
                            parse_mode='HTML'
                        )
                    
                        base_caption = self.clean_caption(result.get("caption", ""))[:1024]
                    
                        for i, file_path in enumerate(result["files"]):
                            self.db.record_download(user_id)
                            try:
                                part_header = f"<b>Part {i+1}/{result['count']}</b>"
                                caption = f"{part_header}"
                                if base_caption and i == 0:
                                    caption += f"\n\n{base_caption}"
                    
                                if file_path.endswith(('.mp4', '.mov', '.avi')):
                                    with open(file_path, 'rb') as video_file:
                                        await context.bot.send_video(
                                            chat_id=update.effective_chat.id,
                                            video=video_file,
                                            caption=caption,
                                            parse_mode='HTML'
                                        )
                                else:
                                    await context.bot.send_photo(
                                        chat_id=update.effective_chat.id,
                                        photo=file_path,
                                        caption=caption,
                                        parse_mode='HTML'
                                    )
                    
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                    
                            except Exception as e:
                                logger.error(f"Error sending Instagram file {i+1}: {e}")

                    else:
                        # Single file (photo or video)
                        self.db.record_download(user_id)
                        
                        caption = self.clean_caption(result.get("caption", ""))
                        if not caption:
                            caption = self.messages["download_success"]
                        
                        if result["type"] == "photo":
                            await context.bot.send_photo(
                                chat_id=update.effective_chat.id,
                                photo=result["file_path"],
                                caption=caption,
                                parse_mode='HTML'
                            )
                        else:
                            with open(result["file_path"], 'rb') as video_file:
                                await context.bot.send_video(
                                    chat_id=update.effective_chat.id,
                                    video=video_file,
                                    caption=caption,
                                    parse_mode='HTML'
                                )
                        
                        if os.path.exists(result["file_path"]):
                            os.remove(result["file_path"])

                else:
                    await processing_msg.edit_text(
                        self.messages["download_error"].format(error=result["error"]),
                        parse_mode='HTML'
                    )

        except Exception as e:
            logger.error(f"Download error: {e}")
            await processing_msg.edit_text(
                self.messages["download_error"].format(error=str(e)),
                parse_mode='HTML'
            )

    async def vip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /vip command"""
        keyboard = []

        for days, info in self.vip_packages.items():
            price_text = f"Rp {info['price']:,}"
            button_text = f"{info['name']} - {price_text}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"vip_{days}")
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(self.messages["vip_info"], reply_markup=reply_markup, parse_mode='HTML')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        vip_info = self.db.get_vip_status(user_id)

        is_admin = user_id in self.config.ADMIN_IDS

        if is_admin:
            status = "👑 ADMIN - Unlimited access"
        elif vip_info and vip_info["is_active"]:
            status = f"✅ VIP aktif\nKadaluwarsa: {vip_info['expires_at']}"
        else:
            status = "❌ Durung VIP"

        downloads = self.db.get_daily_downloads(user_id)
        if is_admin:
            status += f"\nDownload dina iki: {downloads}/∞ (Unlimited)"
        else:
            limit = self.config.VIP_DAILY_LIMIT if vip_info and vip_info["is_active"] else self.config.FREE_DAILY_LIMIT
            status += f"\nDownload dina iki: {downloads}/{limit}"

        await update.message.reply_text(
            self.messages["vip_status"].format(status=status),
            parse_mode='HTML'
        )

    async def handle_vip_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle VIP package selection"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        callback_data = query.data

        if callback_data.startswith("vip_"):
            days = int(callback_data.split("_")[1])
            package = self.vip_packages[days]

            # Generate payment URL
            payment_url = self.trakteer.generate_payment_url(
                user_id=user_id,
                days=days,
                amount=package["price"],
                quantity=package["quantity"]
            )

            # Don't record payment yet - only when user actually pays
            await query.edit_message_text(
                self.messages["payment_generated"].format(url=payment_url),
                parse_mode='HTML'
            )

    async def admin_check_payments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to check pending payments - responds to !cek and !cp"""
        user_id = update.effective_user.id

        # Debug log
        logger.info(f"Admin check payments called by user {user_id}")

        if user_id not in self.config.ADMIN_IDS:
            await update.message.reply_text(self.messages["not_admin"], parse_mode='HTML')
            return

        # Send processing message
        processing_msg = await update.message.reply_text("🔄 Mengecek Trakteer API untuk pembayaran baru...", parse_mode='HTML')
        logger.info("Processing message sent")

        try:
            # Check API key first
            if not self.config.TRAKTEER_API_KEY or self.config.TRAKTEER_API_KEY == "your_api_key_here":
                await processing_msg.edit_text("❌ API Key Trakteer belum dikonfigurasi!", parse_mode='HTML')
                return

            # Sync payments from Trakteer
            logger.info("Starting payment sync...")
            synced_payments = await self.trakteer.sync_payments()
            logger.info(f"Sync completed, found {len(synced_payments) if synced_payments else 0} payments")

            # Debug log for API troubleshooting
            if not synced_payments:
                logger.warning("No payments found. Check API key and Trakteer account activity.")

            if not synced_payments:
                await processing_msg.edit_text("⚠️ Tidak ada pembayaran baru ditemukan atau API tidak tersedia.\n\nGunakan <code>!pend</code> untuk melihat pembayaran pending manual.",
                parse_mode="HTML"
                )
                return

            await processing_msg.edit_text(f"✅ Ditemukan {len(synced_payments)} pembayaran baru!", parse_mode='HTML')

            # Show each synced payment with details
            for payment in synced_payments:
                validation_status = "✅ Valid" if payment.get('validation_passed', False) else "⚠️ Perlu Review"

                # Use HTML formatting
                payment_text = f"""💰 <b>PEMBAYARAN TERDETEKSI:</b>

👤 <b>User ID:</b> {payment['user_id']}
👥 <b>Supporter:</b> {payment.get('supporter_name', 'Unknown')}
📅 <b>Durasi:</b> {payment['days']} hari
💵 <b>Jumlah:</b> Rp {payment['amount']:,}
🔢 <b>Quantity:</b> {payment.get('quantity', 0)}
🆔 <b>Payment ID:</b> {payment['id']}
🔗 <b>Trakteer ID:</b> {payment['trakteer_id']}
📅 <b>Created:</b> {payment['created_at']}
🔍 <b>Status:</b> {validation_status}
"""

                keyboard = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{payment['id']}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{payment['id']}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(payment_text, reply_markup=reply_markup, parse_mode='HTML')

        except Exception as e:
            error_msg = f"❌ <b>ERROR MENGECEK PEMBAYARAN:</b>\n\n<code>{str(e)}</code>\n\n💡 <b>Alternatif:</b>\n• Gunakan !pend untuk lihat pending manual\n• Periksa kembali TRAKTEER_API_KEY di config"
            await processing_msg.edit_text(error_msg, parse_mode='HTML')
            logger.error(f"Error in admin_check_payments: {e}")

    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin approval/rejection"""
        query = update.callback_query
        user_id = query.from_user.id

        if user_id not in self.config.ADMIN_IDS:
            await query.answer("Kowe ora admin!")
            return

        await query.answer()

        callback_data = query.data
        action, payment_id = callback_data.split("_", 1)
        payment_id = int(payment_id)

        payment = self.db.get_payment_by_id(payment_id)
        if not payment:
            await query.edit_message_text("Payment ora ketemu!", parse_mode='HTML')
            return

        if action == "approve":
            # Approve payment and activate VIP
            expires_at = datetime.now() + timedelta(days=payment['days'])

            # IMPORTANT: Update payment status FIRST before activating VIP
            self.db.update_payment_status(payment_id, "approved")
            logger.info(f"Payment {payment_id} status updated to 'approved'")

            # Then activate VIP
            self.db.activate_vip(payment['user_id'], expires_at)
            logger.info(f"VIP activated for user {payment['user_id']} until {expires_at}")

            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=payment['user_id'],
                    text=self.messages["payment_approved"],
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Failed to notify user {payment['user_id']} about approval: {e}")

            # Update message with detailed confirmation
            await query.edit_message_text(
                f"✅ <b>PAYMENT APPROVED!</b>\n\n"
                f"👤 <b>User:</b> {payment['user_id']}\n"
                f"💰 <b>Amount:</b> Rp {payment['amount']:,}\n"
                f"📅 <b>VIP Until:</b> {expires_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"🔄 <b>Status:</b> Payment &amp; VIP synchronized",
                parse_mode='HTML'
            )

        elif action == "reject":
            # Update payment status to rejected
            self.db.update_payment_status(payment_id, "rejected")
            logger.info(f"Payment {payment_id} status updated to 'rejected'")

            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=payment['user_id'],
                    text=self.messages["payment_rejected"],
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Failed to notify user {payment['user_id']} about rejection: {e}")

            # Update message with confirmation
            await query.edit_message_text(
                f"❌ <b>PAYMENT REJECTED!</b>\n\n"
                f"👤 <b>User:</b> {payment['user_id']}\n"
                f"💰 <b>Amount:</b> Rp {payment['amount']:,}\n"
                f"🔄 <b>Status:</b> Payment marked as rejected",
                parse_mode='HTML'
            )

    async def admin_pending_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to show pending payments list - responds to !pend and !pa"""
        user_id = update.effective_user.id

        # Debug log
        logger.info(f"Admin pending list called by user {user_id}")

        if user_id not in self.config.ADMIN_IDS:
            await update.message.reply_text(self.messages["not_admin"], parse_mode='HTML')
            return

        # ENHANCED AUTO-SYNC: Fix multiple types of inconsistencies
        pending_payments = self.db.get_pending_payments()
        auto_fixed = 0
        old_transactions_cleaned = 0

        from datetime import datetime, timedelta

        for payment in pending_payments[:]:  # Copy list to modify during iteration
            user_id_check = payment['user_id']
            vip_status = self.db.get_vip_status(user_id_check)

            # Auto-fix 1: User has active VIP but payment still pending
            if vip_status and vip_status.get('is_active'):
                self.db.update_payment_status(payment['id'], 'approved')
                auto_fixed += 1
                logger.info(f"Auto-fixed payment {payment['id']} for user {user_id_check} - VIP already active until {vip_status['expires_at']}")
                continue

# Auto-fix 2: Clean up very old pending payments (older than 7 days)
            try:
                payment_time = datetime.fromisoformat(payment['created_at'])
                if datetime.now() - payment_time > timedelta(days=7):
                    self.db.update_payment_status(payment['id'], 'expired')
                    old_transactions_cleaned += 1
                    logger.info(f"Auto-cleaned old payment {payment['id']} from {payment['created_at']}")
                    continue
            except Exception:
                pass

        # Get updated pending payments after auto-fix
        pending_payments = self.db.get_pending_payments()
        logger.info(f"Found {len(pending_payments)} pending payments (auto-fixed {auto_fixed})")

        if not pending_payments:
            cleanup_msg = ""
            if auto_fixed > 0 or old_transactions_cleaned > 0:
                cleanup_msg = f"\n\n🔧 <b>Auto-maintenance:</b>\n"
                if auto_fixed > 0:
                    cleanup_msg += f"• Fixed {auto_fixed} sinkronisasi VIP\n"
                if old_transactions_cleaned > 0:
                    cleanup_msg += f"• Cleaned {old_transactions_cleaned} transaksi lama"

            await update.message.reply_text(
                f"📭 <b>TIDAK ADA PEMBAYARAN PENDING</b>{cleanup_msg}\n\n"
                f"Gunakan <code>!cek</code> untuk mengecek pembayaran baru dari Trakteer.", 
                parse_mode='HTML'
            )
            return

        message = "📝 <b>DAFTAR PEMBAYARAN PENDING:</b>\n\n"

        if auto_fixed > 0 or old_transactions_cleaned > 0:
            message += f"🔧 <b>Auto-maintenance:</b> "
            if auto_fixed > 0:
                message += f"Fixed {auto_fixed} VIP sinkron, "
            if old_transactions_cleaned > 0:
                message += f"Cleaned {old_transactions_cleaned} transaksi lama"
            message += "\n\n"

        for i, payment in enumerate(pending_payments[:10], 1):  # Limit to 10
            message += f"<b>#{i}</b> (ID: {payment['id']})\n"
            message += f"👤 <b>User:</b> {payment['user_id']}\n"
            message += f"📦 <b>Package:</b> {payment['days']} hari VIP\n"
            message += f"💰 <b>Amount:</b> Rp {payment['amount']:,}\n"
            message += f"📅 <b>Created:</b> {payment['created_at']}\n"
            message += f"📄 <b>Status:</b> {payment.get('status', 'pending')}\n"

            if payment.get('trakteer_id'):
                message += f"🔗 <b>Trakteer ID:</b> {payment['trakteer_id']}\n"

            message += "\n"

        if len(pending_payments) > 10:
            message += f"📄 <i>Menampilkan 10 dari {len(pending_payments)} pembayaran pending</i>\n\n"

        message += "💡 <b>Actions:</b>\n"
        message += "• Gunakan tombol dibawah untuk approve/reject\n"
        message += "• Atau gunakan !cek untuk sync pembayaran baru"

        # Create inline keyboard for actions
        keyboard = []
        for payment in pending_payments[:5]:  # Limit to first 5 for UI readability
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve #{payment['id']}", callback_data=f"approve_{payment['id']}"),
                InlineKeyboardButton(f"❌ Reject #{payment['id']}", callback_data=f"reject_{payment['id']}")
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

    async def admin_list_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to list all VIP users - responds to !listvip"""
        user_id = update.effective_user.id

        logger.info(f"Admin list VIP called by user {user_id}")

        if user_id not in self.config.ADMIN_IDS:
            await update.message.reply_text(self.messages["not_admin"], parse_mode='HTML')
            return

        try:
            # Get VIP users from database
            vip_users = self.db.get_vip_users()
            logger.info(f"Found {len(vip_users)} VIP users")

            if not vip_users:
                await update.message.reply_text("📭 <b>TIDAK ADA USER VIP AKTIF</b>", parse_mode='HTML')
                return

            message = "👑 <b>DAFTAR USER VIP AKTIF:</b>\n\n"

            for i, user in enumerate(vip_users[:20], 1):  # Limit to 20
                # Proper HTML escaping
                username = str(user.get('username', 'Unknown'))
                # Remove any problematic characters and escape properly
                username = username.replace('<', '').replace('>', '').replace('&', '').replace('"', '')
                expires_at = str(user['vip_expires_at'])

                message += f"<b>#{i}</b>\n"
                message += f"👤 <b>User ID:</b> <code>{user['user_id']}</code>\n"
                message += f"📅 <b>VIP Expires:</b> {expires_at}\n"
                message += f"📊 <b>Status:</b> {'✅ Active' if user['is_active'] else '❌ Expired'}\n"
                message += "\n"

            if len(vip_users) > 20:
                message += f"📄 <i>Menampilkan 20 dari {len(vip_users)} user VIP</i>\n\n"

            message += "💡 <b>Actions:</b>\n"
            message += "• Gunakan <code>!delvip</code> untuk hapus VIP user"
            await update.message.reply_text(message, parse_mode='HTML')

        except Exception as e:
            logger.error(f"Error in admin_list_vip: {e}")
            await update.message.reply_text(
                f"❌ <b>ERROR:</b>\n\n<code>{str(e)}</code>",
                parse_mode='HTML'
            )

    async def admin_delete_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to delete VIP status - responds to !delvip <user_id>"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()

        logger.info(f"Admin delete VIP called by user {user_id}: {message_text}")

        if user_id not in self.config.ADMIN_IDS:
            await update.message.reply_text(self.messages["not_admin"], parse_mode='HTML')
            return

        # Extract target user ID from command
        try:
            target_user_id = int(message_text.split()[1])
        except (IndexError, ValueError):
            await update.message.reply_text(
                "❌ <b>FORMAT SALAH COK!</b>\n\n"
                "Gunakan: <code>!delvip &lt;user_id&gt;</code>\n"
                "Contoh: <code>!delvip 1234567890</code>",
                parse_mode='HTML'
            )
            return

        # Check if user exists and has VIP
        vip_status = self.db.get_vip_status(target_user_id)
        if not vip_status or not vip_status.get('is_active'):
            await update.message.reply_text(
                f"❌ <b>USER {target_user_id} TIDAK MEMILIKI VIP AKTIF</b>",
                parse_mode='HTML'
            )
            return

        # Remove VIP status
        try:
            self.db.remove_vip(target_user_id)

            # Notify the user that their VIP was removed
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="⚠️ <b>VIP status kamu telah dihapus oleh admin cok!</b>",
                    parse_mode='HTML'
                )
            except Exception:
                logger.warning(f"Could not notify user {target_user_id} about VIP removal")

            await update.message.reply_text(
                f"✅ <b>VIP STATUS BERHASIL DIHAPUS!</b>\n\n"
                f"👤 <b>User ID:</b> {target_user_id}\n"
                f"📅 <b>Dihapus pada:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode='HTML'
            )

            logger.info(f"VIP status removed for user {target_user_id} by admin {user_id}")

        except Exception as e:
            await update.message.reply_text(
                f"❌ <b>ERROR MENGHAPUS VIP:</b>\n\n<code>{str(e)}</code>",
                parse_mode='HTML'
            )
            logger.error(f"Error removing VIP for user {target_user_id}: {e}")

    async def admin_debug(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin debug command to check system status"""
        user_id = update.effective_user.id

        if user_id not in self.config.ADMIN_IDS:
            await update.message.reply_text(self.messages["not_admin"], parse_mode='HTML')
            return

        try:
            # Get debug info
            debug_info = self.db.debug_payment_status()
            user_stats = self.db.get_user_stats()

            message = "🔧 <b>DEBUG INFO:</b>\n\n"

            # Payment status breakdown
            message += "📊 <b>Payment Status:</b>\n"
            for status, count in debug_info['status_counts'].items():
                message += f"• {status}: {count}\n"

            message += f"\n👑 <b>Active VIP Users:</b> {debug_info['active_vip_count']}\n"
            message += f"📈 <b>Total Users:</b> {user_stats['total_users']}\n"

            # Recent payments
            message += "\n📋 <b>Recent 5 Payments:</b>\n"
            for payment in debug_info['recent_payments'][:5]:
                message += f"• <b>ID:</b>{payment[0]} <b>User:</b>{payment[1]} <b>Status:</b>{payment[4]}\n"

            await update.message.reply_text(message, parse_mode='HTML')

        except Exception as e:
            await update.message.reply_text(f"❌ <b>Debug error:</b> <code>{str(e)}</code>", parse_mode='HTML')

    async def cleanup_expired_vip(self, context: ContextTypes.DEFAULT_TYPE):
        """Clean up expired VIP users"""
        self.db.cleanup_expired_vip()

    def run(self):
        """Run the bot with comprehensive error handling"""
        try:
            # Test configuration
            logger.info("Testing bot configuration...")
            test_app = Application.builder().token(self.config.BOT_TOKEN).build()

            # Test database connection
            logger.info("Testing database connection...")
            self.db.get_user_stats()

            logger.info("✅ All tests passed, starting bot...")

            application = Application.builder().token(self.config.BOT_TOKEN).build()

            # Add handlers
            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(CommandHandler("vip", self.vip_command))
            application.add_handler(CommandHandler("status", self.status_command))
            # Admin commands dengan pattern yang lebih robust
            application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^!cek\s*$"), self.admin_check_payments))
            application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^!pend\s*$"), self.admin_pending_list))
            application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^!cp\s*$"), self.admin_check_payments))  # Alias
            application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^!pa\s*$"), self.admin_pending_list))    # Alias
            application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^!listvip\s*$"), self.admin_list_vip))
            application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^!delvip\s+\d+\s*$"), self.admin_delete_vip))
            # Debug handler untuk semua text messages
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
            application.add_handler(CallbackQueryHandler(self.handle_vip_callback, pattern="^vip_"))
            application.add_handler(CallbackQueryHandler(self.handle_admin_callback, pattern="^(approve|reject)_"))

            # Add job queue for VIP cleanup
            job_queue = application.job_queue
            if job_queue:
                job_queue.run_repeating(self.cleanup_expired_vip, interval=3600)  # Every hour

            # Start bot
            logger.info("🚀 Bot starting...")
            application.run_polling(allowed_updates=Update.ALL_TYPES)

        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: Bot failed to start - {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        logger.info("🤖 Initializing Javanese TikTok Bot...")
        bot = JawaneseTikTokBot()
        bot.run()
    except ValueError as e:
        logger.error(f"❌ Configuration Error: {e}")
        print(f"❌ Configuration Error: {e}")
        print("💡 Check your environment variables (.env file)")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal Error: {e}")
        print(f"❌ Fatal Error: {e}")
        sys.exit(1)
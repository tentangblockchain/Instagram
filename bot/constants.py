"""Configuration constants and fixed data structures"""

VIP_PACKAGES = {
    3: {"price": 5000, "name": "3 dina", "quantity": 1},
    7: {"price": 10000, "name": "7 dina", "quantity": 2},
    15: {"price": 20000, "name": "15 dina", "quantity": 4},
    30: {"price": 35000, "name": "30 dina", "quantity": 7},
    60: {"price": 60000, "name": "60 dina", "quantity": 12},
    90: {"price": 80000, "name": "90 dina", "quantity": 16}
}

JAVANESE_MESSAGES = {
    "welcome": """
🌸 <b>Hai! Selamat datang di Bot Downloader</b> 🌸

<code>✨ TikTok &amp; Instagram Downloader Pro ✨</code>

<blockquote>Kirim link TikTok atau Instagram kamu, atau ketik <code>/vip</code> untuk upgrade akun ya!</blockquote>

<i>⚡ Gratis tapi ada batasnya • 💎 VIP unlimited download</i>
""",

    "not_member": """
🙏 <b>Halo kak! Boleh join channel dulu ya~</b>

<blockquote>📢 Mohon join semua channel ini dulu:
{channels}</blockquote>

<i>Setelah join, kakak bisa langsung download konten favorit! 💕</i>
""",

    "daily_limit": """
⏰ <b>Yah, limit download hari ini sudah habis nih kak</b>

<blockquote>📊 Download hari ini: <code>{current}/{limit}</code></blockquote>

<i>💎 Upgrade ke VIP untuk unlimited download, atau tunggu besok ya kak! ✨</i>
""",

    "invalid_url": """
❌ <b>Ups! Link-nya sepertinya belum benar nih kak</b>

<blockquote>🔗 Pastikan kirim link yang benar ya:
• <code>TikTok</code> (tiktok.com, vt.tiktok.com, vm.tiktok.com)
• <code>Instagram</code> (instagram.com, instagr.am)</blockquote>
""",

    "processing": """
⏳ <b>Sebentar ya kak, lagi diproses...</b>

<blockquote><code>🔄 Sedang mengunduh konten...</code></blockquote>

<i>Ditunggu sebentar aja ya, file kakak sedang disiapkan! 💫</i>
""",

    "download_success": """
✅ <b>Yeay! Berhasil!</b>

<blockquote><code>📁 File kakak sudah siap!</code></blockquote>

<i>Selamat menikmati kontennya! 🎉</i>
""",

    "carousel_success": """
✅ <b>Sukses! Album berhasil diunduh</b>

<blockquote><code>📸 Carousel/Album berhasil diunduh!</code>
<b>Total file:</b> {count}</blockquote>

<i>Semua file sudah dikirim ya kak! 🎊</i>
""",

    "download_error": """
❌ <b>Maaf kak, ada kendala nih</b>

<blockquote><code>⚠️ Tidak bisa download:</code>
{error}</blockquote>

<i>Coba lagi ya kak, atau pakai link yang lain! 🙏</i>
""",

    "payment_generated": """
💳 <b>Link Pembayaran Sudah Dibuat!</b>

<blockquote>🔗 Silakan klik tombol "Bayar Sekarang" di bawah ini ya kak</blockquote>

<b>⚠️ Penting banget nih:</b>
<i>Pembayaran akan otomatis terdeteksi setelah kakak benar-benar bayar. Jangan cuma klik tombol aja ya! 😊</i>

<tg-spoiler>Biasanya diproses dalam 1-24 jam</tg-spoiler>
""",

    "payment_pending": """
⏳ <b>Pembayaran Sedang Diproses</b>

<blockquote><code>🔄 Status: Menunggu persetujuan admin</code></blockquote>

<i>Sabar ya kak, admin sedang mengecek pembayaran kakak! 💕</i>
""",

    "payment_approved": """
🎉 <b>Selamat! Pembayaran Disetujui</b>

<blockquote><code>✅ Pembayaran kakak sudah diapprove!</code>
<b>Status VIP:</b> <u>AKTIF SEKARANG</u></blockquote>

<i>Selamat menikmati fitur VIP unlimited ya kak! 🚀✨</i>
""",

    "payment_rejected": """
❌ <b>Maaf, Pembayaran Ditolak</b>

<blockquote><code>⚠️ Alasan: Pembayaran tidak valid</code></blockquote>

<i>Pastikan sudah benar-benar bayar ya kak! Kalau ada kendala, hubungi admin ya 🙏</i>
""",

    "payment_detected": """
💰 <b>Pembayaran Terdeteksi!</b>

<blockquote><code>🔍 Status: Menunggu persetujuan admin</code></blockquote>

<i>Pembayaran kakak sudah masuk, tunggu admin approve ya! 💕</i>
""",

    "not_admin": """
🚫 <b>Maaf, Akses Terbatas</b>

<blockquote><code>⛔ Command ini hanya untuk admin</code></blockquote>
""",

    "vip_status": """
👑 <b>Status VIP Kakak</b>

<blockquote>{status}</blockquote>

<i>Terima kasih sudah menjadi VIP member! 🙏✨</i>
""",
}

TELEGRAM_CONSTANTS = {
    "BOT_USERNAME": "@jawaneseTikTokDownloader",
    "SUPPORT_TIMEOUT": 10,
    "DOWNLOAD_TIMEOUT": 15,
}

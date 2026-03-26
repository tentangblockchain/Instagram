VIP_PACKAGES = {
    3:  {"price": 5000,  "name": "3 Hari"},
    7:  {"price": 10000, "name": "7 Hari"},
    15: {"price": 20000, "name": "15 Hari"},
    30: {"price": 35000, "name": "30 Hari"},
    60: {"price": 60000, "name": "60 Hari"},
    90: {"price": 80000, "name": "90 Hari"},
}

MESSAGES = {
    "welcome": (
        "🌸 <b>Hai! Selamat datang di Bot Downloader</b>\n\n"
        "<code>✨ TikTok &amp; Instagram Downloader Pro ✨</code>\n\n"
        "<blockquote>Kirim link TikTok atau Instagram, atau ketik <code>/vip</code> untuk upgrade akun!</blockquote>\n\n"
        "<i>⚡ Gratis tapi ada batasnya • 💎 VIP unlimited download</i>"
    ),

    "not_member": (
        "🙏 <b>Halo kak! Boleh join channel dulu ya~</b>\n\n"
        "<blockquote>📢 Join channel berikut dulu:\n{channels}</blockquote>\n\n"
        "<i>Setelah join bisa langsung download! 💕</i>"
    ),

    "daily_limit": (
        "⏰ <b>Limit download hari ini sudah habis kak</b>\n\n"
        "<blockquote>📊 Download hari ini: <code>{current}/{limit}</code></blockquote>\n\n"
        "<i>💎 Upgrade ke VIP untuk unlimited download, atau tunggu besok! ✨</i>"
    ),

    "invalid_url": (
        "❌ <b>Link belum benar kak</b>\n\n"
        "<blockquote>🔗 Kirim link yang valid:\n"
        "• <code>TikTok</code> — tiktok.com, vt.tiktok.com, vm.tiktok.com\n"
        "• <code>Instagram</code> — instagram.com, instagr.am</blockquote>"
    ),

    "processing": (
        "⏳ <b>Sebentar ya kak, lagi diproses...</b>\n\n"
        "<blockquote><code>🔄 Sedang mengunduh konten...</code></blockquote>\n\n"
        "<i>Sabar sebentar, file kamu sedang disiapkan! 💫</i>"
    ),

    "download_success": (
        "✅ <b>Berhasil!</b>\n\n"
        "<blockquote><code>📁 File kamu sudah siap!</code></blockquote>\n\n"
        "<i>Selamat menikmati! 🎉</i>"
    ),

    "carousel_success": (
        "✅ <b>Album berhasil diunduh</b>\n\n"
        "<blockquote><code>📸 Total file: {count}</code></blockquote>\n\n"
        "<i>Semua file sudah dikirim! 🎊</i>"
    ),

    "download_error": (
        "❌ <b>Maaf kak, ada kendala</b>\n\n"
        "<blockquote><code>⚠️ {error}</code></blockquote>\n\n"
        "<i>Coba lagi atau pakai link lain! 🙏</i>"
    ),

    "vip_info": (
        "💎 <b>Paket VIP Premium</b>\n\n"
        "<blockquote><code>🌟 Pilih paket yang cocok:</code></blockquote>\n\n"
        "• <code>3 hari</code>  — <b>Rp 5.000</b>\n"
        "• <code>7 hari</code>  — <b>Rp 10.000</b>\n"
        "• <code>15 hari</code> — <b>Rp 20.000</b>\n"
        "• <code>30 hari</code> — <b>Rp 35.000</b>\n"
        "• <code>60 hari</code> — <b>Rp 60.000</b>\n"
        "• <code>90 hari</code> — <b>Rp 80.000</b>\n\n"
        "<i>⚡ VIP: Download unlimited + prioritas support! 💕</i>"
    ),

    "vip_status": (
        "👑 <b>Status VIP Kamu</b>\n\n"
        "<blockquote>{status}</blockquote>\n\n"
        "<i>Terima kasih sudah jadi VIP member! 🙏✨</i>"
    ),

    "qr_caption": (
        "💳 <b>Scan QR untuk Bayar VIP {days} Hari</b>\n\n"
        "💰 <b>Nominal:</b> Rp {amount:,}\n"
        "🏦 <b>Metode:</b> QRIS (semua e-wallet &amp; m-banking)\n"
        "⏱ <b>Berlaku:</b> 15 menit\n\n"
        "<i>VIP otomatis aktif setelah pembayaran terdeteksi! 🚀</i>"
    ),

    "payment_success": (
        "🎉 <b>Pembayaran Berhasil!</b>\n\n"
        "<blockquote>✅ VIP <b>{days} hari</b> sudah aktif!\n"
        "Berlaku sampai: <code>{expires}</code></blockquote>\n\n"
        "<i>Selamat menikmati download unlimited! 🚀✨</i>"
    ),

    "payment_failed": (
        "❌ <b>Pembayaran Gagal/Dibatalkan</b>\n\n"
        "<blockquote>Transaksi tidak berhasil atau dibatalkan.</blockquote>\n\n"
        "<i>Silakan coba lagi via /vip 🙏</i>"
    ),

    "payment_expired": (
        "⏰ <b>QR Kadaluarsa</b>\n\n"
        "<blockquote>Waktu pembayaran 15 menit sudah habis.</blockquote>\n\n"
        "<i>Silakan generate QR baru via /vip 🙏</i>"
    ),

    "qr_generating": (
        "⏳ <b>Membuat QR pembayaran...</b>\n\n"
        "<i>Sebentar ya kak 💫</i>"
    ),

    "qr_error": (
        "❌ <b>Gagal membuat pembayaran</b>\n\n"
        "<blockquote><code>{error}</code></blockquote>\n\n"
        "<i>Coba lagi via /vip ya kak 🙏</i>"
    ),

    "not_admin": (
        "🚫 <b>Akses Terbatas</b>\n\n"
        "<blockquote><code>⛔ Command ini hanya untuk admin</code></blockquote>"
    ),

    "help_user": (
        "🌸 <b>Panduan Bot Downloader</b>\n\n"
        "<b>📌 Command:</b>\n"
        "• <code>/start</code> — Mulai bot\n"
        "• <code>/vip</code> — Lihat &amp; beli paket VIP\n"
        "• <code>/status</code> — Cek status VIP kamu\n"
        "• <code>/help</code> — Bantuan\n\n"
        "<b>📥 Cara Download:</b>\n"
        "<blockquote>Kirim link langsung:\n"
        "• TikTok — vt.tiktok.com, vm.tiktok.com\n"
        "• Instagram — Post, reels, carousel</blockquote>\n\n"
        "<b>💎 Paket VIP:</b>\n"
        "<pre>"
        "3 hari  → Rp 5.000\n"
        "7 hari  → Rp 10.000\n"
        "15 hari → Rp 20.000\n"
        "30 hari → Rp 35.000\n"
        "60 hari → Rp 60.000\n"
        "90 hari → Rp 80.000"
        "</pre>\n\n"
        "<b>⚠️ Limit:</b>\n"
        "<blockquote>• Gratis: 10 download/hari\n"
        "• VIP: 100 download/hari</blockquote>\n\n"
        "<i>🎉 Selamat menggunakan bot! 💕</i>"
    ),

    "help_admin": (
        "🔐 <b>Panduan Admin</b>\n\n"
        "<b>🛠 Command Admin:</b>\n"
        "• <code>!listvip</code> — Daftar semua VIP aktif\n"
        "• <code>!delvip &lt;user_id&gt;</code> — Hapus VIP user\n"
        "• <code>!stats</code> — Statistik bot\n\n"
        "<b>💳 Alur Pembayaran Saweria:</b>\n"
        "<blockquote>\n"
        "1. User ketik /vip → pilih paket\n"
        "2. Bot buat QR QRIS via Saweria\n"
        "3. User scan &amp; bayar\n"
        "4. Bot polling otomatis (tiap 7 detik)\n"
        "5. VIP aktif otomatis setelah bayar ✅\n"
        "</blockquote>\n\n"
        "<i>Tidak perlu approve manual!</i>"
    ),
}

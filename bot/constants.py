VIP_PACKAGES = {
    3:  {"price": 1000,  "name": "3 Hari"},
    7:  {"price": 50000, "name": "7 Hari"},
    15: {"price": 10000, "name": "15 Hari"},
    30: {"price": 15000, "name": "30 Hari"},
    60: {"price": 20000, "name": "60 Hari"},
    90: {"price": 25000, "name": "90 Hari"},
}

MESSAGES = {
    "welcome": (
        "🌸 <b>Hai! Selamat datang di Bot Downloader</b>\n\n"
        "<code>✨ TikTok &amp; Instagram Downloader Pro ✨</code>\n\n"
        "<i>Pilih menu di bawah untuk mulai!</i>"
    ),

    "main_menu": (
        "🏠 <b>Menu Utama</b>\n\n"
        "Pilih menu di bawah ini:"
    ),

    "cara_dl": (
        "📥 <b>Cara Download</b>\n\n"
        "<blockquote>Cukup kirim link langsung ke bot ini!\n\n"
        "• <b>TikTok</b>\n"
        "  <code>tiktok.com</code> / <code>vt.tiktok.com</code> / <code>vm.tiktok.com</code>\n\n"
        "• <b>Instagram</b>\n"
        "  <code>instagram.com</code> / <code>instagr.am</code>\n"
        "  (Post, Reels, Carousel)</blockquote>\n\n"
        "<b>⚠️ Limit Download:</b>\n"
        "• Gratis: <code>10 download/hari</code>\n"
        "• VIP: <code>100 download/hari</code>\n\n"
        "<i>Upgrade VIP untuk download lebih banyak! 💎</i>"
    ),

    "not_member": (
        "🙏 <b>Halo kak! Boleh join channel dulu ya~</b>\n\n"
        "<blockquote>📢 Join channel berikut dulu:\n{channels}</blockquote>\n\n"
        "<i>Setelah join bisa langsung download! 💕</i>"
    ),

    "daily_limit": (
        "⏰ <b>Limit download hari ini sudah habis kak</b>\n\n"
        "<blockquote>📊 Download hari ini: <code>{current}/{limit}</code></blockquote>\n\n"
        "<i>💎 Upgrade ke VIP untuk download lebih banyak, atau tunggu besok! ✨</i>"
    ),

    "invalid_url": (
        "❌ <b>Link belum benar kak</b>\n\n"
        "<blockquote>🔗 Kirim link yang valid:\n"
        "• <code>TikTok</code> — tiktok.com, vt.tiktok.com\n"
        "• <code>Instagram</code> — instagram.com</blockquote>"
    ),

    "processing": (
        "⏳ <b>Sebentar ya kak, lagi diproses...</b>\n\n"
        "<blockquote><code>🔄 Sedang mengunduh konten...</code></blockquote>\n\n"
        "<i>Sabar sebentar, file kamu sedang disiapkan! 💫</i>"
    ),

    "download_success": (
        "✅ <b>Berhasil!</b>\n\n"
        "<blockquote><code>📁 File kamu sudah siap!</code></blockquote>"
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
        "💎 <b>Upgrade VIP Premium</b>\n\n"
        "<blockquote>Pilih durasi paket VIP kamu:</blockquote>\n\n"
        "• <code>3 hari</code>  — <b>Rp 1.000</b>\n"
        "• <code>7 hari</code>  — <b>Rp 50.000</b>\n"
        "• <code>15 hari</code> — <b>Rp 10.000</b>\n"
        "• <code>30 hari</code> — <b>Rp 15.000</b>\n"
        "• <code>60 hari</code> — <b>Rp 20.000</b>\n"
        "• <code>90 hari</code> — <b>Rp 25.000</b>\n\n"
        "<i>Pembayaran via QRIS, VIP aktif otomatis! 🚀</i>"
    ),

    "vip_status": (
        "👑 <b>Status Akun Kamu</b>\n\n"
        "<blockquote>{status}</blockquote>"
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
        "<i>Selamat menikmati download tanpa batas! 🚀✨</i>"
    ),

    "payment_failed": (
        "❌ <b>Pembayaran Gagal/Dibatalkan</b>\n\n"
        "<blockquote>Transaksi tidak berhasil.</blockquote>\n\n"
        "<i>Silakan coba lagi lewat menu VIP 🙏</i>"
    ),

    "payment_expired": (
        "⏰ <b>QR Kadaluarsa</b>\n\n"
        "<blockquote>Waktu pembayaran 15 menit sudah habis.</blockquote>\n\n"
        "<i>Silakan generate QR baru lewat menu VIP 🙏</i>"
    ),

    "qr_generating": (
        "⏳ <b>Membuat QR pembayaran...</b>\n\n"
        "<i>Sebentar ya kak 💫</i>"
    ),

    "qr_error": (
        "❌ <b>Gagal membuat pembayaran</b>\n\n"
        "<blockquote><code>{error}</code></blockquote>\n\n"
        "<i>Coba lagi lewat menu VIP ya kak 🙏</i>"
    ),

    "free_vip_join_channels": (
        "🎁 <b>VIP Gratis 1 Hari</b>\n\n"
        "<blockquote>📢 Klik semua tombol channel di bawah untuk join, "
        "lalu tekan <b>🎁 Sudah Join — Klaim VIP Gratis!</b> 💕\n\n"
        "⚠️ Harus join <b>semua {count} channel</b> ya kak!</blockquote>"
    ),

    "free_vip_not_member": (
        "❌ <b>Belum Join Semua Channel</b>\n\n"
        "<blockquote>Bot mendeteksi kamu belum join semua channel sponsor.\n\n"
        "Klik tombol-tombol di bawah, join semua, lalu tekan klaim lagi! 🙏</blockquote>"
    ),

    "free_vip_already_active": (
        "✅ <b>VIP Kamu Masih Aktif!</b>\n\n"
        "<blockquote>VIP berlaku sampai: <code>{expires}</code></blockquote>\n\n"
        "<i>Klaim lagi setelah VIP habis ya kak~ 💎</i>"
    ),

    "free_vip_success": (
        "🎉 <b>VIP Gratis Berhasil Diklaim!</b>\n\n"
        "<blockquote>✅ VIP <b>1 hari</b> sudah aktif!\n"
        "Berlaku sampai: <code>{expires}</code></blockquote>\n\n"
        "<i>Klaim lagi besok dengan tetap stay di channel sponsor ya! 🌸</i>"
    ),

    "free_vip_no_channels": (
        "⚙️ <b>VIP Gratis Belum Dikonfigurasi</b>\n\n"
        "<blockquote>Fitur ini memerlukan channel sponsor.\n"
        "Hubungi admin untuk informasi lebih lanjut.</blockquote>"
    ),

    "not_admin": (
        "🚫 <b>Akses Terbatas</b>\n\n"
        "<blockquote><code>⛔ Menu ini hanya untuk admin</code></blockquote>"
    ),

    "help_user": (
        "🌸 <b>Panduan Bot Downloader</b>\n\n"
        "<b>📌 Command:</b>\n"
        "• <code>/start</code> — Buka menu utama\n"
        "• <code>/help</code> — Tampilkan bantuan ini\n\n"
        "<b>📥 Cara Download:</b>\n"
        "<blockquote>Kirim link TikTok atau Instagram langsung ke chat ini. "
        "Bot akan otomatis mengunduh dan mengirimkan file ke kamu!</blockquote>\n\n"
        "<b>💎 Fitur VIP:</b>\n"
        "<blockquote>Buka menu utama → <b>Upgrade VIP</b>\n"
        "Pilih paket → Scan QR → VIP aktif otomatis!</blockquote>\n\n"
        "<i>Ada pertanyaan? Hubungi admin ya! 💕</i>"
    ),

    "help_admin": (
        "🔐 <b>Panduan Admin</b>\n\n"
        "<b>📌 Command:</b>\n"
        "• <code>/start</code> — Buka menu utama (ada panel admin)\n"
        "• <code>/help</code> — Bantuan ini\n\n"
        "<b>🛠 Menu Admin</b> (di menu utama → Admin Panel):\n"
        "• <b>👥 List VIP</b> — Daftar VIP aktif\n"
        "• <b>📊 Statistik</b> — Statistik bot\n\n"
        "<b>✏️ Command teks:</b>\n"
        "• <code>!delvip &lt;user_id&gt;</code> — Hapus VIP user\n\n"
        "<b>💳 Alur Pembayaran Saweria (Otomatis):</b>\n"
        "<blockquote>User pilih paket → Bot buat QRIS → User bayar → "
        "Bot polling 7 detik → VIP aktif sendiri ✅</blockquote>"
    ),
}

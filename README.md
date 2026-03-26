# 🤖 Bot Downloader TikTok & Instagram

Bot Telegram untuk mengunduh konten **TikTok** dan **Instagram** lengkap dengan sistem **VIP subscription** dan pembayaran **QRIS otomatis via Saweria**.

---

## ✨ Fitur Utama

### 📥 Download Konten
| Platform | Format | Keterangan |
|----------|--------|------------|
| TikTok | Video, Foto/Slideshow | Support link pendek `vt.tiktok.com`, `vm.tiktok.com` |
| Instagram | Post, Reels, Carousel | Carousel dikirim satu per satu dengan nomor urut |

- Caption konten otomatis disertakan
- File dikirim langsung ke chat

### 💎 Sistem VIP
| Tipe | Limit Download/Hari |
|------|---------------------|
| Gratis | 10 |
| VIP | 100 |

**Paket VIP:**
| Durasi | Harga |
|--------|-------|
| 3 Hari | Rp 1.000 |
| 7 Hari | Rp 50.000 |
| 15 Hari | Rp 10.000 |
| 30 Hari | Rp 15.000 |
| 60 Hari | Rp 20.000 |
| 90 Hari | Rp 25.000 |

### 💳 Pembayaran QRIS Otomatis (Saweria)
- Bot generate QR Code QRIS langsung di chat
- Support semua e-wallet & mobile banking (GoPay, OVO, Dana, BCA, BRI, dll.)
- Bot polling otomatis setiap **7 detik**, maksimal **15 menit**
- VIP **aktif sendiri** begitu pembayaran terdeteksi — tanpa perlu konfirmasi admin

### 🔒 Keamanan
- Wajib join channel sebelum bisa download (dapat dinonaktifkan)
- Sistem limit harian mencegah penyalahgunaan
- Semua aktivitas tercatat di database SQLite

---

## 🗂 Struktur Proyek

```
bot/
├── config.py          # Konfigurasi dari environment variables
├── constants.py       # Semua teks pesan & paket VIP
├── database.py        # SQLite: user, VIP, payment, download log
├── main.py            # Entry point, handler, menu sistem
├── payment/
│   └── saweria.py     # Saweria API: buat donasi, generate QR, cek status
└── downloaders/
    ├── tiktok.py      # Download TikTok via yt-dlp
    └── instagram.py   # Download Instagram via yt-dlp + gallery-dl
```

---

## 🚀 Setup & Instalasi

### Prasyarat
- Python 3.11+
- Akun [Saweria](https://saweria.co) (untuk pembayaran)
- Telegram Bot Token dari [@BotFather](https://t.me/BotFather)

### 1. Clone & Install

```bash
git clone https://github.com/tentangblockchain/Instagram.git
cd Instagram
pip install -r requirements.txt
```

### 2. Konfigurasi Environment

Buat file `.env` dari contoh:

```bash
cp .env.example .env
```

Isi variabel berikut:

```env
# Wajib
BOT_TOKEN=token_dari_botfather
ADMIN_IDS=123456789,987654321

# Saweria (untuk pembayaran QRIS)
SAWERIA_USERNAME=username_saweria_kamu
SAWERIA_USER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Opsional
REQUIRED_CHANNEL=@channelmu
FREE_DAILY_LIMIT=10
VIP_DAILY_LIMIT=100
DATABASE_PATH=database.db
```

> **Cara dapat `SAWERIA_USER_ID`:**
> Buka `saweria.co/usernamemu` → F12 → tab Network → cari request ke endpoint `snap` → salin nilai `user_id` (format UUID).

### 3. Jalankan Bot

```bash
python -m bot.main
```

---

## 📱 Cara Pakai (User)

### Download Konten
Cukup kirim link langsung ke chat bot — tidak perlu command apapun.

```
https://vt.tiktok.com/ZSxxxx
https://www.instagram.com/p/xxxx/
```

### Menu Utama (`/start`)

```
🏠 Menu Utama
├── 💎 Upgrade VIP     → Pilih paket → Scan QR → VIP aktif otomatis
├── 👑 Status VIP      → Cek status & sisa download hari ini
└── 📥 Cara Download   → Panduan singkat
```

Untuk admin, muncul tambahan:
```
└── 🔐 Admin Panel
    ├── 👥 List VIP    → Daftar semua VIP aktif
    └── 📊 Statistik   → Statistik bot
```

---

## ⌨️ Command

| Command | Deskripsi | Akses |
|---------|-----------|-------|
| `/start` | Buka menu utama | Semua user |
| `/help` | Panduan penggunaan | Semua user |
| `!delvip <user_id>` | Hapus VIP user tertentu | Admin only |

> Semua fitur lain (VIP, status, statistik, list VIP) tersedia melalui tombol menu — tidak perlu command.

---

## 🔄 Alur Pembayaran VIP

```
User klik "Upgrade VIP"
    → Pilih paket (misal: 30 Hari - Rp 15.000)
        → Bot buat donasi di Saweria
            → Bot kirim QR Code QRIS ke chat
                → User scan & bayar (maks. 15 menit)
                    → Bot polling status setiap 7 detik
                        → Pembayaran terdeteksi
                            → VIP aktif otomatis ✅
```

---

## 🛠 Dependencies Utama

| Package | Fungsi |
|---------|--------|
| `python-telegram-bot==21.5` | Framework bot Telegram |
| `yt-dlp` | Download TikTok & Instagram |
| `gallery-dl` | Fallback download Instagram carousel |
| `qrcode` + `Pillow` | Generate gambar QR Code |
| `python-dotenv` | Baca file `.env` |
| `APScheduler` | Cleanup VIP expired terjadwal |

> Saweria API menggunakan `curl` via subprocess untuk bypass Cloudflare TLS fingerprinting (Python HTTP client diblokir Saweria).

---

## 🗄 Database Schema

```sql
users          -- user_id, username, registered_at
vip_users      -- user_id, vip_expires_at, is_active
payments       -- id, user_id, days, amount, status, donation_id, created_at
download_logs  -- user_id, downloaded_at
```

---

## 📄 License

Proyek ini untuk keperluan edukasi. Hormati hak cipta kreator konten dan syarat layanan platform.

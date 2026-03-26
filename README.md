# 🤖 Bot Downloader TikTok & Instagram

Bot Telegram untuk mengunduh konten **TikTok** dan **Instagram** lengkap dengan sistem **VIP subscription**, **VIP gratis harian**, pembayaran **QRIS otomatis via Saweria**, dan **AI Error Monitor berbasis Groq**.

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
| Tipe | Limit Download/Hari | Cara Dapat |
|------|---------------------|------------|
| Gratis | 10 | Default |
| VIP Gratis | 100 | Join channel sponsor (klaim ulang tiap hari) |
| VIP Berbayar | 100 | Bayar via QRIS |

**Paket VIP Berbayar:**
| Durasi | Harga |
|--------|-------|
| 3 Hari | Rp 1.000 |
| 7 Hari | Rp 50.000 |
| 15 Hari | Rp 10.000 |
| 30 Hari | Rp 15.000 |
| 60 Hari | Rp 20.000 |
| 90 Hari | Rp 25.000 |

### 🎁 VIP Gratis Harian (Anti-Join & Leave)
- User klik tombol **🎁 VIP Gratis** di menu utama
- Bot tampilkan daftar channel sponsor sebagai tombol klik langsung (3 per baris)
- Setelah join semua channel, user klik **Klaim VIP Gratis**
- Bot **cek ulang membership secara real-time** via Telegram API
- Jika lolos → VIP 1 hari aktif otomatis
- **Besok VIP habis** → user harus klaim lagi → bot cek lagi → dst.
- Jika user cabut dari channel → tidak bisa klaim ulang

### 💳 Pembayaran QRIS Otomatis (Saweria)
- Bot generate QR Code QRIS langsung di chat
- Support semua e-wallet & mobile banking (GoPay, OVO, Dana, BCA, BRI, dll.)
- Bot polling otomatis setiap **7 detik**, maksimal **15 menit**
- VIP **aktif sendiri** begitu pembayaran terdeteksi — tanpa perlu konfirmasi admin

### 🤖 AI Error Monitor (Groq)
Bot dilengkapi sistem monitoring error berbasis AI yang bekerja otomatis:

**Deteksi & Analisa:**
- Setiap error yang terjadi langsung dikirim ke Groq untuk dianalisa
- AI memberikan laporan terstruktur: tingkat keparahan, penyebab, saran solusi, dampak
- Laporan dikirim ke semua admin via Telegram secara real-time

**5-Tier Model Cascade** (otomatis fallback jika model sibuk/limit):
| Tier | Model | Kualitas | Limit/Hari |
|------|-------|----------|------------|
| 1 | llama-3.3-70b-versatile | 10/10 | 1.000 |
| 2 | moonshotai/kimi-k2-instruct | 9/10 | 1.000 |
| 3 | groq/compound | 8/10 | 250 |
| 4 | llama-4-scout-17b-16e | 7/10 | 1.000 |
| 5 | llama-3.1-8b-instant | 6/10 | 14.400 |

**Semi-Auto Fix dengan Approval Admin:**
- AI generate patch kode otomatis untuk memperbaiki error
- Admin menerima notifikasi dengan tombol:
  - ✅ **Terapkan Fix & Restart** — bot terapkan patch + buat backup + restart sendiri
  - ❌ **Abaikan** — abaikan patch
- Backup file `.bak` selalu dibuat sebelum patch diterapkan

**Rollback:**
- Setelah fix diterapkan, tombol **🔄 Rollback** tersedia
- Jika fix malah merusak bot, admin klik Rollback → file dikembalikan dari backup → restart
- Riwayat semua fix tersimpan di `rollback_store.json` — bisa rollback kapan saja
- Akses via Admin Panel → **🔄 Riwayat Rollback**

### 🔒 Keamanan & Stabilitas
- Wajib join channel sebelum bisa download (dapat dinonaktifkan)
- Sistem limit harian mencegah penyalahgunaan
- Retry otomatis saat terjadi network error (timeout) — tidak langsung crash
- Timeout koneksi ke Telegram API: 30 detik

---

## 🗂 Struktur Proyek

```
bot/
├── config.py          # Konfigurasi dari environment variables
├── constants.py       # Semua teks pesan & paket VIP
├── database.py        # SQLite: user, VIP, payment, download log
├── main.py            # Entry point, handler, menu sistem
├── ai_monitor.py      # Groq AI Monitor: analisa error, generate fix, rollback
├── payment/
│   └── saweria.py     # Saweria API: buat donasi, generate QR, cek status
└── downloaders/
    ├── tiktok.py      # Download TikTok via yt-dlp
    └── instagram.py   # Download Instagram via yt-dlp

pending_fixes.json     # Fix AI yang menunggu approval admin (auto-generated)
rollback_store.json    # Riwayat fix yang sudah diterapkan (auto-generated)
database.db            # SQLite database (auto-generated)
ecosystem.config.js    # Konfigurasi PM2
start.sh               # Script startup otomatis
```

---

## 🚀 Setup & Instalasi

### Prasyarat
- Python 3.11+
- Node.js + PM2 (untuk produksi)
- Akun [Saweria](https://saweria.co) (untuk pembayaran QRIS)
- Telegram Bot Token dari [@BotFather](https://t.me/BotFather)
- Groq API Key dari [console.groq.com](https://console.groq.com) *(opsional, untuk AI Monitor)*

### 1. Clone & Install

```bash
git clone https://github.com/tentangblockchain/Instagram.git
cd Instagram
pip install -r requirements.txt --break-system-packages
```

### 2. Konfigurasi Environment

Buat file `.env`:

```bash
cp .env.example .env
nano .env
```

Isi variabel berikut:

```env
# ── Wajib ────────────────────────────────────────────
BOT_TOKEN=token_dari_botfather
ADMIN_IDS=123456789,987654321

# ── Saweria (pembayaran QRIS) ────────────────────────
SAWERIA_USERNAME=username_saweria_kamu
SAWERIA_USER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# ── Channel Sponsor (VIP Gratis) ─────────────────────
# Pisahkan dengan koma, format @username
REQUIRED_CHANNEL=@channel1,@channel2,@channel3

# ── AI Error Monitor (Groq) ──────────────────────────
# Dapatkan gratis di console.groq.com
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# ── Opsional ──────────────────────────────────────────
FREE_DAILY_LIMIT=10
VIP_DAILY_LIMIT=100
DATABASE_PATH=database.db
```

> **Cara dapat `SAWERIA_USER_ID`:**
> Buka `saweria.co/usernamemu` → F12 → tab Network → cari request ke endpoint `snap` → salin nilai `user_id` (format UUID).

> **Cara dapat `GROQ_API_KEY`:**
> Buka [console.groq.com](https://console.groq.com) → Login → API Keys → Create API Key → Copy.

### 3. Jalankan Bot

#### Langsung (testing)
```bash
python3 -m bot.main
```

#### Via PM2 (produksi — recommended)

```bash
# Install PM2 jika belum ada
npm install -g pm2

# Start bot (otomatis cek .env, install deps, setup PM2)
bash start.sh
```

**Perintah PM2 sehari-hari:**
```bash
pm2 logs downloader-ig-vt       # Log live
pm2 status                      # Status bot
pm2 restart downloader-ig-vt    # Restart bot
pm2 stop downloader-ig-vt       # Stop bot
pm2 monit                       # Monitor real-time (CPU & RAM)
pm2 save                        # Simpan config (auto-start saat reboot)
pm2 startup                     # Generate perintah auto-start OS
```

---

## 📱 Cara Pakai (User)

### Download Konten
Cukup kirim link langsung ke chat bot:

```
https://vt.tiktok.com/ZSxxxx
https://www.instagram.com/p/xxxx/
```

### Menu Utama (`/start`)

```
🏠 Menu Utama
├── 💎 Upgrade VIP      → Pilih paket → Scan QR → VIP aktif otomatis
├── 👑 Status VIP       → Cek status & sisa download hari ini
├── 🎁 VIP Gratis       → Join channel sponsor → VIP 1 hari gratis
└── 📥 Cara Download    → Panduan singkat
```

Untuk admin, muncul tambahan:
```
└── 🔐 Admin Panel
    ├── 👥 List VIP           → Daftar semua VIP aktif
    ├── 📊 Statistik          → Statistik bot
    └── 🔄 Riwayat Rollback   → Kelola rollback fix AI
```

---

## ⌨️ Command

| Command | Deskripsi | Akses |
|---------|-----------|-------|
| `/start` | Buka menu utama | Semua user |
| `/help` | Panduan penggunaan | Semua user |
| `!delvip <user_id>` | Hapus VIP user tertentu | Admin only |

> Semua fitur lain tersedia melalui tombol menu — tidak perlu command tambahan.

---

## 🔄 Alur Pembayaran VIP

```
User klik "💎 Upgrade VIP"
    → Pilih paket (misal: 30 Hari - Rp 15.000)
        → Bot buat donasi di Saweria
            → Bot kirim QR Code QRIS ke chat
                → User scan & bayar (maks. 15 menit)
                    → Bot polling status setiap 7 detik
                        → Pembayaran terdeteksi
                            → VIP aktif otomatis ✅
```

## 🎁 Alur VIP Gratis Harian

```
User klik "🎁 VIP Gratis"
    → Bot cek status VIP saat ini
        → VIP masih aktif? → Tampil info expire
        → Belum aktif?
            → Tampil daftar channel sponsor (tombol 3/baris)
                → User join semua channel
                    → Klik "✅ Sudah Join — Klaim VIP Gratis!"
                        → Bot cek ulang membership real-time
                            → Belum join semua? → Tampil pesan gagal
                            → Sudah join semua? → VIP 1 hari aktif ✅
                                → Besok klaim lagi → bot cek lagi → dst.
```

## 🤖 Alur AI Error Monitor

```
Error terjadi di bot
    → Groq analisa (cascade 5 tier, mulai dari model terbaik)
        → AI generate laporan + patch kode
            → Admin terima notifikasi di Telegram
                ├── Klik "✅ Terapkan Fix & Restart"
                │       → Backup .bak dibuat otomatis
                │       → Patch diterapkan ke file
                │       → Bot restart sendiri
                │       → Tombol "🔄 Rollback" tersedia
                │           → Klik Rollback jika bot malah rusak
                │               → File dikembalikan dari backup
                │               → Bot restart ke kondisi sebelumnya ✅
                └── Klik "❌ Abaikan"
                        → Patch diabaikan, tidak ada perubahan
```

---

## 🛠 Dependencies Utama

| Package | Fungsi |
|---------|--------|
| `python-telegram-bot==21.5` | Framework bot Telegram (async) |
| `yt-dlp` | Download TikTok & Instagram |
| `httpx` | HTTP client async (Groq API & Saweria) |
| `qrcode` + `Pillow` | Generate gambar QR Code |
| `python-dotenv` | Baca file `.env` (override system env) |
| `APScheduler` | Cleanup VIP expired terjadwal |

> Saweria API menggunakan `curl` via subprocess untuk bypass Cloudflare TLS fingerprinting.

---

## 🗄 Database Schema

```sql
-- Tabel users: data user & status VIP
users (
    user_id        INTEGER PRIMARY KEY,
    username       TEXT,
    created_at     TIMESTAMP,
    is_vip         BOOLEAN,
    vip_expires_at TIMESTAMP
)

-- Tabel downloads: tracking limit harian
downloads (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER,
    download_date  DATE,
    created_at     TIMESTAMP
)

-- Tabel payments: riwayat transaksi Saweria
payments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER,
    days           INTEGER,
    amount         INTEGER,
    status         TEXT,       -- pending | approved | rejected | expired
    donation_id    TEXT,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
)
```

---

## 📄 Changelog

### 2026-03-26
- **AI Error Monitor (Groq)** — deteksi error real-time, analisa AI, notif ke admin
- **5-Tier Model Cascade** — fallback otomatis ke model lebih ringan jika limit
- **Semi-Auto Fix** — AI generate patch, admin approve, bot terapkan & restart sendiri
- **Rollback System** — backup otomatis sebelum patch, rollback 1 klik jika gagal
- **VIP Gratis Harian** — join channel sponsor → VIP 1 hari, klaim ulang tiap hari
- **Network Retry** — bot tidak crash saat timeout, retry otomatis hingga 60 detik
- **Migrasi Saweria** — ganti Trakteer ke Saweria QRIS, pembayaran fully automatic

---

## 📄 License

Proyek ini untuk keperluan edukasi. Hormati hak cipta kreator konten dan syarat layanan platform.

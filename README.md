# 🤖 Bot Downloader TikTok, Instagram & Facebook

Bot Telegram untuk mengunduh konten **TikTok**, **Instagram** & **Facebook Reels** lengkap dengan sistem **VIP subscription**, **VIP gratis harian**, pembayaran **QRIS otomatis via Saweria**, **multi-link batch 51** dan **AI Error Monitor berbasis Groq** — tanpa Docker, full Playwright + yt-dlp.

> **Update 2026-09-01:** Facebook Reels tanpa login (public), profile `?sk=reels_tab` scrape 10 reels via Playwright desktop, multi-link 1 pesan, Groq cascade fix, batch race-fix.

---

## ✨ Fitur Utama

### 📥 Download Konten

| Platform | Format | Keterangan |
|----------|--------|------------|
| **TikTok** | Video, Foto/Slideshow | Support link pendek `vt.tiktok.com`, `vm.tiktok.com`, `tiktok.com/@user/video/ID` — fallback `tikwm API` jika yt-dlp gagal |
| **Instagram** | Post, Reels, Carousel | Carousel dikirim satu per satu dengan nomor urut, fallback `fastdl.app` via Playwright jika restricted |
| **Facebook** | Reels, Video, `fb.watch` | **Tanpa login** untuk public: `facebook.com/reel/ID`, `fb.watch/ID`, `facebook.com/share/r/ID` — **Profile** `facebook.com/people/.../?sk=reels_tab` scrape 10 reels via Playwright desktop (tanpa Docker, pengganti FlareSolverr) + `yt-dlp` |

- **Multi-link 1 pesan:** kirim **51 link sekaligus** dalam 1 pesan (4019 chars < 4096 limit Telegram) — bot proses berurutan dengan progress `Processing 5/51...` & summary `Selesai! 51/51 Sukses`, anti-flood `asyncio.sleep(0.3)` antar link
- **Facebook:** `FACEBOOK_RE = https?://(?:www\.|m\.|mbasic\.)?(?:facebook\.com|fb\.com|fb\.watch)/\S+` — single reel public tanpa `FACEBOOK_COOKIES`, profile reels butuh cookies jika private/has_next_page
- Caption konten otomatis disertakan, file dikirim langsung ke chat

### 💎 Sistem VIP

| Tipe | Limit Download/Hari | Cara Dapat |
|------|---------------------|------------|
| Gratis | 10 | Default |
| VIP Gratis | 100 | Join channel sponsor (klaim ulang tiap hari) |
| VIP Berbayar | 100 | Bayar via QRIS |
| Admin | Unlimited | `ADMIN_IDS` |

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
- **`Conflict` & `NetworkError` (httpx.ReadError)** di-filter — tidak spam Groq (hanya log warning), karena polling Telegram kadang jitter di Replit

**6-Tier Model Cascade** (otomatis fallback jika model sibuk/limit) — **update 2026-08-26**:

| Tier | Model | RPD | TPM | Label |
|------|-------|-----|-----|-------|
| 1 | `groq/compound` | 250 | 70K | Good (9/10) |
| 2 | `groq/compound-mini` | 250 | 70K | Mini (8/10) |
| 3 | `openai/gpt-oss-120b` | 1K | 8K | GPT-OSS-120b (8/10) |
| 4 | `openai/gpt-oss-20b` | 1K | 8K | GPT-OSS-20b (7/10) |
| 5 | `qwen/qwen3.6-27b` | 1K | 8K | Qwen (6/10) |
| 6 | `allam-2-7b` | 7K | 6K | Allam (5/10) |

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
- Sistem limit harian mencegah penyalahgunaan (cek per-link di batch)
- Retry otomatis saat terjadi network error (timeout) — tidak langsung crash, exponential backoff 5s→60s
- Timeout koneksi ke Telegram API: 30 detik
- **Batch race-fix:** `proc_msg` tidak di-delete mid-batch (`batch=True`), progress aman, `Message to delete/edit not found` tidak lagi terjadi

---

## 🗂 Struktur Proyek

```
bot/
├── config.py          # Konfigurasi dari environment variables (FACEBOOK_COOKIES, INSTAGRAM_COOKIES)
├── constants.py       # Semua teks pesan & paket VIP
├── database.py        # SQLite: user, VIP, payment, download log
├── main.py            # Entry point, handler, menu sistem (multi-link findall, _send_facebook batch)
├── ai_monitor.py      # Groq AI Monitor: analisa error, generate fix, rollback (6 tiers 2026-08-26)
├── payment/
│   └── saweria.py     # Saweria API: buat donasi, generate QR, cek status
└── downloaders/
    ├── tiktok.py      # Download TikTok via yt-dlp + tikwm fallback
    ├── instagram.py   # Download Instagram via yt-dlp + fastdl.app Playwright
    ├── facebook.py    # Download Facebook via yt-dlp + Playwright www.facebook desktop (tanpa Docker)
    └── fastdl.py      # Fallback IG restricted via fastdl.app Playwright

pending_fixes.json     # Fix AI yang menunggu approval admin (auto-generated)
rollback_store.json    # Riwayat fix yang sudah diterapkan (auto-generated)
database.db            # SQLite database (auto-generated)
facebook_reels_yayu/   # Contoh hasil batch 10 reels Yayu iswahyuni (22M, public)
ecosystem.config.js    # Konfigurasi PM2
replit.nix             # Nix deps: python311, ffmpeg, playwright-driver, stdenv.cc.lib
start.sh               # Script startup otomatis
```

---

## 🚀 Setup & Instalasi

### Prasyarat

- Python 3.11+
- Node.js + PM2 (untuk produksi)
- `ffmpeg` (untuk merge video)
- Akun [Saweria](https://saweria.co) (untuk pembayaran QRIS)
- Telegram Bot Token dari [@BotFather](https://t.me/BotFather)
- Groq API Key dari [console.groq.com](https://console.groq.com) *(opsional, untuk AI Monitor)*
- **Playwright** (untuk Facebook profile & IG restricted) — tanpa Docker di Replit via `REPLIT_PLAYWRIGHT_CHROMIUM_EXECUTABLE`

### 1. Clone & Install

```bash
git clone https://github.com/tentangblockchain/Instagram.git
cd Instagram
pip install -r requirements.txt --break-system-packages
# Jika di Replit, replit.nix akan auto-install playwright-driver + ffmpeg
# Jika manual: playwright install chromium
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

# ── Cookies (opsional, untuk konten private) ─────────
# Instagram restricted: export via ekstensi Get cookies.txt LOCALLY
INSTAGRAM_COOKIES=instagram_cookies.txt
# Facebook profile reels_tab private/has_next_page >10: sama, login facebook.com -> export
FACEBOOK_COOKIES=facebook_cookies.txt

# ── Opsional ──────────────────────────────────────────
FREE_DAILY_LIMIT=10
VIP_DAILY_LIMIT=100
DATABASE_PATH=database.db
```

> **Cara dapat `SAWERIA_USER_ID`:** Buka `saweria.co/usernamemu` → F12 → tab Network → cari request ke endpoint `snap` → salin nilai `user_id` (format UUID).

> **Cara dapat `GROQ_API_KEY`:** Buka [console.groq.com](https://console.groq.com) → Login → API Keys → Create API Key → Copy.

> **Cara dapat `FACEBOOK_COOKIES`:** Admin Panel → `🍪 Set FB Cookies` → paste isi `cookies.txt` (Netscape) dari ekstensi Get cookies.txt setelah login facebook.com. Tanpa ini, profile `?sk=reels_tab` public tetap bisa 10 reels via `www.facebook` desktop (sudah verified tanpa login).

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

Cukup kirim link langsung ke chat bot — **bisa 51 link sekaligus dalam 1 pesan** (findall, batch):

```
https://vt.tiktok.com/ZSxxxx
https://www.instagram.com/p/xxxx/
https://www.facebook.com/reel/1034720669351172/
https://www.facebook.com/reel/1057930243820615/?s=fb_shorts_profile&stack_idx=0
https://www.facebook.com/people/Yayu-iswahyuni/61590328673759/?sk=reels_tab
```

Bot akan proses berurutan, kirim video satu per satu, update progress tiap 5 link: `Processing 5/51...` → summary `Selesai! 51/51 Sukses`.

*Contoh batch Facebook 10 reels Yayu iswahyuni (public, 22M total) sudah ada di `facebook_reels_yayu/`.*

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
    ├── 🍪 Set IG Cookies     → Set cookies Instagram restricted
    ├── 🍪 Set FB Cookies     → Set cookies Facebook profile reels
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
Error terjadi di bot (kecuali Conflict & NetworkError yang di-filter)
    → Groq analisa (cascade 6 tier, mulai dari model terbaik)
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

## 📥 Alur Facebook Reels (Tanpa Docker)

```
User kirim link Facebook
├── Jika single reel (facebook.com/reel/ID, fb.watch/ID, share/r/ID)
│   → yt-dlp download bestvideo+bestaudio → merge mp4 → kirim video
│
└── Jika profile reels_tab (facebook.com/.../?sk=reels_tab)
    → Playwright goto www.facebook.com (desktop UA, serviceWorkers:block)
    → window.scrollTo + mouse.wheel → extract href /reel/ → kumpulkan 10 reels
    → Jika has_next_page=true & ada FACEBOOK_COOKIES → inject cookies → fetch cursor next page via GraphQL (bisa 30+)
    → Tampilkan tombol 📥 Reels #1..10 (callback fbdl_0..9) atau dalam batch download reel pertama
```

---

## 🛠 Dependencies Utama

| Package | Fungsi |
|---------|--------|
| `python-telegram-bot==21.5` | Framework bot Telegram (async) |
| `yt-dlp==2026.3.3` | Download TikTok, Instagram & Facebook |
| `playwright==1.55.0` | Playwright untuk Facebook profile & IG fastdl (tanpa Docker) |
| `httpx==0.27.2` | HTTP client async (Groq API & Saweria) |
| `qrcode` + `Pillow` | Generate gambar QR Code |
| `python-dotenv` | Baca file `.env` (override system env) |
| `APScheduler` | Cleanup VIP expired terjadwal |
| `ffmpeg` | Merge video/audio |

> Saweria API menggunakan `curl` via subprocess untuk bypass Cloudflare TLS fingerprinting.
> Facebook profile tanpa login tetap bisa 10 reels via `www.facebook` desktop (verified 2026-08-31).

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

### 2026-09-01

- **Facebook Reels** — download single reel & profile `?sk=reels_tab` via Playwright www.facebook desktop + yt-dlp, tanpa Docker (pengganti FlareSolverr), tanpa login untuk public (10 reels verified)
- **Multi-link 51** — 1 pesan bisa 51 link (findall, mixed TikTok/IG/FB), progress tiap 5, anti-flood sleep 0.3s
- **Batch race-fix** — proc_msg tidak di-delete mid-batch (`batch=True`), `Message to delete/edit not found` teratasi
- **Groq 2026-08-26** — update 5→6 tiers: `groq/compound` 250, `groq/compound-mini` 250, `openai/gpt-oss-120b` 1K, `openai/gpt-oss-20b` 1K, `qwen/qwen3.6-27b` 1K, `allam-2-7b` 7K
- **Filter error spam** — `Conflict` & `NetworkError` (httpx.ReadError) tidak dikirim ke Groq
- **TikTok fallback** — yt-dlp fail `Unable to extract universal data` → fallback `tikwm API` sukses

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

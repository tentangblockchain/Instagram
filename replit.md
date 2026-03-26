# TikTok & Instagram Downloader Bot

## Overview
Telegram bot Python untuk download konten TikTok dan Instagram. Dilengkapi sistem VIP berbayar (QRIS Saweria), VIP gratis harian (channel sponsor), dan AI Error Monitor berbasis Groq dengan sistem rollback.

## Tech Stack
- **Language**: Python 3.11
- **Framework**: python-telegram-bot 21.5
- **Database**: SQLite (database.db)
- **Payment**: Saweria QRIS (auto-detect via polling)
- **AI Monitor**: Groq API (5-tier cascade model)
- **Key Libraries**:
  - yt-dlp — Media downloading
  - httpx — Async HTTP (Groq API + Saweria)
  - qrcode + Pillow — Generate QR image
  - python-dotenv 1.1.0 — Environment config (override=True)

## Project Structure
```
├── bot/
│   ├── __init__.py
│   ├── main.py             # Entry point & semua handler
│   ├── config.py           # Config loader dari env
│   ├── constants.py        # VIP packages & semua pesan
│   ├── database.py         # SQLite handler
│   ├── ai_monitor.py       # Groq AI Monitor + fix & rollback storage
│   ├── payment/
│   │   ├── __init__.py
│   │   └── saweria.py      # Saweria API (curl bypass Cloudflare)
│   └── downloaders/
│       ├── __init__.py
│       ├── tiktok.py
│       └── instagram.py
├── requirements.txt
├── ecosystem.config.js     # PM2 config
├── start.sh                # Script startup
├── pending_fixes.json      # AI fix pending approval (auto-generated)
├── rollback_store.json     # Riwayat fix yang diterapkan (auto-generated)
└── database.db             # Auto-created
```

## Environment Variables
| Variable | Wajib | Keterangan |
|---|---|---|
| `BOT_TOKEN` | ✅ | Token dari @BotFather |
| `ADMIN_IDS` | ✅ | User ID admin, pisah koma |
| `REQUIRED_CHANNEL` | ❌ | Channel sponsor VIP gratis, pisah koma |
| `SAWERIA_USERNAME` | ✅ | Username Saweria (tanpa @) |
| `SAWERIA_USER_ID` | ✅ | UUID Saweria (dari DevTools Network tab) |
| `GROQ_API_KEY` | ❌ | API key Groq untuk AI Monitor |
| `FREE_DAILY_LIMIT` | ❌ | Limit download user gratis (default: 10) |
| `VIP_DAILY_LIMIT` | ❌ | Limit download VIP (default: 100) |
| `DATABASE_PATH` | ❌ | Path file SQLite (default: database.db) |

## Key Features

### VIP Gratis Harian
- Tombol "🎁 VIP Gratis" di menu utama
- Bot cek membership channel sponsor real-time (Telegram API)
- Durasi 1 hari, harus klaim ulang setiap hari
- Otomatis gagal jika user sudah cabut dari channel

### AI Error Monitor (Groq)
- Error handler global via `app.add_error_handler()`
- 5-tier model cascade dengan daily usage tracking in-memory
- Generate patch kode + kirim ke admin dengan tombol approval
- Semi-auto fix: admin approve → bot terapkan + backup + restart (SIGTERM)
- Rollback: restore dari .bak + restart, riwayat di rollback_store.json

### Network Stability
- Timeout 30 detik untuk connect/read/write/pool
- Retry loop di entry point untuk NetworkError/TimedOut
- Exponential backoff: 5s → 10s → 20s → max 60s

## Admin Panel
- List VIP aktif
- Statistik bot
- Riwayat Rollback (fix AI yang bisa di-undo)
- `!delvip <user_id>` — hapus VIP via teks

## Recent Changes
- 2026-03-26: **Rollback System** — backup .bak otomatis, rollback 1 klik, riwayat rollback di admin panel
- 2026-03-26: **Semi-Auto Fix** — AI generate patch, admin approve, bot terapkan & restart
- 2026-03-26: **AI Error Monitor (Groq)** — 5-tier cascade, analisa real-time, notif ke admin
- 2026-03-26: **VIP Gratis Harian** — channel sponsor, tombol 3/baris, re-check membership
- 2026-03-26: **Network Retry** — tidak crash saat timeout, retry eksponensial
- 2026-03-26: **Migrasi Trakteer → Saweria** — QRIS fully automatic

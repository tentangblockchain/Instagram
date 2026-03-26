# TikTok & Instagram Downloader Bot

## Overview
Telegram bot Python untuk download konten TikTok dan Instagram. Dilengkapi sistem VIP berbasis pembayaran QRIS otomatis via Saweria.

## Tech Stack
- **Language**: Python 3.11
- **Framework**: python-telegram-bot 21.5
- **Database**: SQLite (database.db)
- **Payment**: Saweria QRIS (auto-detect via polling)
- **Key Libraries**:
  - yt-dlp 2026.3.3 — Media downloading
  - beautifulsoup4 4.12.3 — HTML parsing
  - qrcode + Pillow — Generate QR image
  - python-dotenv 1.1.0 — Environment config

## Project Structure
```
├── bot/
│   ├── __init__.py
│   ├── main.py             # Entry point & semua handler
│   ├── config.py           # Config loader dari env
│   ├── constants.py        # VIP packages & semua pesan
│   ├── database.py         # SQLite handler
│   ├── payment/
│   │   ├── __init__.py
│   │   └── saweria.py      # Saweria API (curl bypass Cloudflare)
│   └── downloaders/
│       ├── __init__.py
│       ├── tiktok.py
│       └── instagram.py
├── requirements.txt
└── database.db             # Auto-created
```

## Environment Variables
| Variable | Wajib | Keterangan |
|---|---|---|
| `BOT_TOKEN` | ✅ | Token dari @BotFather |
| `ADMIN_IDS` | ✅ | User ID admin, pisah koma |
| `REQUIRED_CHANNEL` | ❌ | Channel wajib join sebelum download |
| `SAWERIA_USERNAME` | ✅ | Username Saweria (tanpa @) |
| `SAWERIA_USER_ID` | ✅ | UUID Saweria (dari DevTools Network tab) |
| `FREE_DAILY_LIMIT` | ❌ | Limit download user gratis (default: 10) |
| `VIP_DAILY_LIMIT` | ❌ | Limit download VIP (default: 100) |
| `DATABASE_PATH` | ❌ | Path file SQLite (default: database.db) |

## Alur Pembayaran VIP (Fully Automatic)
1. User ketik `/vip` → pilih paket
2. Bot hit Saweria API → buat transaksi QRIS
3. Bot generate QR image → kirim ke user
4. Bot polling status tiap **7 detik** (max **15 menit**)
5. Setelah bayar → VIP **otomatis aktif** tanpa perlu admin approve

## User Commands
- `/start` — Mulai bot
- `/vip` — Lihat paket & bayar VIP
- `/status` — Cek status VIP
- `/help` — Bantuan

## Admin Commands (kirim sebagai pesan biasa)
- `!listvip` — Daftar semua VIP aktif
- `!delvip <user_id>` — Hapus VIP user
- `!stats` — Statistik bot

## VIP Packages
| Durasi | Harga |
|---|---|
| 3 hari | Rp 5.000 |
| 7 hari | Rp 10.000 |
| 15 hari | Rp 20.000 |
| 30 hari | Rp 35.000 |
| 60 hari | Rp 60.000 |
| 90 hari | Rp 80.000 |

## Database Schema
- **users** — Registrasi user & status VIP
- **downloads** — Tracking download harian
- **payments** — Rekaman transaksi Saweria

## Saweria API Notes
- Menggunakan `curl` via subprocess untuk bypass Cloudflare TLS fingerprinting
- Endpoint calculate: `POST /donations/{username}/calculate_pg_amount`
- Endpoint create: `POST /donations/snap/{user_id}`
- Endpoint status: `GET /donations/qris/snap/{donation_id}`
- QR valid selama **15 menit** sesuai batas Saweria

## Workflow
- Command: `python -m bot.main`
- Output: console

## Recent Changes
- 2026-03-26: **Fitur VIP Gratis 1 Hari (Anti-Join & Leave)**
  - Tambah tombol "🎁 VIP Gratis" di menu utama
  - Flow: klik → tampil daftar channel sponsor → join semua → klaim → VIP 1 hari aktif
  - Setiap klaim bot re-check membership secara real-time via Telegram API
  - Jika user cabut dari channel, tidak bisa klaim ulang keesokan harinya
  - User dengan VIP aktif (paid maupun free) tidak bisa klaim dobel
  - Channel `@username` otomatis jadi tombol link langsung ke channel

- 2026-03-26: **Migrasi Trakteer → Saweria + Full Refactor**
  - Ganti payment gateway dari Trakteer ke Saweria QRIS
  - Pembayaran kini fully automatic (tidak perlu admin approve)
  - Bot generate QR image dan polling status otomatis
  - Full refactor kode: bersih, modular, async proper
  - DB migration: kolom `trakteer_id` → `donation_id`
  - Hapus command `!cek`, `!pend` (tidak diperlukan lagi)
  - Tambah `!stats` untuk statistik bot
  - Tambah package `qrcode + Pillow` untuk generate QR image

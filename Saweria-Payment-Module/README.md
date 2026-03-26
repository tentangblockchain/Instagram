# 🤖 Saweria Telegram Bot

> Bot Telegram untuk donasi QRIS via Saweria — Node.js + Telegraf v4  
> Dilengkapi Cloudflare bypass, logger WIB, rate limiter, notifikasi admin, dan health monitor.

---

## 📋 Daftar Isi

1. [Fitur](#1-fitur)
2. [Cara Kerja Sistem](#2-cara-kerja-sistem)
3. [Instalasi & Setup](#3-instalasi--setup)
4. [Konfigurasi Environment Variables](#4-konfigurasi-environment-variables)
5. [Cara Dapat Saweria User ID](#5-cara-dapat-saweria-user-id)
6. [Saweria API — Referensi Lengkap](#6-saweria-api--referensi-lengkap)
7. [Cloudflare Bypass — Kenapa Pakai curl](#7-cloudflare-bypass--kenapa-pakai-curl)
8. [Polling Status Pembayaran](#8-polling-status-pembayaran)
9. [Fitur Admin](#9-fitur-admin)
10. [Error Handling](#10-error-handling)
11. [Checklist Deploy](#11-checklist-deploy)
12. [Dependencies](#12-dependencies)

---

## 1. Fitur

| Fitur | Keterangan |
|-------|-----------|
| 💳 **Donasi QRIS** | Generate QR Saweria langsung di Telegram |
| 🛡️ **Cloudflare Bypass** | Pakai system `curl` + browser headers — lolos TLS fingerprinting |
| ⏱️ **Logger WIB** | Semua log dengan timestamp Asia/Jakarta |
| 🚦 **Rate Limiter** | Max 15 pesan/menit per user, sliding window |
| 🎯 **Error Pintar** | Pesan error diterjemahkan jadi bahasa ramah user |
| 🔔 **Notifikasi Admin** | Alert donasi masuk & error ke admin via Telegram |
| 🏥 **Health Monitor** | Command `/health` untuk cek status bot secara real-time |
| 🔁 **Auto Retry** | Exponential backoff 3x (2s → 4s → 8s) untuk semua API call |
| 🔒 **Safety Net** | Fallback reply baru jika edit pesan gagal |
| 🔍 **Cek Status Manual** | User bisa cek status transaksi dengan ID donasi |

---

## 2. Cara Kerja Sistem

```
User Telegram
    │
    ▼
Bot Telegram (Telegraf)
    │
    ├─► [1] POST /donations/{username}/calculate_pg_amount  → Hitung biaya PG
    │
    ├─► [2] POST /donations/snap/{user_id}                  → Buat transaksi, dapat QR string
    │
    ├─► Generate QR image dari qr_string
    │
    ├─► Kirim QR image ke user via Telegram
    │
    └─► Loop polling status tiap 7 detik (max 15 menit)
            │
            ├─ "PENDING"              → lanjut tunggu, update countdown tiap menit
            ├─ "SUCCESS/SETTLEMENT"   → notif sukses ✅ + alert admin
            ├─ "CAPTURE"              → notif sukses ✅ (kartu kredit Midtrans)
            ├─ "FAILED/DENY"          → notif gagal ❌
            └─ timeout 15 menit       → notif expired ⏰
```

> **Catatan:** Step `check-eligible` dihapus — tidak diperlukan dan memperlambat proses.

---

## 3. Instalasi & Setup

```bash
# 1. Clone / download project
git clone <repo>
cd saweria-telegram-bot

# 2. Install dependencies
npm install

# 3. Buat file .env
cp .env.example .env
# Edit .env sesuai konfigurasi kamu

# 4. Jalankan bot
npm start

# Development (auto-restart)
npm run dev
```

---

## 4. Konfigurasi Environment Variables

Buat file `.env` di root project:

```env
# === WAJIB ===
BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNoo

# === SAWERIA ===
# Username Saweria kamu (tanpa @)
SAWERIA_USERNAME=username_kamu

# User ID Saweria (UUID — lihat cara dapat di bagian 5)
SAWERIA_USER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# === OPSIONAL ===
# Chat ID Telegram kamu untuk notifikasi donasi masuk & command /health
# Cara dapat: kirim pesan ke @userinfobot
ADMIN_CHAT_ID=123456789

# Set true untuk enable debug logs (lebih verbose)
DEBUG=false
```

| Variable | Wajib | Default | Keterangan |
|----------|-------|---------|-----------|
| `BOT_TOKEN` | ✅ | — | Token dari @BotFather |
| `SAWERIA_USERNAME` | ❌ | `zahwafe` | Username Saweria tanpa @ |
| `SAWERIA_USER_ID` | ❌ | bawaan | UUID pemilik akun Saweria |
| `ADMIN_CHAT_ID` | ❌ | — | Chat ID untuk notifikasi & `/health` |
| `DEBUG` | ❌ | `false` | Enable debug logging |

> ⚠️ Bot akan **exit otomatis** dengan pesan jelas jika `BOT_TOKEN` tidak diset atau tidak valid.

---

## 5. Cara Dapat Saweria User ID

User ID Saweria adalah UUID panjang, **berbeda** dari username.

**Cara 1 — DevTools (paling mudah):**
1. Buka `https://saweria.co/username_kamu` di Chrome
2. Tekan `F12` → tab **Network**
3. Refresh halaman, filter dengan kata `snap`
4. Klik request ke `backend.saweria.co` → lihat URL-nya
5. Path: `/donations/snap/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` → UUID itu **User ID** kamu

**Cara 2 — Dari response API:**
Field `user_id` di response endpoint buat transaksi berisi User ID pemilik akun.

---

## 6. Saweria API — Referensi Lengkap

### Base URL
```
https://backend.saweria.co
```

### Header Wajib (semua request)
Bot menggunakan `curl` dengan header browser lengkap untuk bypass Cloudflare. Lihat bagian [7](#7-cloudflare-bypass--kenapa-pakai-curl) untuk penjelasan detail.

---

### Endpoint 1 — Hitung Biaya Payment Gateway

```
POST /donations/{SAWERIA_USERNAME}/calculate_pg_amount
```

**Request Body:**
```json
{
  "agree": true,
  "notUnderage": true,
  "message": "Pesan donasi",
  "amount": 35000,
  "payment_type": "qris",
  "vote": "",
  "currency": "IDR",
  "customer_info": {
    "first_name": "Nama User",
    "email": "email@user.com",
    "phone": ""
  }
}
```

**Response:**
```json
{
  "data": {
    "amount_to_pay": 35248,
    "pg_fee": 248,
    "platform_fee": 0
  }
}
```

| Field | Keterangan |
|-------|-----------|
| `amount_to_pay` | Total yang dibayar user (sudah termasuk biaya PG) |
| `pg_fee` | Biaya payment gateway |
| `platform_fee` | Biaya platform (biasanya 0 untuk QRIS) |

---

### Endpoint 2 — Buat Transaksi & Dapat QR String

```
POST /donations/snap/{SAWERIA_USER_ID}
```

> ⚠️ Path ini pakai **User ID (UUID)**, **bukan username**.

**Request Body:**
```json
{
  "agree": true,
  "notUnderage": true,
  "message": "Pesan donasi",
  "amount": 35000,
  "payment_type": "qris",
  "vote": "",
  "currency": "IDR",
  "customer_info": {
    "first_name": "Nama User",
    "email": "email@user.com",
    "phone": ""
  }
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": "08e1e8c5-7c85-445d-9b7b-085241d8b27c",
    "amount": 35248,
    "amount_raw": 35248,
    "created_at": "Wed, 11 Mar 2026 21:32:18 GMT",
    "currency": "IDR",
    "donator": {
      "email": "email@user.com",
      "first_name": "Nama User",
      "phone": null
    },
    "message": "Pesan donasi",
    "payment_type": "qris",
    "qr_string": "00020101021226650013CO.XENDIT.WWW...",
    "status": "PENDING",
    "type": "donation",
    "user_id": "d8e876df-405c-4e08-9708-9808b9037ea5"
  }
}
```

| Field | Keterangan |
|-------|-----------|
| `id` | ID unik transaksi — simpan untuk polling status |
| `qr_string` | String QRIS standar — convert ke gambar QR |
| `status` | Status awal selalu `"PENDING"` |

---

### Endpoint 3 — Cek Status Transaksi

```
GET https://backend.saweria.co/donations/qris/snap/{DONATION_ID}
```

**Response:**
```json
{
  "data": {
    "id": "b4810786-98f8-4e3c-af92-3938db364063",
    "amount_raw": 1008,
    "created_at": "Sat, 14 Mar 2026 19:07:18 GMT",
    "qr_string": "...",
    "transaction_status": "Pending",
    "username": "sillviaroyshita"
  }
}
```

> ✅ Tidak perlu BUILD_ID — langsung ke backend, stabil meski Saweria deploy update.

### Semua Nilai Status yang Mungkin

| Status | Arti | Aksi Bot |
|--------|------|----------|
| `Pending` | Menunggu pembayaran | Lanjut polling |
| `Success` | Berhasil ✅ | Notif sukses |
| `Settlement` | Berhasil (settled) ✅ | Notif sukses |
| `Paid` | Berhasil dibayar ✅ | Notif sukses |
| `Capture` | Kartu kredit di-capture ✅ | Notif sukses |
| `Failed` | Gagal ❌ | Notif gagal |
| `Expired` | QR kedaluwarsa ⏰ | Notif expired |
| `Cancel` | Dibatalkan | Notif batal |
| `Deny` | Ditolak bank | Notif gagal |
| `Failure` | Kegagalan sistem | Notif gagal |

> ⚠️ Status bisa huruf besar, kecil, atau campur. Bot selalu normalize dengan `.toUpperCase()`.

---

## 7. Cloudflare Bypass — Kenapa Pakai curl

Saweria menggunakan Cloudflare Bot Management yang memblokir request dari server cloud (Replit, AWS, GCP) karena **TLS fingerprinting**.

| Aspek | Node.js / axios | System curl |
|-------|----------------|-------------|
| TLS fingerprint (JA3/JA4) | Dikenal Cloudflare sebagai bot | Berbeda dari Node.js |
| Browser headers | Tidak ada by default | Bisa ditambahkan lengkap |
| Hasil | ❌ HTTP 403 — diblokir | ✅ Lolos |

Bot menggunakan `child_process.execFile('curl', ...)` dengan 14 browser headers:

```
sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform
Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site
Accept-Language: id-ID,id;q=0.9,...
User-Agent: Chrome/145 Windows
Accept-Encoding: gzip, deflate, br, zstd
Priority: u=1, i
DNT: 1
Origin: https://saweria.co
Referer: https://saweria.co/
```

> 💡 Teknik ini dipelajari dari analisis proyek lain yang berhasil mengakses API Saweria dari server.

---

## 8. Polling Status Pembayaran

### Konfigurasi

```javascript
CHECK_INTERVAL_MS = 7000   // Cek tiap 7 detik
MAX_WAIT_MINUTES  = 15     // Maksimal tunggu 15 menit
```

> ⚠️ Jangan polling lebih cepat dari 5 detik — berisiko kena rate limit Saweria.

### Mekanisme

- Menggunakan `Date.now()` untuk hitung sisa waktu — akurat meski ada async delay
- Update countdown message ke user tiap 1 menit (bukan tiap 7 detik) untuk hemat Telegram API call
- Interval dibersihkan otomatis saat success/failed/expired/cancel
- Semua interval dibersihkan saat bot menerima SIGINT/SIGTERM (graceful shutdown)

---

## 9. Fitur Admin

Set `ADMIN_CHAT_ID` di `.env` untuk mengaktifkan fitur admin.

### Notifikasi Otomatis

Bot mengirim pesan ke admin untuk:

**✅ Donasi berhasil:**
```
💳 DONASI MASUK

👤 Dari: Budi
💰 Jumlah: Rp35.248
🆔 Ref: 08e1e8c5-...
```

**🚨 Error saat proses donasi:**
```
🚨 ERROR DONASI

👤 User: Budi (123456789)
💰 Nominal: Rp35.000
❌ Error: Non-JSON response dari Saweria
```

### Command `/health`

Kirim `/health` ke bot (hanya bisa jika `ADMIN_CHAT_ID` = Chat ID kamu):

```
🏥 System Health

✅ Status: RUNNING
⏱ Uptime: 5h 23m 14s

💾 Memory:
   • Heap Used: 45.2 MB
   • Heap Total: 128.0 MB
   • RSS: 62.1 MB

📊 Polling Aktif: 2 transaksi
👥 Users Proses: 1
```

---

## 10. Error Handling

### Error Otomatis per Kategori

| Kategori | Trigger | Pesan ke User |
|----------|---------|--------------|
| `TIMEOUT` | `ETIMEDOUT`, `timeout` | ⏳ Koneksi lambat. Silakan coba lagi. |
| `RATE_LIMIT` | `429`, `rate limit` | ⏳ Terlalu banyak permintaan. Tunggu sebentar. |
| `NETWORK` | `ECONNRESET`, `network` | 🌐 Masalah koneksi. Silakan coba lagi. |
| `NOT_FOUND` | `404`, `not found` | 🔍 Data tidak ditemukan. |
| `PERMISSION` | `403`, `forbidden` | 🚫 Akses ditolak oleh server. |
| `VALIDATION` | `non-json`, `invalid` | 📝 Respons tidak valid dari Saweria. |
| `UNKNOWN` | Lainnya | ❌ Terjadi kesalahan. Silakan coba lagi. |

### Error Umum & Solusi

| Error | Penyebab | Solusi |
|-------|----------|--------|
| `403` dari Saweria API | Cloudflare blokir IP server | Sudah teratasi dengan curl bypass |
| `404` di endpoint status | ID transaksi tidak ditemukan | Pastikan ID donasi benar |
| `Non-JSON response` | Cloudflare challenge page | Curl headers perlu diupdate |
| `ETIMEDOUT` ke Telegram | ISP blokir akses Telegram | Jalankan dari VPS Indonesia atau lokal |
| `BOT_TOKEN tidak valid` | Token salah / belum diset | Set `BOT_TOKEN` di `.env` atau secrets |

---

## 11. Checklist Deploy

### Setup Awal
- [ ] File `.env` sudah dibuat dan diisi
- [ ] `BOT_TOKEN` valid — test: `https://api.telegram.org/bot{TOKEN}/getMe`
- [ ] `SAWERIA_USERNAME` benar (tanpa @)
- [ ] `SAWERIA_USER_ID` benar (format UUID)
- [ ] `npm install` sudah dijalankan

### Opsional tapi Direkomendasikan
- [ ] `ADMIN_CHAT_ID` diset untuk notifikasi donasi real-time
- [ ] Test `/health` command dari akun admin

### Testing Fungsionalitas
- [ ] `/start` → menu utama muncul
- [ ] Pilih nominal → form nama/email/pesan berjalan
- [ ] QR muncul setelah submit
- [ ] Tombol Batalkan berfungsi
- [ ] Nominal custom (bukan preset) berfungsi
- [ ] Cek Status manual dengan ID transaksi
- [ ] Polling update countdown tiap menit
- [ ] Test donasi sungguhan / tunggu expired 15 menit

### Keamanan
- [ ] File `.env` ada di `.gitignore`
- [ ] `BOT_TOKEN` tidak hardcode di kode
- [ ] `SAWERIA_USER_ID` tidak hardcode di kode

---

## 12. Dependencies

```json
{
  "dependencies": {
    "telegraf": "^4.16.3",
    "qrcode": "^1.5.3",
    "dotenv": "^17.3.1"
  },
  "devDependencies": {
    "nodemon": "^3.1.4"
  }
}
```

> **Tidak ada axios** — request HTTP ke Saweria menggunakan system `curl` via `child_process.execFile`.

Install:
```bash
npm install
```

---

## 📝 Catatan Penting

- **Bot harus dijalankan dari IP non-data center** (lokal / VPS Indonesia) agar bisa akses Saweria. Meskipun curl sudah bypass Cloudflare, IP Replit secara keseluruhan mungkin masih diblokir di level IP reputation.
- **QR code valid 15 menit** — sesuai batas waktu Saweria untuk transaksi QRIS.
- **Satu user, satu transaksi** — rate limiter dan `processingUsers` mencegah user spam transaksi bersamaan.
- **Endpoint status stabil** — pakai `GET /donations/qris/snap/{id}` langsung ke backend, tidak bergantung Next.js BUILD_ID yang bisa expired.

---

*Dibuat dengan Node.js + Telegraf v4 + Saweria API*

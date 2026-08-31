# CHANGELOG FIXES — downloader-ig-vt

## IG-001: Fix register_user() INSERT OR REPLACE berbahaya
- **Tanggal:** 2026-05-25
- **File:** `/root/telegram/Instagram/bot/database.py` baris 72-80
- **Masalah:** `INSERT OR REPLACE` = DELETE + INSERT di SQLite. Setiap user `/start` ulang bisa hilangkan data `is_vip` dan `vip_expires_at` yang sudah ada.
- **Fix:** Ganti dengan `INSERT ... ON CONFLICT(user_id) DO UPDATE SET username = excluded.username`. Data VIP, created_at, dan kolom lain tetap aman.
- **Verifikasi:** `python3 -m py_compile` clean.

## IG-002: Suppress httpx INFO logging dari stderr
- **Tanggal:** 2026-05-25
- **File:** `/root/telegram/Instagram/bot/main.py` baris 33-34
- **Masalah:** Setiap HTTP request polling Telegram (tiap ~10 detik) tercatat sebagai `[INFO] httpx: HTTP Request: POST .../getUpdates` di error log. File log error penuh noise, sulit identifikasi error sesungguhnya.
- **Fix:** Tambah `logging.getLogger("httpx").setLevel(logging.WARNING)` dan `logging.getLogger("httpcore").setLevel(logging.WARNING)` setelah basicConfig.
- **Verifikasi:** `python3 -m py_compile` clean, log setelah restart bersih dari httpx INFO.

## IG-003: Bersihkan log arsip & optimasi logrotate
- **Tanggal:** 2026-05-25
- **File:** `/root/telegram/Instagram/logs/` + PM2 logrotate config
- **Masalah:** 37 file log arsip (>7 hari) menghabiskan 55 MB dari total 73 MB (75%). PM2 logrotate retain 30 file (terlalu banyak).
- **Fix:** Hapus log arsip >7 hari (55 MB → 0). Ubah PM2 logrotate retain dari 30 → 7, max_size dari 10M → 5M.
- **Verifikasi:** Log folder: 72 MB → 18 MB. PM2 logrotate updated.

## IG-004: Tambahkan periodic cleanup temp files
- **Tanggal:** 2026-05-25
- **File:** `/root/telegram/Instagram/bot/main.py` (method baru + job queue)
- **Masalah:** `TikTokDownloader.cleanup_downloads()` ada tapi tidak pernah dipanggil. File temp di `/tmp/jawanese_bot_*/` dan `/tmp/qr_*.png` bisa menumpuk.
- **Fix:** Tambah method `_job_cleanup_temp_files()` yang bersihkan file >1 jam. Ditambahkan ke job queue (interval 3600 detik, bersamaan dengan cleanup VIP).
- **Verifikasi:** `python3 -m py_compile` clean, PM2 log: `Added job "_job_cleanup_temp_files"`.

## IG-005: Bersihkan .env — hapus config Trakteer
- **Tanggal:** 2026-05-25
- **File:** `/root/telegram/Instagram/.env`
- **Masalah:** `TRAKTEER_API_KEY` dan `TRAKTEER_USERNAME` masih ada di .env padahal sudah migrasi ke Saweria. Tidak dipakai di kode manapun (hanya di database.py migration rename column).
- **Fix:** Hapus kedua baris TRAKTEER_* dari .env.
- **Verifikasi:** Bot restart normal, tidak ada error config.

## IG-006: Fix logging — semua INFO salah masuk ke stderr/error log
- **Tanggal:** 2026-05-28
- **File:** `/root/telegram/Instagram/bot/main.py` baris 27-38
- **Masalah:** `logging.StreamHandler()` default ke stderr. Semua log (INFO, WARNING, ERROR) masuk ke `bot-error-*.log`. `bot-out-*.log` selalu kosong (0 bytes). Sulit monitor aktivitas bot.
- **Fix:** Pisahkan handler: INFO/DEBUG → stdout (`bot-out`), WARNING/ERROR → stderr (`bot-error`). Pakai custom `_InfoFilter` class.
- **Verifikasi:** Bot restart, INFO log muncul di `bot-out-39.log` (type: "out").

## IG-007: Fix TikTok short URL gagal download — operator precedence bug
- **Tanggal:** 2026-05-28
- **File:** `/root/telegram/Instagram/bot/downloaders/tiktok.py` baris 235
- **Masalah:** `if 'notfound' in ... or resolved_url == url and (...)` — operator precedence salah. `and` lebih kuat dari `or`, sehingga kondisi `resolved_url == url` (yang terjadi saat resolve gagal) langsung trigger fail tanpa coba yt-dlp. yt-dlp bisa handle short URL langsung.
- **Fix:** Hapus kondisi `resolved_url == url`. Hanya fail jika URL resolve ke halaman `notfound`. Biarkan yt-dlp coba download langsung jika resolve gagal.
- **Verifikasi:** `python3 -m py_compile` clean, bot restart normal.

## IG-008: Fix Instagram carousel hitungan download salah
- **Tanggal:** 2026-05-28
- **File:** `/root/telegram/Instagram/bot/main.py` baris 287→293
- **Masalah:** `self.db.record_download(user_id)` di dalam loop per media. Carousel 10 foto = 10 download count, padahal seharusnya 1 request = 1 download.
- **Fix:** Pindah `record_download()` ke luar loop, sebelum iterasi media. Sekarang 1 carousel = 1 download count.
- **Verifikasi:** `python3 -m py_compile` clean, bot restart normal.

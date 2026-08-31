# FIX HISTORY — Audit Log

## BOT-001: Guard clause di handle_text — AttributeError: 'NoneType'
- **Tanggal:** 2026-08-26
- **File:** `bot/main.py` baris 211-212
- **Severity:** High
- **Status:** DEFENSIVE FIX — root cause tidak terverifikasi karena log sudah ke-rotate (log tertua tersisa 25 Juli, fix dibuat 14 Juli). Skenario paling mungkin: channel_post lolos filter, update.message = None.
- **Masalah:** `update.message.text.strip()` crash dengan `AttributeError: 'NoneType' object has no attribute 'text'` ketika `update.message` bernilai `None`. Error di-generate oleh Groq AI Monitor dan tersimpan di `pending_fixes.json`, tapi traceback asli sudah hilang dari log (di-rotate oleh pm2-logrotate).
- **Root cause (kemungkinan):** `app.run_polling(allowed_updates=Update.ALL_TYPES)` menerima channel post. `MessageHandler(filters.TEXT)` bisa menangkap channel post lewat `update.effective_message`, tapi `update.message` tetap `None` → crash.
- **Fix:** Guard clause: `if not update.message or not update.message.text: return` di awal `handle_text`.
- **Efek samping:** Update yang tidak valid di-skip secara diam-diam. Logging untuk skip case belum ditambahkan (lihat BOT-004).
- **Verifikasi:** `python -m py_compile` clean, ruff 33 error pre-existing (tidak ada baru).

## BOT-002: Guard clause di _handle_admin_state — defense in depth
- **Tanggal:** 2026-08-26
- **File:** `bot/main.py` baris 608-614
- **Severity:** Low (defense in depth — sudah terlindungi BOT-001)
- **Root cause:** Identik BOT-001. `text = update.message.text.strip()` crash jika `update.message` None. Saat ini hanya dipanggil dari `handle_text` yang sudah di-guard, jadi crash hanya mungkin jika ada code path baru di masa depan.
- **Fix:** Guard clause: `if not update.message or not update.message.text: return False` di awal `_handle_admin_state`.
- **Verifikasi:** `python -m py_compile` clean.

## BOT-003: Guard clause di _handle_url — defense in depth
- **Tanggal:** 2026-08-26
- **File:** `bot/main.py` baris 225-226
- **Severity:** Low (defense in depth — sudah terlindungi BOT-001)
- **Root cause:** Identik BOT-001. `text = update.message.text` crash jika `update.message` None.
- **Fix:** Guard clause: `if not update.message or not update.message.text: return` di awal `_handle_url`.
- **Verifikasi:** `python -m py_compile` clean.

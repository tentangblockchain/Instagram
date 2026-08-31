# Audit Workflow

## Alur Kerja (per issue)

1. **PROPOSE** — Sebelum fix apapun, tulis proposal yang berisi:
   - Root cause (kenapa bug terjadi, sertakan baris kode sebagai bukti)
   - Severity (lihat tabel di bawah)
   - Rencana perubahan (file apa aja yang kesentuh, logic apa yang berubah)
   - Efek samping potensial
   - **Tunggu approval sebelum lanjut ke langkah berikutnya.**

2. **EXECUTE** — Implement HANYA sesuai proposal yang disetujui.
   - Jangan sekalian benerin hal lain di luar scope. Kalau nemu issue lain saat implementasi, laporkan dulu sebagai temuan baru — jangan langsung fix.

3. **VERIFY** — Jalankan sebelum minta user tes:
   - `python -m py_compile <file>.py` (wajib, cek syntax)
   - `mypy <file>.py` (kalau file punya type hints)
   - Tidak ada pytest suite saat ini — verifikasi manual/logic review jadi andalan utama, jelaskan skenario yang sudah dicek.

4. **USER TEST** — Tunggu user tes manual di server/Replit. **Jangan commit atau push sebelum ada konfirmasi eksplisit dari user.**
   - Catatan penting: kode yang diedit dan kode yang ditest user adalah SAMA PERSIS (server yang sama). Kalau bug "masih muncul" setelah fix, kemungkinan paling masuk akal adalah bot belum di-restart — BUKAN kode berbeda. Wajib trace ulang dulu sebelum menyimpulkan fix gagal.

5. **COMMIT & LOG** — Setelah dikonfirmasi OK:
   - Commit + push
   - Update `docs/audit/fix-history.md` dengan: Issue ID, severity, root cause, fix yang diterapkan, tanggal

## Issue ID Format

`{KOMPONEN}-{NOMOR}`, contoh: `BOT-001`, `MON-001` (GroqMonitor), `DB-001`

## Severity Levels

| Level | Kriteria |
|---|---|
| Critical | Bot crash / data hilang / kredensial bocor |
| High | Logic mismatch vs behavior yang diharapkan / data integrity |
| Medium | Edge case jarang terjadi / race condition kecil |
| Low | Dead code / naming / komentar |

## Dokumentasi

- Semua temuan dan fix dicatat di `docs/audit/fix-history.md` — tidak ada file bug.md terpisah.
- Kalau ada perubahan arsitektur, env var baru, atau behavior baru, update juga README.md / dokumentasi relevan lainnya.

## Scope

- Cakupan audit: `bot/` (semua module), root-level scripts, dependency di `requirements.txt`.

## Catatan Environment

- Dependency manager: pip biasa (`requirements.txt`)
- Type hints: sebagian dipakai (contoh: `self.monitor: GroqMonitor | None = None`) — mypy bisa dijalankan tapi belum full-coverage
- Tidak ada pytest — jangan asumsikan ada test suite, jangan coba jalankan `pytest` sampai ada konfirmasi ditambahkan

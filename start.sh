#!/bin/bash
# ================================================
# Script startup Bot Telegram via PM2
# Jalankan: bash start.sh
# ================================================

set -e

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BOT_DIR"

echo "📁 Working directory: $BOT_DIR"

# ── Cek .env ────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "❌ File .env tidak ditemukan!"
  echo "   Jalankan: cp .env.example .env"
  echo "   Lalu isi BOT_TOKEN, ADMIN_IDS, SAWERIA_USERNAME, SAWERIA_USER_ID"
  exit 1
fi

if grep -q "your_telegram_bot_token_here" .env; then
  echo "❌ .env belum dikonfigurasi! Isi BOT_TOKEN terlebih dahulu."
  exit 1
fi

echo "✅ File .env ditemukan"

# ── Cek Python ──────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "❌ python3 tidak ditemukan. Install Python 3.11+ terlebih dahulu."
  exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYTHON_VER ditemukan"

# ── Cek dependencies ────────────────────────────
echo "📦 Mengecek dependencies..."
if ! python3 -c "import telegram" &>/dev/null; then
  echo "📦 Install dependencies..."
  pip install -r requirements.txt --break-system-packages
else
  echo "✅ Dependencies sudah terpasang"
fi

# ── Cek PM2 ─────────────────────────────────────
if ! command -v pm2 &>/dev/null; then
  echo "❌ PM2 tidak ditemukan. Install dengan:"
  echo "   npm install -g pm2"
  exit 1
fi

echo "✅ PM2 $(pm2 --version) ditemukan"

# ── Buat folder logs ────────────────────────────
mkdir -p logs
echo "✅ Folder logs siap"

# ── Install logrotate (sekali) ──────────────────
if ! pm2 list | grep -q "pm2-logrotate" 2>/dev/null; then
  echo "📦 Install pm2-logrotate..."
  pm2 install pm2-logrotate --silent 2>/dev/null || true
fi

# ── Start / Restart bot ─────────────────────────
if pm2 list | grep -q "downloader-ig-vt"; then
  echo "🔄 Merestart bot yang sudah berjalan..."
  pm2 restart ecosystem.config.js
else
  echo "🚀 Menjalankan bot untuk pertama kali..."
  pm2 start ecosystem.config.js
fi

# ── Simpan config PM2 (auto-start saat reboot) ──
pm2 save

echo ""
echo "✅ Bot berhasil dijalankan!"
echo ""
echo "📋 Perintah berguna:"
echo "   pm2 logs downloader-ig-vt     # Lihat log live"
echo "   pm2 status                   # Status bot"
echo "   pm2 restart downloader-ig-vt # Restart bot"
echo "   pm2 stop downloader-ig-vt    # Stop bot"
echo "   pm2 monit                    # Monitor real-time"

# 🚀 Deployment Guide

## Path Locations di Different Environments

### 🖥️ **Replit Environment**
```bash
Home directory:      /home/runner
Workspace directory: /home/runner/workspace
Project location:    /home/runner/workspace
```

**✅ CORRECT Paths:**
```bash
cd /home/runner/workspace   # ✅ Correct
cd ~/workspace              # ✅ Correct
python main.py              # ✅ Correct (from workspace dir)
```

**❌ WRONG Paths:**
```bash
cd ~/Instagram              # ❌ WRONG! Project di /home/runner/workspace
cd /home/runner/Instagram   # ❌ WRONG! 
```

---

### 🖥️ **VPS/Server (Custom Path)**
```bash
# Example if you clone to ~/Instagram
Home directory:      /home/yourusername
Project location:    /home/yourusername/Instagram
```

**Setup for VPS:**
```bash
# 1. Clone repository
cd ~
git clone https://github.com/tentangblockchain/Instagram.git
cd Instagram

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup .env
cp .env.example .env
nano .env  # Edit dengan credentials kamu

# 4. Start dengan PM2
bash start-pm2.sh
```

---

## PM2 Configuration

### Automatic Path Detection
File `ecosystem.config.js` menggunakan `process.cwd()` yang otomatis detect current directory:

```javascript
cwd: process.cwd(),  // Auto-detect current working directory
```

Ini artinya:
- ✅ **Replit**: Auto-detect `/home/runner/workspace`
- ✅ **VPS**: Auto-detect dari mana kamu run PM2 (contoh: `~/Instagram`)

### Manual Path Override (Optional)
Jika perlu specify path manual, edit `ecosystem.config.js`:

```javascript
// Untuk VPS dengan path custom
cwd: '/home/yourusername/Instagram',

// Atau gunakan environment variable
cwd: process.env.PROJECT_PATH || process.cwd(),
```

---

## Deployment Options

### Option 1: Replit Reserved VM (Recommended untuk Replit)
1. Sudah running di Replit workspace
2. Click "Deploy" → "Reserved VM"
3. Configure secrets
4. Done! Running 24/7

**Path di Production**: `/home/runner/workspace`

### Option 2: PM2 di VPS/Server
```bash
# Dari directory project
cd /path/to/project
bash start-pm2.sh

# PM2 akan auto-detect path
pm2 status
```

**Path**: Auto-detect dari current directory

### Option 3: Systemd (Alternative untuk VPS)
Create `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram Bot Downloader
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/Instagram
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable & start:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

---

## Verifikasi Path

### Check Current Working Directory
```bash
pwd
# Output: /home/runner/workspace (di Replit)
# Output: /home/username/Instagram (di VPS)
```

### Check Home Directory
```bash
echo $HOME
# Output: /home/runner (di Replit)
# Output: /home/username (di VPS)
```

### Verify PM2 Path
```bash
pm2 describe telegram-bot | grep cwd
# Pastikan cwd nya benar sesuai lokasi project
```

---

## Troubleshooting

### ❌ Error: "ModuleNotFoundError"
**Penyebab**: PM2 running dari directory yang salah

**Solusi**:
```bash
# Stop PM2
pm2 stop telegram-bot
pm2 delete telegram-bot

# Masuk ke directory project yang benar
cd /home/runner/workspace  # Replit
# ATAU
cd ~/Instagram             # VPS

# Start lagi
bash start-pm2.sh
```

### ❌ Error: "database.db not found"
**Penyebab**: Working directory salah

**Solusi**:
```bash
# Check PM2 working directory
pm2 describe telegram-bot

# Pastikan cwd = project directory
# Jika salah, edit ecosystem.config.js dan restart
```

### ❌ Error: ".env file not found"
**Penyebab**: .env tidak ada di working directory

**Solusi**:
```bash
# Pastikan .env ada di project directory
cd /home/runner/workspace  # atau path project kamu
ls -la .env

# Jika tidak ada, copy dari example
cp .env.example .env
nano .env  # Edit dengan credentials kamu
```

---

## Quick Reference

### Replit Environment
```bash
# Start bot
python main.py

# Atau dengan workflow (already running)
# Bot auto-start via Replit workflow
```

### PM2 Commands (VPS/Server)
```bash
# Start
pm2 start ecosystem.config.js

# Status
pm2 status

# Logs
pm2 logs telegram-bot

# Restart
pm2 restart telegram-bot

# Stop
pm2 stop telegram-bot

# Auto-startup
pm2 startup
pm2 save
```

---

## Environment Variables

Semua environment variables diload dari `.env` file yang harus ada di **project root directory**.

**Verify .env location**:
```bash
# Harus ada di same directory dengan main.py
ls -la .env main.py
```

---

**🎯 TL;DR**: PM2 config sekarang pakai `process.cwd()` jadi auto-detect path, tidak perlu hardcode `/home/runner/workspace` atau `~/Instagram`!

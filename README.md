# 🤖 Telegram Bot Downloader TikTok & Instagram

Bot Telegram untuk download konten TikTok dan Instagram dengan sistem VIP subscription menggunakan pembayaran Trakteer. Bot ini menggunakan bahasa Jawa (Javanese) untuk interaksi dengan user.

**GitHub Repository:** [https://github.com/tentangblockchain/Instagram](https://github.com/tentangblockchain/Instagram)

---

## ✨ Fitur Utama

### 📥 Download Content
- ✅ **TikTok**: Video & Photo/Slideshow
- ✅ **Instagram**: Post, Reel, Carousel/Album
- ✅ **Auto Caption**: Otomatis kirim caption dari konten
- ✅ **Fast Download**: Optimized untuk kecepatan maksimal

### 💎 Sistem VIP
- **User Gratis**: 10 download/hari
- **User VIP**: 100 download/hari
- **Paket VIP**:
  - 3 hari → Rp 5.000
  - 7 hari → Rp 10.000 (Recommended)
  - 15 hari → Rp 20.000
  - 30 hari → Rp 35.000 (Best Value)
  - 60 hari → Rp 60.000
  - 90 hari → Rp 80.000 (Super Saver)

### 💳 Payment Integration
- **Trakteer API**: Semi-automatic payment detection
- **Admin Approval**: Manual verification untuk keamanan
- **Auto VIP Activation**: Langsung aktif setelah approved

### 🔒 Security Features
- **Channel Membership Check**: Wajib join channel sebelum download
- **Daily Limit System**: Mencegah abuse
- **Database Tracking**: Semua aktivitas tercatat
- **Admin Only Commands**: Command khusus admin

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token (dari @BotFather)
- Trakteer API Key

### Installation

```bash
# Clone repository
git clone https://github.com/tentangblockchain/Instagram.git
cd Instagram
```
```bash
# Install dependencies
pip install -r requirements.txt
```
# Setup environment variables
cp .env.example .env
# Edit .env dengan credentials kamu
```

### Configuration (.env)

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=your_admin_id_1,your_admin_id_2
REQUIRED_CHANNEL=@your_channel
TRAKTEER_API_KEY=your_trakteer_api_key
TRAKTEER_USERNAME=your_trakteer_username
FREE_DAILY_LIMIT=10
VIP_DAILY_LIMIT=100
```

### Running the Bot

#### Option 1: Direct Run
```bash
python main.py
```

#### Option 2: PM2 (Recommended for Production)
```bash
# Install PM2 (jika belum)
npm install -g pm2
```
```bash
# Start bot dengan PM2
bash start-pm2.sh
```
```bash
# Atau manual
pm2 start ecosystem.config.js
```

#### Option 3: Replit Deployment
1. Import project ke Replit
2. Configure secrets di Replit
3. Click "Deploy" → pilih "Reserved VM"
4. Bot akan running 24/7

---

## 📱 Command List

### User Commands
- `/start` - Mulai bot dan register
- `/vip` - Lihat paket VIP dan beli
- `/status` - Cek status VIP kamu
- `/help` - Panduan lengkap

### Admin Commands
- `!cek` atau `!cp` - Sync pembayaran dari Trakteer
- `!pend` atau `!pa` - Lihat daftar payment pending
- `!listvip` - Lihat semua VIP user aktif
- `!delvip <user_id>` - Hapus VIP user
- `!debug` - Debug information

### Download Content
Kirim link langsung ke bot:
- TikTok: `https://vt.tiktok.com/...` atau `https://www.tiktok.com/...`
- Instagram: `https://www.instagram.com/p/...` atau `https://www.instagram.com/reel/...`

---

## 🔧 PM2 Management

### Start Bot
```bash
pm2 start ecosystem.config.js
```

### Monitor Bot
```bash
pm2 status              # Status bot
pm2 logs                # Live logs
pm2 logs --lines 100    # Last 100 lines
pm2 monit               # Real-time monitoring
```

### Control Bot
```bash
pm2 restart telegram-bot    # Restart bot
pm2 stop telegram-bot       # Stop bot
pm2 delete telegram-bot     # Remove from PM2
pm2 flush                   # Clear logs
```

### Auto-start on Server Reboot
```bash
pm2 startup             # Generate startup script
pm2 save                # Save current process list
```

---

## 🏗️ Architecture

### Tech Stack
- **Language**: Python 3.11
- **Framework**: python-telegram-bot 20.7
- **Database**: SQLite
- **Downloader**: yt-dlp + custom scraper
- **Scheduler**: APScheduler

### Project Structure
```
├── main.py                 # Main bot application
├── config.py               # Configuration loader
├── database.py             # Database handler
├── tiktok_downloader.py    # TikTok download engine (OPTIMIZED)
├── instagram_downloader.py # Instagram download engine (OPTIMIZED)
├── trakteer_api.py         # Trakteer payment integration
├── requirements.txt        # Python dependencies
├── ecosystem.config.js     # PM2 configuration
├── start-pm2.sh           # PM2 startup script
├── .env                    # Environment variables
└── database.db            # SQLite database (auto-created)
```

### Database Schema

#### Users Table
```sql
- user_id (PRIMARY KEY)
- username
- created_at
- is_vip
- vip_expires_at
```

#### Downloads Table
```sql
- id (AUTO INCREMENT)
- user_id (FOREIGN KEY)
- download_date
- created_at
```

#### Payments Table
```sql
- id (AUTO INCREMENT)
- user_id (FOREIGN KEY)
- days
- amount
- status (pending/approved/rejected)
- trakteer_id
- created_at
- updated_at
```

---

## ⚡ Performance Optimizations

Bot ini sudah dioptimasi untuk kecepatan maksimal:

### 🚀 Fast-Fail Strategy
- Deteksi error rate-limit/fatal error secara cepat
- Exit immediate tanpa mencoba format lain
- **Hasil**: 15-20 detik lebih cepat saat error

### ⏱️ Timeout Optimization
- Socket timeout: 10 detik
- Connection timeout: 10 detik
- Max retries: 2x
- **Hasil**: Tidak hang di network issues

### 🎯 Single Format Attempt
- Langsung gunakan format 'best'
- Tidak mencoba 5 format berbeda
- **Hasil**: 3x lebih cepat download

### 📡 Concurrent Downloads
- Parallel fragment downloads
- Optimized chunk size (10MB)
- **Hasil**: Download lebih smooth

---

## 🔐 Security Best Practices

1. **Environment Variables**: Semua secret disimpan di `.env`
2. **No Hardcoded Credentials**: Tidak ada credentials di code
3. **Admin Verification**: Payment butuh admin approval
4. **Database Protection**: SQLite dengan proper isolation
5. **Input Validation**: Semua user input divalidasi

---

## 📊 Monitoring & Logs

### Log Files (PM2)
```
logs/
├── pm2-error.log      # Error logs
├── pm2-out.log        # Output logs
└── pm2-combined.log   # Combined logs
```

### Database Statistics
```python
# Cek statistics via code
from database import Database
db = Database()
stats = db.get_user_stats()
print(stats)
```

---

## 🐛 Troubleshooting

### Bot tidak start
```bash
# Check logs
pm2 logs telegram-bot

# Restart bot
pm2 restart telegram-bot
```

### Instagram rate-limit
- **Penyebab**: Terlalu banyak request ke Instagram
- **Solusi**: Tunggu 30-60 menit, Instagram akan reset limit
- **Optimasi**: Bot sudah fast-fail untuk tidak waste waktu

### TikTok link expired
- **Penyebab**: Short link TikTok expire/video dihapus
- **Solusi**: Minta user kirim link baru
- **Deteksi**: Bot auto-detect dan kasih error jelas

### Database locked
```bash
# Stop bot
pm2 stop telegram-bot

# Backup database
cp database.db database.backup.db

# Restart bot
pm2 start telegram-bot
```

---

## 📈 Future Improvements

- [ ] Twitter/X download support
- [ ] YouTube Shorts download
- [ ] Auto-renewal VIP subscription
- [ ] Multiple payment gateway (OVO, Dana, GoPay)
- [ ] Referral system untuk bonus VIP
- [ ] Download queue untuk batch processing
- [ ] CDN integration untuk faster delivery

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

This project is for educational purposes. Respect content creators and platform terms of service.

---

## 💬 Support

- **GitHub Issues**: [https://github.com/tentangblockchain/Instagram/issues](https://github.com/tentangblockchain/Instagram/issues)
- **Telegram**: Contact admin via bot

---

## 🙏 Credits

- **yt-dlp**: For powerful media downloading
- **python-telegram-bot**: For Telegram bot framework
- **Trakteer**: For payment gateway
- **BeautifulSoup**: For HTML parsing
- **APScheduler**: For task scheduling

---

**Made with ❤️ for Indonesian Telegram users**

**Repository**: [https://github.com/tentangblockchain/Instagram](https://github.com/tentangblockchain/Instagram)

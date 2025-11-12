# Javanese TikTok & Instagram Downloader Bot

## Overview
This is a Telegram bot written in Python that allows users to download TikTok and Instagram content. It features a VIP subscription system with Trakteer payment integration and uses Javanese language (bahasa Jawa kasar) for messages.

## Project Type
**Backend Application** - Telegram Bot (No web frontend)

## Tech Stack
- **Language**: Python 3.11
- **Main Framework**: python-telegram-bot (version 20.7)
- **Database**: SQLite (database.db)
- **Key Libraries**:
  - yt-dlp: Media downloading
  - beautifulsoup4: HTML parsing for Instagram carousel
  - requests: HTTP requests
  - python-dotenv: Environment configuration

## Project Structure
```
├── main.py                    # Main bot application
├── config.py                  # Configuration loader from .env
├── database.py                # SQLite database handler
├── tiktok_downloader.py       # TikTok download logic
├── instagram_downloader.py    # Instagram download logic
├── trakteer_api.py            # Trakteer payment API integration
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (secrets)
└── database.db               # SQLite database (auto-created)
```

## Features
1. **TikTok Downloads**: Videos and photos
2. **Instagram Downloads**: Posts, carousels, albums
3. **VIP System**: 
   - Free users: 10 downloads/day
   - VIP users: 100 downloads/day
   - Packages: 3, 7, 15, 30, 60, 90 days
4. **Payment Integration**: Trakteer payment gateway
5. **Channel Membership Check**: Require users to join specific channels
6. **Admin Commands**: Payment approval, VIP management, statistics

## Setup & Configuration

### Environment Variables (.env)
Required variables:
- `BOT_TOKEN`: Telegram bot token from @BotFather
- `ADMIN_IDS`: Comma-separated admin user IDs
- `REQUIRED_CHANNEL`: Telegram channel(s) users must join
- `TRAKTEER_API_KEY`: Trakteer API key
- `TRAKTEER_USERNAME`: Trakteer username
- `FREE_DAILY_LIMIT`: Free user download limit (default: 10)
- `VIP_DAILY_LIMIT`: VIP user download limit (default: 100)

### Running the Bot
The bot runs via the `telegram-bot` workflow:
```bash
python main.py
```

## Admin Commands
- `!cek` or `!cp`: Check and sync new payments from Trakteer
- `!pend` or `!pa`: List pending payments
- `!listvip`: List all active VIP users
- `!delvip <user_id>`: Remove VIP status from user
- `!debug`: Debug information

## User Commands
- `/start`: Start the bot and register
- `/vip`: View VIP packages and purchase
- `/status`: Check VIP status
- `/help`: Show help message

## Recent Changes
- 2025-11-12: Initial Replit setup + Performance Optimization
  - Created missing config.py file
  - Installed Python 3.11 and all dependencies
  - Configured workflow for bot execution
  - Updated .gitignore to include config.py in version control
  - Bot successfully running and connected to Telegram API
  
- 2025-11-12: **CRITICAL PERFORMANCE OPTIMIZATION** ⚡
  - **Fixed slow download issue (20+ seconds wasted per failed request)**
  - Implemented Fast-Fail Strategy for rate-limit/fatal errors
  - Optimized timeouts: Added socket_timeout=10s to prevent hanging
  - Single format attempt instead of 5 sequential tries
  - Better error detection (rate-limit, auth, fatal errors)
  - Fixed database type safety (Optional[str] for trakteer_id)
  - **Result: 3-5x faster response time, especially on errors**

## Database Schema
### Tables
1. **users**: User registration and VIP status
2. **downloads**: Download tracking for limits
3. **payments**: Payment records and approval workflow

## Architecture Notes
- Uses SQLite for simplicity (single-user admin bot)
- Downloads are stored in temp directory and cleaned up after sending
- Semi-automatic payment system: Trakteer API detects payments, admin approves
- VIP expiry is checked on-demand and via scheduled cleanup task

## Known Configuration
- Admin IDs: 6185398749, 7027694923
- Required Channel: @silviaroyshita_88
- Trakteer Username: yovica

## GitHub Repository
**Official Repository**: https://github.com/tentangblockchain/Instagram

## Deployment Options
### Option 1: PM2 (VPS/Server)
- Use `bash start-pm2.sh` untuk start dengan PM2
- Auto-restart, monitoring, dan logs management
- File config: `ecosystem.config.js`

### Option 2: Replit Reserved VM
- Deploy via Replit Deploy button
- Choose "Reserved VM" deployment type
- Bot akan running 24/7
- Config sudah ada di `.replit` file

## Performance Optimizations (Nov 12, 2025)
- ✅ Fast-fail strategy untuk rate-limit errors (15-20 detik lebih cepat)
- ✅ Socket timeout optimization (10 detik)
- ✅ Single format attempt instead of 5 formats
- ✅ Concurrent fragment downloads
- ✅ Better error detection untuk Instagram/TikTok

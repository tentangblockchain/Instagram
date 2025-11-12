#!/bin/bash

# PM2 Start Script for Telegram Bot
# Usage: bash start-pm2.sh

echo "🚀 Starting Telegram Bot with PM2..."

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null
then
    echo "❌ PM2 not found. Installing PM2..."
    npm install -g pm2
fi

# Create logs directory if not exists
mkdir -p logs

# Stop existing instance if running
pm2 stop telegram-bot 2>/dev/null || true
pm2 delete telegram-bot 2>/dev/null || true

# Start bot with ecosystem config
pm2 start ecosystem.config.js

# Save PM2 process list
pm2 save

# Setup PM2 startup (optional - for auto-restart on server reboot)
# pm2 startup

echo "✅ Bot started successfully!"
echo ""
echo "📊 Useful PM2 Commands:"
echo "  pm2 status          - Check bot status"
echo "  pm2 logs            - View live logs"
echo "  pm2 logs --lines 50 - View last 50 lines"
echo "  pm2 restart telegram-bot - Restart bot"
echo "  pm2 stop telegram-bot    - Stop bot"
echo "  pm2 monit           - Monitor bot (CPU/RAM)"
echo "  pm2 flush           - Clear all logs"

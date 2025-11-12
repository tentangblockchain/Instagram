import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

class Config:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not found in environment variables")
        
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
        
        required_channels_str = os.getenv("REQUIRED_CHANNEL", "")
        self.REQUIRED_CHANNELS = [ch.strip() for ch in required_channels_str.split(",") if ch.strip()]
        
        self.FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "10"))
        self.VIP_DAILY_LIMIT = int(os.getenv("VIP_DAILY_LIMIT", "100"))
        
        self.TRAKTEER_API_KEY = os.getenv("TRAKTEER_API_KEY", "")
        self.TRAKTEER_USERNAME = os.getenv("TRAKTEER_USERNAME", "")
        
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")
        
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        logger.info(f"Config loaded: Admin IDs: {self.ADMIN_IDS}, Channels: {self.REQUIRED_CHANNELS}")

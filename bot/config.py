import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(override=True)


class Config:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN tidak ditemukan di environment variables")

        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(i.strip()) for i in admin_ids_str.split(",") if i.strip()]

        required_channels_str = os.getenv("REQUIRED_CHANNEL", "")
        self.REQUIRED_CHANNELS = [ch.strip() for ch in required_channels_str.split(",") if ch.strip()]

        self.FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "10"))
        self.VIP_DAILY_LIMIT = int(os.getenv("VIP_DAILY_LIMIT", "100"))

        self.SAWERIA_USERNAME = os.getenv("SAWERIA_USERNAME", "")
        self.SAWERIA_USER_ID = os.getenv("SAWERIA_USER_ID", "")

        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        logger.info(f"Konfigurasi dimuat — Admin: {self.ADMIN_IDS}, Channel: {self.REQUIRED_CHANNELS}")

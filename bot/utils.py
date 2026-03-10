"""Utility functions for bot"""
import re
import logging

logger = logging.getLogger(__name__)


def sanitize_text(text: str) -> str:
    """Clean text for Telegram caption
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text safe for Telegram
    """
    if not text:
        return ""

    text = re.sub(r'\s+', ' ', text.strip())
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        '',
        text
    )

    return text.strip()


class BotException(Exception):
    """Base exception for bot errors"""
    pass


class DownloadException(BotException):
    """Exception for download failures"""
    pass


class PaymentException(BotException):
    """Exception for payment processing"""
    pass


class DatabaseException(BotException):
    """Exception for database operations"""
    pass

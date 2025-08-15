# Telegram Trading Bot
# Production-ready cryptocurrency trading bot for Telegram

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "Advanced Telegram-based cryptocurrency trading bot with technical analysis"

# Package metadata
__title__ = "telegram-trading-bot"
__license__ = "MIT"
__url__ = "https://github.com/yourusername/telegram-trading-bot"

# Export main components
from config.config import ConfigManager, get_config
from database.database_manager import DatabaseManager
from exchange.crypto_exchange_api import CryptoExchangeAPI
from signals.signal_engine import SignalEngine, get_signal_engine
from telegram_bot.bot_core import TelegramTradingBot

__all__ = [
    "ConfigManager",
    "get_config", 
    "DatabaseManager",
    "CryptoExchangeAPI",
    "SignalEngine",
    "get_signal_engine",
    "TelegramTradingBot"
]

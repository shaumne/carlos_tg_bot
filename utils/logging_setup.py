#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional

def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/trading_bot.log",
    log_max_size: int = 10 * 1024 * 1024,  # 10MB
    log_backup_count: int = 5,
    console_output: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Gelişmiş logging kurulumu
    
    Args:
        log_level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log dosyası yolu
        log_max_size: Log dosyası maksimum boyutu (byte)
        log_backup_count: Tutulacak backup dosya sayısı
        console_output: Console'a da log yazılsın mı
        format_string: Özel log formatı
    
    Returns:
        Configured logger instance
    """
    
    # Log dizini oluştur
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Log seviyesi ayarla
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Root logger'ı temizle
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Log formatı
    if format_string is None:
        format_string = (
            '%(asctime)s | %(name)s | %(levelname)8s | '
            '%(filename)s:%(lineno)d | %(funcName)s() | %(message)s'
        )
    
    formatter = logging.Formatter(
        format_string,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger seviyesi ayarla
    root_logger.setLevel(numeric_level)
    
    # File handler (rotating)
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=log_max_size,
            backupCount=log_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}", file=sys.stderr)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # Console için daha kısa format
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Ana logger'ı döndür
    logger = logging.getLogger("telegram_trading_bot")
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")
    
    return logger

def setup_module_loggers():
    """Modül-spesifik logger'ları ayarla"""
    
    # Telegram bot logger
    telegram_logger = logging.getLogger("telegram.ext")
    telegram_logger.setLevel(logging.WARNING)  # Telegram kütüphanesi çok verbose
    
    # HTTP request logger
    urllib_logger = logging.getLogger("urllib3")
    urllib_logger.setLevel(logging.WARNING)
    
    # SQLite logger
    sqlite_logger = logging.getLogger("sqlite3")
    sqlite_logger.setLevel(logging.WARNING)
    
    # Exchange API logger
    exchange_logger = logging.getLogger("exchange_api")
    exchange_logger.setLevel(logging.INFO)
    
    # Signal engine logger
    signal_logger = logging.getLogger("signal_engine")
    signal_logger.setLevel(logging.INFO)
    
    # Database logger
    db_logger = logging.getLogger("database")
    db_logger.setLevel(logging.INFO)

class TradingBotLogger:
    """
    Trading bot için özelleştirilmiş logger wrapper
    Telegram bildirimleri ve özel log seviyeleri için
    """
    
    def __init__(self, name: str, telegram_notifier=None):
        self.logger = logging.getLogger(name)
        self.telegram_notifier = telegram_notifier
        self.critical_errors = []
        
    def debug(self, message: str, **kwargs):
        """Debug seviyesi log"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, notify_telegram: bool = False, **kwargs):
        """Info seviyesi log"""
        self.logger.info(message, **kwargs)
        if notify_telegram and self.telegram_notifier:
            self._send_telegram_notification("ℹ️", message)
    
    def warning(self, message: str, notify_telegram: bool = False, **kwargs):
        """Warning seviyesi log"""
        self.logger.warning(message, **kwargs)
        if notify_telegram and self.telegram_notifier:
            self._send_telegram_notification("⚠️", message)
    
    def error(self, message: str, notify_telegram: bool = True, **kwargs):
        """Error seviyesi log"""
        self.logger.error(message, **kwargs)
        if notify_telegram and self.telegram_notifier:
            self._send_telegram_notification("❌", message)
    
    def critical(self, message: str, notify_telegram: bool = True, **kwargs):
        """Critical seviyesi log"""
        self.logger.critical(message, **kwargs)
        self.critical_errors.append({
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'kwargs': kwargs
        })
        if notify_telegram and self.telegram_notifier:
            self._send_telegram_notification("🚨", f"CRITICAL: {message}")
    
    def trade_info(self, message: str, **kwargs):
        """Trade işlemleri için özel log"""
        self.logger.info(f"[TRADE] {message}", **kwargs)
        if self.telegram_notifier:
            self._send_telegram_notification("💰", message)
    
    def signal_info(self, message: str, **kwargs):
        """Sinyal işlemleri için özel log"""
        self.logger.info(f"[SIGNAL] {message}", **kwargs)
        if self.telegram_notifier:
            self._send_telegram_notification("📊", message)
    
    def system_info(self, message: str, **kwargs):
        """Sistem olayları için özel log"""
        self.logger.info(f"[SYSTEM] {message}", **kwargs)
        if self.telegram_notifier:
            self._send_telegram_notification("🔧", message)
    
    def _send_telegram_notification(self, emoji: str, message: str):
        """Telegram bildirimi gönder"""
        try:
            if self.telegram_notifier:
                formatted_message = f"{emoji} {message}"
                self.telegram_notifier.send_message(formatted_message)
        except Exception as e:
            # Telegram bildirimi başarısızsa sadece normal log yaz
            self.logger.error(f"Failed to send Telegram notification: {str(e)}")
    
    def get_critical_errors(self) -> list:
        """Critical error'ları döndür"""
        return self.critical_errors.copy()
    
    def clear_critical_errors(self):
        """Critical error listesini temizle"""
        self.critical_errors.clear()

def create_logger(name: str, telegram_notifier=None) -> TradingBotLogger:
    """TradingBotLogger instance oluştur"""
    return TradingBotLogger(name, telegram_notifier)

# Başlangıç log mesajları için yardımcı fonksiyon
def log_startup_info(logger: logging.Logger, config_summary: dict):
    """Başlangıç bilgilerini logla"""
    logger.info("=" * 80)
    logger.info("🤖 TELEGRAM TRADING BOT STARTING UP")
    logger.info("=" * 80)
    
    logger.info("📋 Configuration Summary:")
    for section, settings in config_summary.items():
        logger.info(f"  {section.upper()}:")
        for key, value in settings.items():
            logger.info(f"    {key}: {value}")
    
    logger.info("=" * 80)
    logger.info("🚀 Bot initialization complete, starting main loop...")
    logger.info("=" * 80)

def log_shutdown_info(logger: logging.Logger, stats: dict = None):
    """Kapanış bilgilerini logla"""
    logger.info("=" * 80)
    logger.info("🛑 TELEGRAM TRADING BOT SHUTTING DOWN")
    logger.info("=" * 80)
    
    if stats:
        logger.info("📊 Session Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
    
    logger.info("=" * 80)
    logger.info("👋 Bot shutdown complete")
    logger.info("=" * 80)

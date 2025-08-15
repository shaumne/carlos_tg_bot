#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class TelegramConfig:
    """Telegram bot konfigürasyonu"""
    bot_token: str
    chat_id: str
    authorized_users: List[int]
    admin_users: List[int]
    webhook_url: Optional[str] = None
    webhook_port: int = 8443
    max_message_length: int = 4096
    parse_mode: str = "Markdown"
    
    def __post_init__(self):
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is required")

@dataclass
class ExchangeConfig:
    """Kripto borsa API konfigürasyonu"""
    api_key: str
    api_secret: str
    base_url: str = "https://api.crypto.com/exchange/v1/"
    account_url: str = "https://api.crypto.com/v2/"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 10
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("CRYPTO_API_KEY environment variable is required")
        if not self.api_secret:
            raise ValueError("CRYPTO_API_SECRET environment variable is required")

@dataclass
class TradingConfig:
    """Trading parametreleri"""
    trade_amount: float = 10.0  # USDT cinsinden
    max_positions: int = 5
    risk_per_trade: float = 2.0  # Yüzde
    enable_auto_trading: bool = False
    enable_paper_trading: bool = False
    min_balance_required: float = 15.0  # USDT
    
    # Teknik analiz parametreleri
    atr_period: int = 14
    atr_multiplier: float = 2.0
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    ma_period: int = 20
    ema_period: int = 12
    
    # Risk yönetimi
    max_drawdown: float = 10.0  # Yüzde
    stop_loss_percentage: float = 5.0
    take_profit_percentage: float = 10.0
    trailing_stop_enabled: bool = True
    trailing_stop_percentage: float = 3.0

@dataclass
class MonitoringConfig:
    """İzleme ve bildirim ayarları"""
    signal_check_interval: int = 30  # saniye
    position_check_interval: int = 60  # saniye
    price_update_interval: int = 10  # saniye
    health_check_interval: int = 300  # saniye
    
    # Bildirim seviyeleri
    notify_signals: bool = True
    notify_trades: bool = True
    notify_errors: bool = True
    notify_system_events: bool = True
    
    # Log ayarları
    log_level: str = "INFO"
    log_file: str = "logs/trading_bot.log"
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # Metrik toplama
    enable_metrics: bool = True
    metrics_interval: int = 60  # saniye

@dataclass
class DatabaseConfig:
    """Veritabanı konfigürasyonu"""
    db_path: str = "data/trading_bot.db"
    backup_enabled: bool = True
    backup_interval: int = 3600  # saniye (1 saat)
    backup_retention_days: int = 30
    auto_vacuum: bool = True
    connection_timeout: int = 30
    
    def __post_init__(self):
        # Database dizini oluştur
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

@dataclass
class SecurityConfig:
    """Güvenlik ayarları"""
    encryption_key: Optional[str] = None
    session_timeout: int = 3600  # saniye
    max_failed_attempts: int = 5
    rate_limit_window: int = 60  # saniye
    rate_limit_max_requests: int = 30
    enable_audit_log: bool = True

class ConfigManager:
    """
    Merkezi konfigürasyon yöneticisi
    Environment variables, config files ve database ayarlarını yönetir
    """
    
    def __init__(self, config_file: str = "config/config.json"):
        self.config_file = config_file
        self._config_data = {}
        
        # Load configurations
        self.load_config()
        
        # Initialize configuration objects
        self.telegram = self._create_telegram_config()
        self.exchange = self._create_exchange_config()
        self.trading = self._create_trading_config()
        self.monitoring = self._create_monitoring_config()
        self.database = self._create_database_config()
        self.security = self._create_security_config()
        
        logger.info("Configuration manager initialized successfully")
    
    def load_config(self):
        """Konfigürasyon dosyasını yükle"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                logger.info("No config file found, using default values")
                self._config_data = {}
        except Exception as e:
            logger.error(f"Failed to load config file: {str(e)}")
            self._config_data = {}
    
    def save_config(self):
        """Konfigürasyonu dosyaya kaydet"""
        try:
            # Config dizini oluştur
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Create config data from current settings
            config_data = {
                'telegram': asdict(self.telegram),
                'exchange': asdict(self.exchange),
                'trading': asdict(self.trading),
                'monitoring': asdict(self.monitoring),
                'database': asdict(self.database),
                'security': asdict(self.security)
            }
            
            # Remove sensitive data before saving
            config_data['telegram']['bot_token'] = "***HIDDEN***"
            config_data['exchange']['api_key'] = "***HIDDEN***"
            config_data['exchange']['api_secret'] = "***HIDDEN***"
            if config_data['security']['encryption_key']:
                config_data['security']['encryption_key'] = "***HIDDEN***"
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {str(e)}")
            return False
    
    def _create_telegram_config(self) -> TelegramConfig:
        """Telegram konfigürasyonunu oluştur"""
        config_section = self._config_data.get('telegram', {})
        
        # Environment variables'ı öncelikle kullan
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', config_section.get('bot_token', ''))
        chat_id = os.getenv('TELEGRAM_CHAT_ID', config_section.get('chat_id', ''))
        
        # Authorized users - env var'dan JSON string olarak alınabilir
        authorized_users_env = os.getenv('TELEGRAM_AUTHORIZED_USERS', '')
        if authorized_users_env:
            try:
                authorized_users = json.loads(authorized_users_env)
            except json.JSONDecodeError:
                # Comma-separated list olarak da kabul et
                authorized_users = [int(x.strip()) for x in authorized_users_env.split(',') if x.strip().isdigit()]
        else:
            authorized_users = config_section.get('authorized_users', [])
        
        admin_users_env = os.getenv('TELEGRAM_ADMIN_USERS', '')
        if admin_users_env:
            try:
                admin_users = json.loads(admin_users_env)
            except json.JSONDecodeError:
                admin_users = [int(x.strip()) for x in admin_users_env.split(',') if x.strip().isdigit()]
        else:
            admin_users = config_section.get('admin_users', [])
        
        return TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id,
            authorized_users=authorized_users,
            admin_users=admin_users,
            webhook_url=os.getenv('TELEGRAM_WEBHOOK_URL', config_section.get('webhook_url')),
            webhook_port=int(os.getenv('TELEGRAM_WEBHOOK_PORT', config_section.get('webhook_port', 8443))),
            max_message_length=config_section.get('max_message_length', 4096),
            parse_mode=config_section.get('parse_mode', 'Markdown')
        )
    
    def _create_exchange_config(self) -> ExchangeConfig:
        """Exchange konfigürasyonunu oluştur"""
        config_section = self._config_data.get('exchange', {})
        
        return ExchangeConfig(
            api_key=os.getenv('CRYPTO_API_KEY', config_section.get('api_key', '')),
            api_secret=os.getenv('CRYPTO_API_SECRET', config_section.get('api_secret', '')),
            base_url=os.getenv('CRYPTO_BASE_URL', config_section.get('base_url', 'https://api.crypto.com/exchange/v1/')),
            account_url=os.getenv('CRYPTO_ACCOUNT_URL', config_section.get('account_url', 'https://api.crypto.com/v2/')),
            timeout=int(os.getenv('CRYPTO_TIMEOUT', config_section.get('timeout', 30))),
            max_retries=int(os.getenv('CRYPTO_MAX_RETRIES', config_section.get('max_retries', 3))),
            rate_limit_per_minute=int(os.getenv('CRYPTO_RATE_LIMIT', config_section.get('rate_limit_per_minute', 10)))
        )
    
    def _create_trading_config(self) -> TradingConfig:
        """Trading konfigürasyonunu oluştur"""
        config_section = self._config_data.get('trading', {})
        
        return TradingConfig(
            trade_amount=float(os.getenv('TRADE_AMOUNT', config_section.get('trade_amount', 10.0))),
            max_positions=int(os.getenv('MAX_POSITIONS', config_section.get('max_positions', 5))),
            risk_per_trade=float(os.getenv('RISK_PER_TRADE', config_section.get('risk_per_trade', 2.0))),
            enable_auto_trading=os.getenv('ENABLE_AUTO_TRADING', str(config_section.get('enable_auto_trading', False))).lower() == 'true',
            enable_paper_trading=os.getenv('ENABLE_PAPER_TRADING', str(config_section.get('enable_paper_trading', False))).lower() == 'true',
            min_balance_required=float(os.getenv('MIN_BALANCE_REQUIRED', config_section.get('min_balance_required', 15.0))),
            
            # Teknik analiz
            atr_period=int(os.getenv('ATR_PERIOD', config_section.get('atr_period', 14))),
            atr_multiplier=float(os.getenv('ATR_MULTIPLIER', config_section.get('atr_multiplier', 2.0))),
            rsi_period=int(os.getenv('RSI_PERIOD', config_section.get('rsi_period', 14))),
            rsi_oversold=float(os.getenv('RSI_OVERSOLD', config_section.get('rsi_oversold', 30.0))),
            rsi_overbought=float(os.getenv('RSI_OVERBOUGHT', config_section.get('rsi_overbought', 70.0))),
            ma_period=int(os.getenv('MA_PERIOD', config_section.get('ma_period', 20))),
            ema_period=int(os.getenv('EMA_PERIOD', config_section.get('ema_period', 12))),
            
            # Risk yönetimi
            max_drawdown=float(os.getenv('MAX_DRAWDOWN', config_section.get('max_drawdown', 10.0))),
            stop_loss_percentage=float(os.getenv('STOP_LOSS_PERCENTAGE', config_section.get('stop_loss_percentage', 5.0))),
            take_profit_percentage=float(os.getenv('TAKE_PROFIT_PERCENTAGE', config_section.get('take_profit_percentage', 10.0))),
            trailing_stop_enabled=os.getenv('TRAILING_STOP_ENABLED', str(config_section.get('trailing_stop_enabled', True))).lower() == 'true',
            trailing_stop_percentage=float(os.getenv('TRAILING_STOP_PERCENTAGE', config_section.get('trailing_stop_percentage', 3.0)))
        )
    
    def _create_monitoring_config(self) -> MonitoringConfig:
        """Monitoring konfigürasyonunu oluştur"""
        config_section = self._config_data.get('monitoring', {})
        
        return MonitoringConfig(
            signal_check_interval=int(os.getenv('SIGNAL_CHECK_INTERVAL', config_section.get('signal_check_interval', 30))),
            position_check_interval=int(os.getenv('POSITION_CHECK_INTERVAL', config_section.get('position_check_interval', 60))),
            price_update_interval=int(os.getenv('PRICE_UPDATE_INTERVAL', config_section.get('price_update_interval', 10))),
            health_check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', config_section.get('health_check_interval', 300))),
            
            # Notifications
            notify_signals=os.getenv('NOTIFY_SIGNALS', str(config_section.get('notify_signals', True))).lower() == 'true',
            notify_trades=os.getenv('NOTIFY_TRADES', str(config_section.get('notify_trades', True))).lower() == 'true',
            notify_errors=os.getenv('NOTIFY_ERRORS', str(config_section.get('notify_errors', True))).lower() == 'true',
            notify_system_events=os.getenv('NOTIFY_SYSTEM_EVENTS', str(config_section.get('notify_system_events', True))).lower() == 'true',
            
            # Logging
            log_level=os.getenv('LOG_LEVEL', config_section.get('log_level', 'INFO')),
            log_file=os.getenv('LOG_FILE', config_section.get('log_file', 'logs/trading_bot.log')),
            log_max_size=int(os.getenv('LOG_MAX_SIZE', config_section.get('log_max_size', 10 * 1024 * 1024))),
            log_backup_count=int(os.getenv('LOG_BACKUP_COUNT', config_section.get('log_backup_count', 5))),
            
            # Metrics
            enable_metrics=os.getenv('ENABLE_METRICS', str(config_section.get('enable_metrics', True))).lower() == 'true',
            metrics_interval=int(os.getenv('METRICS_INTERVAL', config_section.get('metrics_interval', 60)))
        )
    
    def _create_database_config(self) -> DatabaseConfig:
        """Database konfigürasyonunu oluştur"""
        config_section = self._config_data.get('database', {})
        
        return DatabaseConfig(
            db_path=os.getenv('DB_PATH', config_section.get('db_path', 'data/trading_bot.db')),
            backup_enabled=os.getenv('BACKUP_ENABLED', str(config_section.get('backup_enabled', True))).lower() == 'true',
            backup_interval=int(os.getenv('BACKUP_INTERVAL', config_section.get('backup_interval', 3600))),
            backup_retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', config_section.get('backup_retention_days', 30))),
            auto_vacuum=os.getenv('AUTO_VACUUM', str(config_section.get('auto_vacuum', True))).lower() == 'true',
            connection_timeout=int(os.getenv('CONNECTION_TIMEOUT', config_section.get('connection_timeout', 30)))
        )
    
    def _create_security_config(self) -> SecurityConfig:
        """Security konfigürasyonunu oluştur"""
        config_section = self._config_data.get('security', {})
        
        return SecurityConfig(
            encryption_key=os.getenv('ENCRYPTION_KEY', config_section.get('encryption_key')),
            session_timeout=int(os.getenv('SESSION_TIMEOUT', config_section.get('session_timeout', 3600))),
            max_failed_attempts=int(os.getenv('MAX_FAILED_ATTEMPTS', config_section.get('max_failed_attempts', 5))),
            rate_limit_window=int(os.getenv('RATE_LIMIT_WINDOW', config_section.get('rate_limit_window', 60))),
            rate_limit_max_requests=int(os.getenv('RATE_LIMIT_MAX_REQUESTS', config_section.get('rate_limit_max_requests', 30))),
            enable_audit_log=os.getenv('ENABLE_AUDIT_LOG', str(config_section.get('enable_audit_log', True))).lower() == 'true'
        )
    
    def update_setting(self, section: str, key: str, value: Any) -> bool:
        """Dinamik ayar güncelleme"""
        try:
            if hasattr(self, section):
                config_obj = getattr(self, section)
                if hasattr(config_obj, key):
                    setattr(config_obj, key, value)
                    logger.info(f"Updated {section}.{key} = {value}")
                    return True
                else:
                    logger.error(f"Invalid key: {section}.{key}")
                    return False
            else:
                logger.error(f"Invalid section: {section}")
                return False
        except Exception as e:
            logger.error(f"Failed to update setting {section}.{key}: {str(e)}")
            return False
    
    def get_setting(self, section: str, key: str, default_value: Any = None) -> Any:
        """Ayar değeri getir"""
        try:
            if hasattr(self, section):
                config_obj = getattr(self, section)
                if hasattr(config_obj, key):
                    return getattr(config_obj, key)
                else:
                    return default_value
            else:
                return default_value
        except Exception as e:
            logger.error(f"Failed to get setting {section}.{key}: {str(e)}")
            return default_value
    
    def validate_config(self) -> tuple[bool, List[str]]:
        """Konfigürasyon doğrulaması"""
        errors = []
        
        try:
            # Telegram validation
            if not self.telegram.bot_token:
                errors.append("Telegram bot token is required")
            if not self.telegram.chat_id:
                errors.append("Telegram chat ID is required")
            
            # Exchange validation
            if not self.exchange.api_key:
                errors.append("Exchange API key is required")
            if not self.exchange.api_secret:
                errors.append("Exchange API secret is required")
            
            # Trading validation
            if self.trading.trade_amount <= 0:
                errors.append("Trade amount must be positive")
            if self.trading.max_positions <= 0:
                errors.append("Max positions must be positive")
            if not (0 < self.trading.risk_per_trade <= 100):
                errors.append("Risk per trade must be between 0 and 100 percent")
            
            # Database validation
            if not os.path.exists(os.path.dirname(self.database.db_path)):
                try:
                    os.makedirs(os.path.dirname(self.database.db_path), exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create database directory: {str(e)}")
            
            # Log directory validation
            log_dir = os.path.dirname(self.monitoring.log_file)
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create log directory: {str(e)}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Configuration validation error: {str(e)}")
            return False, errors
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Konfigürasyon özeti (hassas bilgiler gizlenir)"""
        return {
            'telegram': {
                'chat_id': self.telegram.chat_id,
                'authorized_users_count': len(self.telegram.authorized_users),
                'admin_users_count': len(self.telegram.admin_users),
                'webhook_configured': bool(self.telegram.webhook_url)
            },
            'exchange': {
                'base_url': self.exchange.base_url,
                'timeout': self.exchange.timeout,
                'rate_limit': self.exchange.rate_limit_per_minute
            },
            'trading': {
                'trade_amount': self.trading.trade_amount,
                'max_positions': self.trading.max_positions,
                'auto_trading_enabled': self.trading.enable_auto_trading,
                'paper_trading_enabled': self.trading.enable_paper_trading,
                'risk_per_trade': self.trading.risk_per_trade
            },
            'monitoring': {
                'signal_check_interval': self.monitoring.signal_check_interval,
                'log_level': self.monitoring.log_level,
                'notifications_enabled': any([
                    self.monitoring.notify_signals,
                    self.monitoring.notify_trades,
                    self.monitoring.notify_errors
                ])
            },
            'database': {
                'db_path': self.database.db_path,
                'backup_enabled': self.database.backup_enabled,
                'backup_interval': self.database.backup_interval
            },
            'security': {
                'session_timeout': self.security.session_timeout,
                'rate_limiting_enabled': self.security.rate_limit_max_requests > 0,
                'audit_log_enabled': self.security.enable_audit_log
            }
        }

# Singleton config instance
_config_instance = None

def get_config() -> ConfigManager:
    """Global config instance getter"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance

def reload_config():
    """Config'i yeniden yükle"""
    global _config_instance
    _config_instance = ConfigManager()
    return _config_instance

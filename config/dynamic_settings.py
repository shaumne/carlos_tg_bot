#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dynamic Settings Manager
System allowing users to change settings at runtime

Priority Order:
1. Database settings (runtime changes) - HIGHEST
2. Environment variables (.env file) - MEDIUM  
3. Default values (hardcoded) - LOWEST
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import threading
import json

logger = logging.getLogger(__name__)

class DynamicSettingsManager:
    """
    Runtime changeable setting management system
    
    Features:
    - Hot reload (restart gerektirmez)
    - Database persistence
    - Priority system (DB > ENV > Default)
    - Thread-safe operations
    - Change notifications
    """
    
    def __init__(self, config_manager, database_manager):
        self.config = config_manager
        self.db = database_manager
        self._lock = threading.RLock()
        self._cached_settings = {}
        self._change_callbacks = {}
        
        # User-configurable settings kategorileri
        self.user_configurable_settings = {
            'trading': {
                'trade_amount': {
                    'type': 'float',
                    'min_value': 1.0,
                    'max_value': 1000.0,
                    'description': 'Trade amount (USDT)',
                    'restart_required': False
                },
                'max_positions': {
                    'type': 'int', 
                    'min_value': 1,
                    'max_value': 20,
                    'description': 'Maximum position count',
                    'restart_required': False
                },
                'risk_per_trade': {
                    'type': 'float',
                    'min_value': 0.5,
                    'max_value': 10.0,
                    'description': 'Risk per trade (%)',
                    'restart_required': False
                },
                'enable_auto_trading': {
                    'type': 'bool',
                    'description': 'Automatic trading active/inactive',
                    'restart_required': False
                },
                'stop_loss_percentage': {
                    'type': 'float',
                    'min_value': 1.0,
                    'max_value': 20.0,
                    'description': 'Stop loss percentage (%)',
                    'restart_required': False
                },
                'take_profit_percentage': {
                    'type': 'float',
                    'min_value': 1.0,
                    'max_value': 50.0,
                    'description': 'Take profit percentage (%)',
                    'restart_required': False
                }
            },
            'technical': {
                'rsi_oversold': {
                    'type': 'float',
                    'min_value': 10.0,
                    'max_value': 40.0,
                    'description': 'RSI oversold level',
                    'restart_required': False
                },
                'rsi_overbought': {
                    'type': 'float',
                    'min_value': 60.0,
                    'max_value': 90.0,
                    'description': 'RSI overbought level',
                    'restart_required': False
                },
                'atr_multiplier': {
                    'type': 'float',
                    'min_value': 1.0,
                    'max_value': 5.0,
                    'description': 'ATR multiplier (for stop loss)',
                    'restart_required': False
                }
            },
            'notifications': {
                'notify_signals': {
                    'type': 'bool',
                    'description': 'Signal notifications',
                    'restart_required': False
                },
                'notify_trades': {
                    'type': 'bool', 
                    'description': 'Trade notifications',
                    'restart_required': False
                },
                'notify_errors': {
                    'type': 'bool',
                    'description': 'Error notifications',
                    'restart_required': False
                }
            },
            'system': {
                'signal_check_interval': {
                    'type': 'int',
                    'min_value': 10,
                    'max_value': 300,
                    'description': 'Signal check interval (seconds)',
                    'restart_required': True
                },
                'backup_enabled': {
                    'type': 'bool',
                    'description': 'Automatic backup',
                    'restart_required': False
                }
            }
        }
        
        logger.info("Dynamic Settings Manager initialized")
    
    def get_setting(self, category: str, key: str, default_value: Any = None) -> Any:
        """
        Get setting value (priority order: DB > ENV > Default)
        """
        with self._lock:
            try:
                # 1. Check from database (highest priority)
                db_key = f"{category}.{key}"
                db_value = self.db.get_setting(db_key)
                
                if db_value is not None:
                    logger.debug(f"Setting from DB: {db_key} = {db_value}")
                    return self._convert_value_type(db_value, category, key)
                
                # 2. Config manager'dan (ENV variables)
                config_value = self.config.get_setting(category, key)
                
                if config_value is not None:
                    logger.debug(f"Setting from ENV: {category}.{key} = {config_value}")
                    return config_value
                
                # 3. Default value
                if default_value is not None:
                    logger.debug(f"Setting from DEFAULT: {category}.{key} = {default_value}")
                    return default_value
                
                # 4. None if nothing found
                logger.warning(f"Setting not found: {category}.{key}")
                return None
                
            except Exception as e:
                logger.error(f"Error getting setting {category}.{key}: {str(e)}")
                return default_value
    
    def set_setting(self, category: str, key: str, value: Any, user_id: int = None) -> bool:
        """
        Set setting value and save to database
        """
        with self._lock:
            try:
                # Validation
                if not self._validate_setting(category, key, value):
                    logger.error(f"Invalid setting value: {category}.{key} = {value}")
                    return False
                
                # Database'e kaydet
                db_key = f"{category}.{key}"
                description = self._get_setting_description(category, key)
                
                success = self.db.set_setting(
                    key=db_key,
                    value=value,
                    description=description
                )
                
                if success:
                    # Cache'i temizle
                    cache_key = f"{category}.{key}"
                    if cache_key in self._cached_settings:
                        del self._cached_settings[cache_key]
                    
                    # Call change callbacks
                    self._notify_setting_changed(category, key, value, user_id)
                    
                    logger.info(f"Setting updated: {category}.{key} = {value} (user: {user_id})")
                    
                    # Audit log
                    self.db.log_event(
                        level="INFO",
                        module="dynamic_settings",
                        message=f"Setting changed: {category}.{key} = {value}",
                        details={"old_value": self.get_setting(category, key), "new_value": value},
                        telegram_id=user_id
                    )
                    
                    return True
                else:
                    logger.error(f"Failed to save setting to database: {category}.{key}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error setting {category}.{key}: {str(e)}")
                return False
    
    def get_user_configurable_settings(self) -> Dict[str, Dict]:
        """Get user-changeable settings"""
        return self.user_configurable_settings.copy()
    
    def get_category_settings(self, category: str) -> Dict[str, Any]:
        """Get all settings in a category"""
        try:
            if category not in self.user_configurable_settings:
                return {}
            
            result = {}
            for key, config in self.user_configurable_settings[category].items():
                current_value = self.get_setting(category, key)
                result[key] = {
                    'value': current_value,
                    'description': config.get('description', ''),
                    'type': config.get('type', 'string'),
                    'min_value': config.get('min_value'),
                    'max_value': config.get('max_value'),
                    'restart_required': config.get('restart_required', False)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting category settings {category}: {str(e)}")
            return {}
    
    def reset_setting(self, category: str, key: str, user_id: int = None) -> bool:
        """Reset setting to default value (delete from database)"""
        with self._lock:
            try:
                db_key = f"{category}.{key}"
                
                # Database'den sil
                query = "DELETE FROM bot_settings WHERE key = ?"
                rows_affected = self.db.execute_update(query, (db_key,))
                
                if rows_affected > 0:
                    # Cache'i temizle
                    cache_key = f"{category}.{key}"
                    if cache_key in self._cached_settings:
                        del self._cached_settings[cache_key]
                    
                    logger.info(f"Setting reset to default: {category}.{key} (user: {user_id})")
                    
                    # Audit log
                    self.db.log_event(
                        level="INFO", 
                        module="dynamic_settings",
                        message=f"Setting reset: {category}.{key}",
                        telegram_id=user_id
                    )
                    
                    return True
                else:
                    logger.warning(f"Setting not found in database: {category}.{key}")
                    return True  # Zaten default durumda
                    
            except Exception as e:
                logger.error(f"Error resetting setting {category}.{key}: {str(e)}")
                return False
    
    def _validate_setting(self, category: str, key: str, value: Any) -> bool:
        """Validate setting value"""
        try:
            if category not in self.user_configurable_settings:
                return False
            
            if key not in self.user_configurable_settings[category]:
                return False
            
            config = self.user_configurable_settings[category][key]
            value_type = config.get('type', 'string')
            
            # Type validation
            if value_type == 'bool':
                if not isinstance(value, bool):
                    try:
                        # Convert string to bool
                        value = str(value).lower() in ('true', '1', 'yes', 'on')
                    except:
                        return False
            elif value_type == 'int':
                try:
                    value = int(value)
                except:
                    return False
            elif value_type == 'float':
                try:
                    value = float(value)
                except:
                    return False
            
            # Range validation
            if value_type in ['int', 'float']:
                min_val = config.get('min_value')
                max_val = config.get('max_value')
                
                if min_val is not None and value < min_val:
                    return False
                
                if max_val is not None and value > max_val:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating setting: {str(e)}")
            return False
    
    def _convert_value_type(self, value: Any, category: str, key: str) -> Any:
        """Convert value to correct type"""
        try:
            if category not in self.user_configurable_settings:
                return value
            
            if key not in self.user_configurable_settings[category]:
                return value
            
            config = self.user_configurable_settings[category][key]
            value_type = config.get('type', 'string')
            
            if value_type == 'bool':
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            elif value_type == 'int':
                return int(value)
            elif value_type == 'float':
                return float(value)
            else:
                return str(value)
                
        except Exception as e:
            logger.error(f"Error converting value type: {str(e)}")
            return value
    
    def _get_setting_description(self, category: str, key: str) -> str:
        """Get setting description"""
        try:
            if category in self.user_configurable_settings:
                if key in self.user_configurable_settings[category]:
                    return self.user_configurable_settings[category][key].get('description', '')
            return f"{category}.{key}"
        except:
            return f"{category}.{key}"
    
    def register_change_callback(self, category: str, key: str, callback):
        """Register callback for setting change"""
        callback_key = f"{category}.{key}"
        if callback_key not in self._change_callbacks:
            self._change_callbacks[callback_key] = []
        self._change_callbacks[callback_key].append(callback)
    
    def _notify_setting_changed(self, category: str, key: str, new_value: Any, user_id: int = None):
        """Call setting change callbacks"""
        try:
            callback_key = f"{category}.{key}"
            if callback_key in self._change_callbacks:
                for callback in self._change_callbacks[callback_key]:
                    try:
                        callback(category, key, new_value, user_id)
                    except Exception as e:
                        logger.error(f"Error in setting change callback: {str(e)}")
        except Exception as e:
            logger.error(f"Error notifying setting change: {str(e)}")
    
    def export_settings(self) -> Dict[str, Any]:
        """Export all custom settings"""
        try:
            exported = {}
            
            for category in self.user_configurable_settings:
                exported[category] = {}
                for key in self.user_configurable_settings[category]:
                    value = self.get_setting(category, key)
                    if value is not None:
                        exported[category][key] = value
            
            return exported
            
        except Exception as e:
            logger.error(f"Error exporting settings: {str(e)}")
            return {}
    
    def import_settings(self, settings_dict: Dict[str, Any], user_id: int = None) -> bool:
        """Settings'leri import et"""
        try:
            success_count = 0
            total_count = 0
            
            for category, category_settings in settings_dict.items():
                if not isinstance(category_settings, dict):
                    continue
                    
                for key, value in category_settings.items():
                    total_count += 1
                    if self.set_setting(category, key, value, user_id):
                        success_count += 1
            
            logger.info(f"Settings import: {success_count}/{total_count} successful")
            return success_count == total_count
            
        except Exception as e:
            logger.error(f"Error importing settings: {str(e)}")
            return False
    
    def get_settings_requiring_restart(self) -> List[str]:
        """Get settings requiring restart"""
        restart_required = []
        
        try:
            for category, category_settings in self.user_configurable_settings.items():
                for key, config in category_settings.items():
                    if config.get('restart_required', False):
                        # Check if this setting exists in database
                        db_key = f"{category}.{key}"
                        db_value = self.db.get_setting(db_key)
                        if db_value is not None:
                            restart_required.append(f"{category}.{key}")
            
            return restart_required
            
        except Exception as e:
            logger.error(f"Error getting restart required settings: {str(e)}")
            return []
    
    def apply_runtime_settings(self, config_manager):
        """Runtime settings'leri config manager'a uygula"""
        try:
            updated_count = 0
            
            # Trading settings
            trading_amount = self.get_setting('trading', 'trade_amount')
            if trading_amount is not None:
                config_manager.trading.trade_amount = float(trading_amount)
                updated_count += 1
            
            max_positions = self.get_setting('trading', 'max_positions')
            if max_positions is not None:
                config_manager.trading.max_positions = int(max_positions)
                updated_count += 1
            
            risk_per_trade = self.get_setting('trading', 'risk_per_trade')
            if risk_per_trade is not None:
                config_manager.trading.risk_per_trade = float(risk_per_trade)
                updated_count += 1
            
            enable_auto_trading = self.get_setting('trading', 'enable_auto_trading')
            if enable_auto_trading is not None:
                config_manager.trading.enable_auto_trading = bool(enable_auto_trading)
                updated_count += 1
            
            # Technical settings
            rsi_oversold = self.get_setting('technical', 'rsi_oversold')
            if rsi_oversold is not None:
                config_manager.trading.rsi_oversold = float(rsi_oversold)
                updated_count += 1
            
            rsi_overbought = self.get_setting('technical', 'rsi_overbought')
            if rsi_overbought is not None:
                config_manager.trading.rsi_overbought = float(rsi_overbought)
                updated_count += 1
            
            # Notification settings
            notify_signals = self.get_setting('notifications', 'notify_signals')
            if notify_signals is not None:
                config_manager.monitoring.notify_signals = bool(notify_signals)
                updated_count += 1
            
            logger.info(f"Applied {updated_count} runtime settings to config manager")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"Error applying runtime settings: {str(e)}")
            return False

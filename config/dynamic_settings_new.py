#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Dynamic Settings Manager
System allowing users to change settings at runtime with JSON configuration

Priority Order:
1. Database settings (runtime changes) - HIGHEST
2. Environment variables (.env file) - MEDIUM  
3. Default values (from JSON config) - LOWEST
"""

import logging
import json
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

class DynamicSettingsManager:
    """
    Enhanced runtime changeable setting management system
    
    Features:
    - JSON-based configuration
    - Hot reload (restart gerektirmez)
    - Database persistence
    - Priority system (DB > ENV > Default)
    - Thread-safe operations
    - Validation and type checking
    - Change notifications
    """
    
    def __init__(self, config_manager, database_manager):
        self.config = config_manager
        self.db = database_manager
        self._lock = threading.RLock()
        self._cached_settings = {}
        self._change_callbacks = {}
        
        # Load settings configuration from JSON
        self.settings_config = self._load_settings_config()
        
        # Initialize default settings in database if they don't exist
        self._initialize_default_settings()
        
        logger.info("Enhanced DynamicSettingsManager initialized with JSON configuration")
    
    def _load_settings_config(self) -> Dict[str, Any]:
        """Load settings configuration from JSON file"""
        try:
            config_path = Path(__file__).parent / "settings_config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                logger.info(f"Loaded settings configuration: {len(config_data)} categories")
                return config_data
        except Exception as e:
            logger.error(f"Failed to load settings config: {str(e)}")
            return {}
    
    def _initialize_default_settings(self):
        """Initialize default settings in database if they don't exist"""
        try:
            initialized_count = 0
            for category, cat_config in self.settings_config.items():
                settings = cat_config.get('settings', {})
                for key, setting_config in settings.items():
                    db_key = f"{category}.{key}"
                    
                    # Check if setting exists in database
                    existing_value = self.db.get_setting(db_key)
                    
                    if existing_value is None:
                        # Set default value
                        default_value = setting_config.get('default')
                        if default_value is not None:
                            description = setting_config.get('description', '')
                            success = self.db.set_setting(db_key, default_value, description)
                            if success:
                                initialized_count += 1
                                logger.debug(f"Initialized default setting: {db_key} = {default_value}")
            
            logger.info(f"Initialized {initialized_count} default settings in database")
                            
        except Exception as e:
            logger.error(f"Error initializing default settings: {str(e)}")
    
    def get_user_configurable_settings(self) -> Dict[str, Any]:
        """Get all user-configurable settings from JSON config"""
        return self.settings_config
    
    def get_setting_config(self, category: str, key: str) -> Optional[Dict[str, Any]]:
        """Get setting configuration from JSON"""
        try:
            return self.settings_config.get(category, {}).get('settings', {}).get(key)
        except Exception:
            return None
    
    def validate_setting_value(self, category: str, key: str, value: Any) -> bool:
        """Validate setting value against JSON configuration"""
        try:
            setting_config = self.get_setting_config(category, key)
            if not setting_config:
                logger.warning(f"No configuration found for {category}.{key}")
                return False
            
            value_type = setting_config.get('type', 'string')
            
            # Type validation
            if value_type == 'number':
                try:
                    num_value = float(value)
                    
                    # Range validation
                    min_val = setting_config.get('min')
                    max_val = setting_config.get('max')
                    
                    if min_val is not None and num_value < min_val:
                        logger.warning(f"Value {num_value} below minimum {min_val} for {category}.{key}")
                        return False
                    if max_val is not None and num_value > max_val:
                        logger.warning(f"Value {num_value} above maximum {max_val} for {category}.{key}")
                        return False
                        
                except (ValueError, TypeError):
                    logger.warning(f"Invalid number format for {category}.{key}: {value}")
                    return False
                    
            elif value_type == 'integer':
                try:
                    int_value = int(value)
                    
                    # Range validation
                    min_val = setting_config.get('min')
                    max_val = setting_config.get('max')
                    
                    if min_val is not None and int_value < min_val:
                        logger.warning(f"Value {int_value} below minimum {min_val} for {category}.{key}")
                        return False
                    if max_val is not None and int_value > max_val:
                        logger.warning(f"Value {int_value} above maximum {max_val} for {category}.{key}")
                        return False
                        
                except (ValueError, TypeError):
                    logger.warning(f"Invalid integer format for {category}.{key}: {value}")
                    return False
                    
            elif value_type == 'boolean':
                if not isinstance(value, bool):
                    # Try to convert string to boolean
                    if isinstance(value, str):
                        if value.lower() in ['true', '1', 'yes', 'on']:
                            return True
                        elif value.lower() in ['false', '0', 'no', 'off']:
                            return True
                    logger.warning(f"Invalid boolean format for {category}.{key}: {value}")
                    return False
                    
            elif value_type == 'choice':
                choices = setting_config.get('choices', [])
                if value not in choices:
                    logger.warning(f"Value {value} not in valid choices {choices} for {category}.{key}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating setting {category}.{key}: {str(e)}")
            return False
    
    def get_setting(self, category: str, key: str, default_value: Any = None) -> Any:
        """
        Get setting value (priority order: DB > ENV > JSON Default > provided default)
        """
        with self._lock:
            try:
                cache_key = f"{category}.{key}"
                
                # Check cache first
                if cache_key in self._cached_settings:
                    return self._cached_settings[cache_key]
                
                # 1. Check from database (highest priority)
                db_key = f"{category}.{key}"
                db_value = self.db.get_setting(db_key)
                
                if db_value is not None:
                    converted_value = self._convert_value_type(db_value, category, key)
                    self._cached_settings[cache_key] = converted_value
                    logger.debug(f"Setting from DB: {db_key} = {converted_value}")
                    return converted_value
                
                # 2. Check environment variables
                env_var = f"{category.upper()}_{key.upper()}"
                env_value = os.getenv(env_var)
                if env_value is not None:
                    converted_value = self._convert_value_type(env_value, category, key)
                    self._cached_settings[cache_key] = converted_value
                    logger.debug(f"Setting from ENV: {env_var} = {converted_value}")
                    return converted_value
                
                # 3. Check JSON default value
                setting_config = self.get_setting_config(category, key)
                if setting_config and 'default' in setting_config:
                    json_default = setting_config['default']
                    self._cached_settings[cache_key] = json_default
                    logger.debug(f"Setting from JSON default: {cache_key} = {json_default}")
                    return json_default
                
                # 4. Use provided default
                if default_value is not None:
                    self._cached_settings[cache_key] = default_value
                    logger.debug(f"Setting from provided default: {cache_key} = {default_value}")
                    return default_value
                
                logger.warning(f"No value found for setting {category}.{key}")
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
                # Validate setting
                if not self.validate_setting_value(category, key, value):
                    logger.error(f"Invalid setting value: {category}.{key} = {value}")
                    return False
                
                # Convert value to proper type
                converted_value = self._convert_value_type(value, category, key)
                
                # Save to database
                db_key = f"{category}.{key}"
                setting_config = self.get_setting_config(category, key)
                description = setting_config.get('description', '') if setting_config else ''
                
                success = self.db.set_setting(
                    key=db_key,
                    value=converted_value,
                    description=description
                )
                
                if success:
                    # Clear cache
                    cache_key = f"{category}.{key}"
                    if cache_key in self._cached_settings:
                        del self._cached_settings[cache_key]
                    
                    # Call change callbacks
                    self._notify_setting_changed(category, key, converted_value, user_id)
                    
                    logger.info(f"Setting updated: {category}.{key} = {converted_value} (user: {user_id})")
                    
                    # Audit log
                    self.db.log_event(
                        level="INFO",
                        module="dynamic_settings",
                        message=f"Setting changed: {category}.{key} = {converted_value}",
                        details={"category": category, "key": key, "old_value": self.get_setting(category, key), "new_value": converted_value},
                        telegram_id=user_id
                    )
                    
                    return True
                else:
                    logger.error(f"Failed to save setting to database: {category}.{key}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error setting {category}.{key}: {str(e)}")
                return False
    
    def _convert_value_type(self, value: Any, category: str, key: str) -> Any:
        """Convert value to proper type based on JSON configuration"""
        try:
            setting_config = self.get_setting_config(category, key)
            if not setting_config:
                return value
            
            value_type = setting_config.get('type', 'string')
            
            if value_type == 'number':
                return float(value)
            elif value_type == 'integer':
                return int(value)
            elif value_type == 'boolean':
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    return value.lower() in ['true', '1', 'yes', 'on']
                else:
                    return bool(value)
            else:
                return str(value)
                
        except Exception as e:
            logger.error(f"Error converting value type for {category}.{key}: {str(e)}")
            return value
    
    def _notify_setting_changed(self, category: str, key: str, value: Any, user_id: int = None):
        """Notify registered callbacks about setting changes"""
        try:
            callback_key = f"{category}.{key}"
            if callback_key in self._change_callbacks:
                for callback in self._change_callbacks[callback_key]:
                    try:
                        callback(category, key, value, user_id)
                    except Exception as e:
                        logger.error(f"Error in setting change callback: {str(e)}")
        except Exception as e:
            logger.error(f"Error notifying setting change: {str(e)}")
    
    def register_change_callback(self, category: str, key: str, callback):
        """Register callback for setting changes"""
        callback_key = f"{category}.{key}"
        if callback_key not in self._change_callbacks:
            self._change_callbacks[callback_key] = []
        self._change_callbacks[callback_key].append(callback)
    
    def get_settings_requiring_restart(self) -> List[str]:
        """Get list of settings that require restart"""
        try:
            restart_settings = []
            for category, cat_config in self.settings_config.items():
                settings = cat_config.get('settings', {})
                for key, setting_config in settings.items():
                    if setting_config.get('restart_required', False):
                        restart_settings.append(f"{category}.{key}")
            return restart_settings
        except Exception as e:
            logger.error(f"Error getting restart settings: {str(e)}")
            return []
    
    def apply_runtime_settings(self, config_manager):
        """Apply runtime settings to config manager"""
        try:
            updated_count = 0
            
            # Trading settings
            trading_amount = self.get_setting('trading', 'trade_amount')
            if trading_amount is not None:
                old_value = getattr(config_manager.trading, 'trade_amount', None)
                config_manager.trading.trade_amount = float(trading_amount)
                logger.info(f"Updated trade_amount: {old_value} -> {trading_amount}")
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
                if hasattr(config_manager, 'monitoring'):
                    config_manager.monitoring.notify_signals = bool(notify_signals)
                    updated_count += 1
            
            logger.info(f"Applied {updated_count} runtime settings to config manager")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"Error applying runtime settings: {str(e)}")
            return False
    
    def export_settings(self) -> Dict[str, Any]:
        """Export all current settings"""
        try:
            exported = {}
            for category, cat_config in self.settings_config.items():
                exported[category] = {}
                settings = cat_config.get('settings', {})
                for key in settings.keys():
                    value = self.get_setting(category, key)
                    if value is not None:
                        exported[category][key] = value
            return exported
        except Exception as e:
            logger.error(f"Error exporting settings: {str(e)}")
            return {}
    
    def import_settings(self, settings_data: Dict[str, Any], user_id: int = None) -> int:
        """Import settings from data"""
        try:
            imported_count = 0
            for category, category_settings in settings_data.items():
                if isinstance(category_settings, dict):
                    for key, value in category_settings.items():
                        success = self.set_setting(category, key, value, user_id)
                        if success:
                            imported_count += 1
            
            logger.info(f"Imported {imported_count} settings")
            return imported_count
        except Exception as e:
            logger.error(f"Error importing settings: {str(e)}")
            return 0

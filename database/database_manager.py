#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    SQLite database manager for Telegram Trading Bot
    Thread-safe operations and connection pooling
    """
    
    def __init__(self, db_path: str = "data/trading_bot.db"):
        self.db_path = db_path
        self.schema_path = "database/schema.sql"
        self._local = threading.local()
        
        # Create database directory
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self.initialize_database()
        
        logger.info(f"Database manager initialized: {self.db_path}")
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Thread-safe database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode = WAL")
        return self._local.connection
    
    @contextmanager
    def get_connection(self):
        """Context manager için connection"""
        conn = self.connection
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {str(e)}")
            raise
        finally:
            conn.commit()
    
    def initialize_database(self):
        """Veritabanını schema ile başlat"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            with self.get_connection() as conn:
                conn.executescript(schema_sql)
                logger.info("Database schema initialized successfully")
                
        except FileNotFoundError:
            logger.error(f"Schema file not found: {self.schema_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """SELECT sorguları için"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {query[:100]}... Error: {str(e)}")
            raise
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """INSERT, UPDATE, DELETE sorguları için"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Update execution failed: {query[:100]}... Error: {str(e)}")
            raise
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """INSERT sorguları için, son eklenen ID'yi döndürür"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Insert execution failed: {query[:100]}... Error: {str(e)}")
            raise
    
    # ============ WATCHED COINS METHODS ============
    
    def add_watched_coin(self, symbol: str, formatted_symbol: str, custom_settings: Dict = None) -> bool:
        """Takip listesine coin ekle"""
        try:
            settings_json = json.dumps(custom_settings) if custom_settings else None
            
            query = """
                INSERT OR REPLACE INTO watched_coins 
                (symbol, formatted_symbol, custom_settings, added_date)
                VALUES (?, ?, ?, ?)
            """
            
            self.execute_insert(query, (symbol, formatted_symbol, settings_json, datetime.now(timezone.utc)))
            logger.info(f"Added coin to watchlist: {symbol} ({formatted_symbol})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add watched coin {symbol}: {str(e)}")
            return False
    
    def remove_watched_coin(self, symbol: str) -> bool:
        """Takip listesinden coin çıkar"""
        try:
            query = "UPDATE watched_coins SET is_active = FALSE WHERE symbol = ?"
            rows_affected = self.execute_update(query, (symbol,))
            
            if rows_affected > 0:
                logger.info(f"Removed coin from watchlist: {symbol}")
                return True
            else:
                logger.warning(f"Coin not found in watchlist: {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove watched coin {symbol}: {str(e)}")
            return False
    
    def get_watched_coins(self, active_only: bool = True) -> List[Dict]:
        """Takip edilen coinleri getir"""
        try:
            query = """
                SELECT symbol, formatted_symbol, custom_settings, added_date
                FROM watched_coins 
                WHERE is_active = ? OR ? = FALSE
                ORDER BY added_date DESC
            """
            
            rows = self.execute_query(query, (True, active_only))
            
            coins = []
            for row in rows:
                coin_data = {
                    'symbol': row['symbol'],
                    'formatted_symbol': row['formatted_symbol'],
                    'added_date': row['added_date'],
                    'custom_settings': json.loads(row['custom_settings']) if row['custom_settings'] else {}
                }
                coins.append(coin_data)
            
            return coins
            
        except Exception as e:
            logger.error(f"Failed to get watched coins: {str(e)}")
            return []
    
    def is_coin_watched(self, symbol: str) -> bool:
        """Coin takip ediliyor mu kontrol et"""
        try:
            query = "SELECT COUNT(*) as count FROM watched_coins WHERE symbol = ? AND is_active = TRUE"
            result = self.execute_query(query, (symbol,))
            return result[0]['count'] > 0
        except Exception as e:
            logger.error(f"Failed to check if coin is watched {symbol}: {str(e)}")
            return False
    
    # ============ ACTIVE POSITIONS METHODS ============
    
    def add_position(self, symbol: str, formatted_symbol: str, side: str, entry_price: float, 
                    quantity: float, order_id: str, stop_loss: float = None, 
                    take_profit: float = None) -> int:
        """Yeni pozisyon ekle"""
        try:
            query = """
                INSERT INTO active_positions 
                (symbol, formatted_symbol, side, entry_price, quantity, order_id, stop_loss, take_profit, highest_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            highest_price = entry_price if side == 'BUY' else None
            
            position_id = self.execute_insert(query, (
                symbol, formatted_symbol, side, entry_price, quantity, 
                order_id, stop_loss, take_profit, highest_price
            ))
            
            logger.info(f"Added position: {symbol} {side} @ {entry_price} (ID: {position_id})")
            return position_id
            
        except Exception as e:
            logger.error(f"Failed to add position: {str(e)}")
            return 0
    
    def update_position(self, position_id: int, **kwargs) -> bool:
        """Pozisyon güncelle"""
        try:
            # Güncellenebilir alanlar
            allowed_fields = [
                'stop_loss', 'take_profit', 'highest_price', 'status', 
                'tp_order_id', 'sl_order_id', 'notes'
            ]
            
            updates = []
            params = []
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    updates.append(f"{field} = ?")
                    params.append(value)
            
            if not updates:
                logger.warning("No valid fields to update")
                return False
            
            query = f"UPDATE active_positions SET {', '.join(updates)} WHERE id = ?"
            params.append(position_id)
            
            rows_affected = self.execute_update(query, tuple(params))
            
            if rows_affected > 0:
                logger.info(f"Updated position {position_id}: {kwargs}")
                return True
            else:
                logger.warning(f"Position not found: {position_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update position {position_id}: {str(e)}")
            return False
    
    def get_active_positions(self, symbol: str = None) -> List[Dict]:
        """Aktif pozisyonları getir"""
        try:
            if symbol:
                query = """
                    SELECT * FROM active_positions 
                    WHERE status = 'ACTIVE' AND (symbol = ? OR formatted_symbol = ?)
                    ORDER BY created_at DESC
                """
                rows = self.execute_query(query, (symbol, symbol))
            else:
                query = """
                    SELECT * FROM active_positions 
                    WHERE status = 'ACTIVE'
                    ORDER BY created_at DESC
                """
                rows = self.execute_query(query)
            
            positions = []
            for row in rows:
                position = dict(row)
                positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get active positions: {str(e)}")
            return []
    
    def close_position(self, position_id: int, close_price: float = None, notes: str = None) -> bool:
        """Pozisyonu kapat"""
        try:
            updates = {'status': 'CLOSED'}
            if notes:
                updates['notes'] = notes
            
            success = self.update_position(position_id, **updates)
            
            if success:
                logger.info(f"Closed position {position_id} at {close_price}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {str(e)}")
            return False
    
    # ============ TRADE HISTORY METHODS ============
    
    def add_trade(self, symbol: str, formatted_symbol: str, action: str, price: float, 
                 quantity: float, order_id: str = None, trade_id: str = None, 
                 fees: float = 0, execution_type: str = 'MARKET', 
                 position_id: int = None, notes: str = None) -> int:
        """İşlem geçmişine kayıt ekle"""
        try:
            query = """
                INSERT INTO trade_history 
                (symbol, formatted_symbol, action, price, quantity, order_id, trade_id, 
                 fees, execution_type, position_id, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            trade_id_result = self.execute_insert(query, (
                symbol, formatted_symbol, action, price, quantity, order_id, trade_id,
                fees, execution_type, position_id, notes
            ))
            
            logger.info(f"Added trade: {symbol} {action} {quantity} @ {price}")
            return trade_id_result
            
        except Exception as e:
            logger.error(f"Failed to add trade: {str(e)}")
            return 0
    
    def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """İşlem geçmişini getir"""
        try:
            if symbol:
                query = """
                    SELECT * FROM trade_history 
                    WHERE symbol = ? OR formatted_symbol = ?
                    ORDER BY timestamp DESC LIMIT ?
                """
                rows = self.execute_query(query, (symbol, symbol, limit))
            else:
                query = """
                    SELECT * FROM trade_history 
                    ORDER BY timestamp DESC LIMIT ?
                """
                rows = self.execute_query(query, (limit,))
            
            trades = []
            for row in rows:
                trade = dict(row)
                trades.append(trade)
            
            return trades
            
        except Exception as e:
            logger.error(f"Failed to get trade history: {str(e)}")
            return []
    
    # ============ SIGNALS METHODS ============
    
    def add_signal(self, symbol: str, formatted_symbol: str, signal_type: str, price: float,
                  confidence: float = 0.5, rsi_value: float = None, atr_value: float = None,
                  ma_signal: str = None, ema_signal: str = None, 
                  indicators: Dict = None, notes: str = None) -> int:
        """Sinyal ekle"""
        try:
            indicators_json = json.dumps(indicators) if indicators else None
            
            query = """
                INSERT INTO signals 
                (symbol, formatted_symbol, signal_type, price, confidence, rsi_value, 
                 atr_value, ma_signal, ema_signal, indicators, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            signal_id = self.execute_insert(query, (
                symbol, formatted_symbol, signal_type, price, confidence, rsi_value,
                atr_value, ma_signal, ema_signal, indicators_json, notes
            ))
            
            logger.info(f"Added signal: {symbol} {signal_type} @ {price} (confidence: {confidence})")
            return signal_id
            
        except Exception as e:
            logger.error(f"Failed to add signal: {str(e)}")
            return 0
    
    def get_recent_signals(self, symbol: str = None, limit: int = 50, 
                          signal_type: str = None) -> List[Dict]:
        """Son sinyalleri getir"""
        try:
            conditions = []
            params = []
            
            if symbol:
                conditions.append("(symbol = ? OR formatted_symbol = ?)")
                params.extend([symbol, symbol])
            
            if signal_type:
                conditions.append("signal_type = ?")
                params.append(signal_type)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            query = f"""
                SELECT * FROM signals 
                {where_clause}
                ORDER BY timestamp DESC LIMIT ?
            """
            params.append(limit)
            
            rows = self.execute_query(query, tuple(params))
            
            signals = []
            for row in rows:
                signal = dict(row)
                if signal['indicators']:
                    signal['indicators'] = json.loads(signal['indicators'])
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Failed to get recent signals: {str(e)}")
            return []
    
    def mark_signal_executed(self, signal_id: int, execution_price: float) -> bool:
        """Sinyali executed olarak işaretle"""
        try:
            query = """
                UPDATE signals 
                SET executed = TRUE, execution_timestamp = ?, execution_price = ?
                WHERE id = ?
            """
            
            rows_affected = self.execute_update(query, (datetime.now(timezone.utc), execution_price, signal_id))
            
            if rows_affected > 0:
                logger.info(f"Marked signal {signal_id} as executed at {execution_price}")
                return True
            else:
                logger.warning(f"Signal not found: {signal_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to mark signal executed {signal_id}: {str(e)}")
            return False
    
    # ============ BOT SETTINGS METHODS ============
    
    def get_setting(self, key: str, default_value: Any = None) -> Any:
        """Bot ayarı getir"""
        try:
            query = "SELECT value, data_type FROM bot_settings WHERE key = ?"
            result = self.execute_query(query, (key,))
            
            if result:
                value = result[0]['value']
                data_type = result[0]['data_type']
                
                # Tip dönüşümü
                if data_type == 'number':
                    return float(value)
                elif data_type == 'boolean':
                    return value.lower() in ('true', '1', 'yes')
                elif data_type == 'json':
                    return json.loads(value)
                else:
                    return value
            else:
                return default_value
                
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {str(e)}")
            return default_value
    
    def set_setting(self, key: str, value: Any, description: str = None) -> bool:
        """Bot ayarı kaydet"""
        try:
            # Tip belirleme
            if isinstance(value, bool):
                data_type = 'boolean'
                value_str = str(value).lower()
            elif isinstance(value, (int, float)):
                data_type = 'number'
                value_str = str(value)
            elif isinstance(value, (dict, list)):
                data_type = 'json'
                value_str = json.dumps(value)
            else:
                data_type = 'string'
                value_str = str(value)
            
            query = """
                INSERT OR REPLACE INTO bot_settings 
                (key, value, data_type, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """
            
            self.execute_update(query, (key, value_str, data_type, description, datetime.now(timezone.utc)))
            logger.info(f"Updated setting {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {str(e)}")
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Tüm ayarları getir"""
        try:
            query = "SELECT key, value, data_type FROM bot_settings ORDER BY key"
            rows = self.execute_query(query)
            
            settings = {}
            for row in rows:
                key = row['key']
                value = row['value']
                data_type = row['data_type']
                
                # Tip dönüşümü
                if data_type == 'number':
                    settings[key] = float(value)
                elif data_type == 'boolean':
                    settings[key] = value.lower() in ('true', '1', 'yes')
                elif data_type == 'json':
                    settings[key] = json.loads(value)
                else:
                    settings[key] = value
            
            return settings
            
        except Exception as e:
            logger.error(f"Failed to get all settings: {str(e)}")
            return {}
    
    # ============ USER MANAGEMENT METHODS ============
    
    def add_user(self, telegram_id: int, username: str = None, first_name: str = None, 
                last_name: str = None, is_authorized: bool = False) -> bool:
        """Kullanıcı ekle"""
        try:
            query = """
                INSERT OR REPLACE INTO bot_users 
                (telegram_id, username, first_name, last_name, is_authorized)
                VALUES (?, ?, ?, ?, ?)
            """
            
            self.execute_update(query, (telegram_id, username, first_name, last_name, is_authorized))
            logger.info(f"Added/updated user: {telegram_id} ({username})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add user {telegram_id}: {str(e)}")
            return False
    
    def is_user_authorized(self, telegram_id: int) -> bool:
        """Kullanıcı yetkili mi kontrol et"""
        try:
            query = "SELECT is_authorized FROM bot_users WHERE telegram_id = ?"
            result = self.execute_query(query, (telegram_id,))
            
            if result:
                return bool(result[0]['is_authorized'])
            else:
                # Kullanıcı kayıtlı değil, otomatik ekle (yetkisiz olarak)
                self.add_user(telegram_id, is_authorized=False)
                return False
                
        except Exception as e:
            logger.error(f"Failed to check user authorization {telegram_id}: {str(e)}")
            return False
    
    def authorize_user(self, telegram_id: int) -> bool:
        """Kullanıcıyı yetkilendir"""
        try:
            query = "UPDATE bot_users SET is_authorized = TRUE WHERE telegram_id = ?"
            rows_affected = self.execute_update(query, (telegram_id,))
            
            if rows_affected > 0:
                logger.info(f"Authorized user: {telegram_id}")
                return True
            else:
                logger.warning(f"User not found for authorization: {telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to authorize user {telegram_id}: {str(e)}")
            return False
    
    # ============ SYSTEM LOGS METHODS ============
    
    def log_event(self, level: str, module: str, message: str, details: Dict = None, 
                 telegram_id: int = None) -> bool:
        """Sistem log'u ekle"""
        try:
            details_json = json.dumps(details) if details else None
            
            query = """
                INSERT INTO system_logs (level, module, message, details, telegram_id)
                VALUES (?, ?, ?, ?, ?)
            """
            
            self.execute_insert(query, (level, module, message, details_json, telegram_id))
            return True
            
        except Exception as e:
            # Log hatası için normal logger kullan
            logger.error(f"Failed to log event: {str(e)}")
            return False
    
    def get_recent_logs(self, level: str = None, limit: int = 100) -> List[Dict]:
        """Son log'ları getir"""
        try:
            if level:
                query = """
                    SELECT * FROM system_logs 
                    WHERE level = ?
                    ORDER BY timestamp DESC LIMIT ?
                """
                rows = self.execute_query(query, (level, limit))
            else:
                query = """
                    SELECT * FROM system_logs 
                    ORDER BY timestamp DESC LIMIT ?
                """
                rows = self.execute_query(query, (limit,))
            
            logs = []
            for row in rows:
                log_entry = dict(row)
                if log_entry['details']:
                    log_entry['details'] = json.loads(log_entry['details'])
                logs.append(log_entry)
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get recent logs: {str(e)}")
            return []
    
    # ============ UTILITY METHODS ============
    
    def backup_database(self, backup_path: str = None) -> bool:
        """Veritabanını yedekle"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backups/trading_bot_backup_{timestamp}.db"
            
            # Backup dizini oluştur
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Database backup
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            logger.info(f"Database backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup database: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Veritabanı istatistikleri"""
        try:
            stats = {}
            
            # Tablo satır sayıları
            tables = [
                'watched_coins', 'active_positions', 'trade_history', 
                'signals', 'bot_users', 'bot_settings', 'system_logs'
            ]
            
            for table in tables:
                query = f"SELECT COUNT(*) as count FROM {table}"
                result = self.execute_query(query)
                stats[f"{table}_count"] = result[0]['count']
            
            # Aktif pozisyon sayısı
            query = "SELECT COUNT(*) as count FROM active_positions WHERE status = 'ACTIVE'"
            result = self.execute_query(query)
            stats['active_positions_count'] = result[0]['count']
            
            # Son 24 saat sinyal sayısı
            query = """
                SELECT COUNT(*) as count FROM signals 
                WHERE timestamp > datetime('now', '-24 hours')
            """
            result = self.execute_query(query)
            stats['signals_24h'] = result[0]['count']
            
            # Son 24 saat işlem sayısı
            query = """
                SELECT COUNT(*) as count FROM trade_history 
                WHERE timestamp > datetime('now', '-24 hours')
            """
            result = self.execute_query(query)
            stats['trades_24h'] = result[0]['count']
            
            # Veritabanı boyutu
            stats['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Eski verileri temizle"""
        try:
            cutoff_date = datetime.now() - datetime.timedelta(days=days_to_keep)
            
            # Eski log'ları sil
            query = "DELETE FROM system_logs WHERE timestamp < ?"
            logs_deleted = self.execute_update(query, (cutoff_date,))
            
            # Eski sinyalleri sil (execute edilmemiş olanları)
            query = "DELETE FROM signals WHERE timestamp < ? AND executed = FALSE"
            signals_deleted = self.execute_update(query, (cutoff_date,))
            
            logger.info(f"Cleaned up old data: {logs_deleted} logs, {signals_deleted} signals")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")
            return False
    
    def close(self):
        """Veritabanı bağlantısını kapat"""
        try:
            if hasattr(self._local, 'connection'):
                self._local.connection.close()
                delattr(self._local, 'connection')
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")

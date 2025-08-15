#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import json

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.constants import ParseMode

# Our imports
from database.database_manager import DatabaseManager
from config.config import ConfigManager
from config.dynamic_settings import DynamicSettingsManager
from exchange.crypto_exchange_api import CryptoExchangeAPI
from signals.signal_engine import SignalEngine
from telegram_bot.settings_handlers import SettingsHandlers
from utils.logging_setup import create_logger

logger = logging.getLogger(__name__)

# Conversation states
(WAITING_FOR_COIN_SYMBOL, WAITING_FOR_CONFIRMATION, 
 WAITING_FOR_TRADE_AMOUNT, WAITING_FOR_SETTING_VALUE) = range(4)

class TelegramTradingBot:
    """Ana Telegram Trading Bot sınıfı"""
    
    def __init__(self, config_manager: ConfigManager, database_manager: DatabaseManager):
        self.config = config_manager
        self.db = database_manager
        self.telegram_config = config_manager.telegram
        
        # Initialize components
        self.exchange_api = None
        self.signal_engine = None
        self.application = None
        self.dynamic_settings = None
        self.settings_handlers = None
        
        # Bot state
        self.is_running = False
        self.last_health_check = None
        
        # User sessions (for conversation states)
        self.user_sessions = {}
        
        # Initialize logger with telegram notifier
        self.logger = create_logger("telegram_bot")
        
        logger.info("Telegram Trading Bot initialized")
    
    async def initialize(self):
        """Bot bileşenlerini başlat"""
        try:
            # Initialize dynamic settings manager
            self.dynamic_settings = DynamicSettingsManager(self.config, self.db)
            logger.info("✅ Dynamic settings manager initialized")
            
            # Apply runtime settings to config
            self.dynamic_settings.apply_runtime_settings(self.config)
            logger.info("✅ Runtime settings applied")
            
            # Initialize exchange API
            self.exchange_api = CryptoExchangeAPI(self.config)
            logger.info("✅ Exchange API initialized")
            
            # Initialize signal engine
            self.signal_engine = SignalEngine(self.config, self.db)
            logger.info("✅ Signal engine initialized")
            
            # Initialize settings handlers
            self.settings_handlers = SettingsHandlers(self.dynamic_settings, self)
            logger.info("✅ Settings handlers initialized")
            
            # Create Telegram application
            self.application = Application.builder().token(self.telegram_config.bot_token).build()
            
            # Setup handlers
            await self._setup_handlers()
            
            # Setup bot commands menu
            await self._setup_bot_commands()
            
            logger.info("✅ Telegram bot initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize bot: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def _setup_handlers(self):
        """Komut ve callback handler'larını ayarla"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("status", self._cmd_status))
        self.application.add_handler(CommandHandler("portfolio", self._cmd_portfolio))
        self.application.add_handler(CommandHandler("balance", self._cmd_balance))
        self.application.add_handler(CommandHandler("watchlist", self._cmd_watchlist))
        self.application.add_handler(CommandHandler("signals", self._cmd_signals))
        self.application.add_handler(CommandHandler("history", self._cmd_history))
        self.application.add_handler(CommandHandler("settings", self._cmd_settings))
        self.application.add_handler(CommandHandler("add_coin", self._cmd_add_coin))
        self.application.add_handler(CommandHandler("remove_coin", self._cmd_remove_coin))
        self.application.add_handler(CommandHandler("analyze", self._cmd_analyze))
        self.application.add_handler(CommandHandler("health", self._cmd_health))
        
        # Admin commands
        self.application.add_handler(CommandHandler("admin", self._cmd_admin))
        self.application.add_handler(CommandHandler("logs", self._cmd_logs))
        self.application.add_handler(CommandHandler("backup", self._cmd_backup))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Message handler for conversations
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Settings message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.settings_handlers.handle_setting_value_input))
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("✅ All handlers setup complete")
    
    async def _setup_bot_commands(self):
        """Bot komutları menüsünü ayarla"""
        commands = [
            BotCommand("start", "Bot'u başlat ve hoş geldin mesajı"),
            BotCommand("help", "Yardım ve komut listesi"),
            BotCommand("status", "Bot durumu ve sistem bilgileri"),
            BotCommand("portfolio", "Aktif pozisyonlar ve portföy"),
            BotCommand("balance", "Exchange bakiye bilgileri"),
            BotCommand("watchlist", "Takip edilen coinler"),
            BotCommand("signals", "Son trading sinyalleri"),
            BotCommand("history", "İşlem geçmişi"),
            BotCommand("settings", "Bot ayarları"),
            BotCommand("add_coin", "Coin takip listesine ekle"),
            BotCommand("remove_coin", "Coin takip listesinden çıkar"),
            BotCommand("analyze", "Belirli bir coin'i analiz et"),
            BotCommand("health", "Sistem sağlık kontrolü"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands menu setup complete")
    
    def _check_authorization(self, user_id: int) -> bool:
        """Kullanıcı yetki kontrolü"""
        try:
            # Database'den kontrol et
            is_authorized = self.db.is_user_authorized(user_id)
            
            # Config'den de kontrol et
            config_authorized = (
                user_id in self.telegram_config.authorized_users or
                user_id in self.telegram_config.admin_users
            )
            
            return is_authorized or config_authorized
            
        except Exception as e:
            logger.error(f"Error checking authorization: {str(e)}")
            return False
    
    def _is_admin(self, user_id: int) -> bool:
        """Admin kontrolü"""
        return user_id in self.telegram_config.admin_users
    
    async def _send_unauthorized_message(self, update: Update):
        """Unauthorized access message"""
        await update.message.reply_text(
            "❌ Unauthorized Access!\n\n"
            "You don't have permission to use this bot.\n"
            "Please contact the administrator for access.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ============ COMMAND HANDLERS ============
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start komutu"""
        user = update.effective_user
        user_id = user.id
        
        # Kullanıcıyı database'e ekle
        self.db.add_user(
            telegram_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_authorized=self._check_authorization(user_id)
        )
        
        if not self._check_authorization(user_id):
            await self._send_unauthorized_message(update)
            return
        
        welcome_text = f"""
🤖 **Welcome to Telegram Trading Bot!**

Hello {user.first_name}! 👋

This bot allows you to manage your cryptocurrency trading operations through Telegram.

**🚀 Key Features:**
• 📊 Technical analysis and signal generation
• 💰 Automated buy/sell operations  
• 📈 Portfolio tracking and reporting
• 🔔 Real-time notifications
• ⚙️ Flexible settings management

**📋 Getting Started Commands:**
• `/help` - Show all commands
• `/status` - Check bot status
• `/portfolio` - View your portfolio
• `/watchlist` - Show tracked coins
• `/settings` - Configure bot settings

**⚠️ Important Warning:**
This bot trades with real money. All trades are at your own responsibility.

Use any command to get started! 🎯
        """
        
        # Inline keyboard with quick actions
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="status"),
                InlineKeyboardButton("💰 Portfolio", callback_data="portfolio")
            ],
            [
                InlineKeyboardButton("📈 Signals", callback_data="signals"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Log user activity
        self.db.log_event("INFO", "telegram_bot", f"User {user_id} started bot", 
                         {"user": user.to_dict()}, user_id)
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        help_text = """
📚 **Telegram Trading Bot - Command Guide**

**📊 Information Commands:**
• `/status` - Bot status and system information
• `/portfolio` - Active positions and P&L
• `/balance` - Exchange balance information
• `/watchlist` - Tracked coin list
• `/signals` - Recent trading signals
• `/history` - Trade history
• `/health` - System health check

**🔧 Management Commands:**
• `/add_coin [SYMBOL]` - Add coin to watchlist
• `/remove_coin [SYMBOL]` - Remove coin from list
• `/analyze [SYMBOL]` - Analyze specific coin
• `/settings` - View/edit bot settings

**⚙️ Settings:**
• Trade amount, risk parameters
• Notification preferences
• Auto trading enable/disable

**🔐 Admin Commands:**
• `/admin` - Admin panel
• `/logs` - System logs
• `/backup` - Database backup

**💡 Tips:**
• Commands can be used alone or with parameters
• Example: `/analyze BTC` or just `/analyze`
• Use buttons for interactive menus

**⚠️ Risk Warning:**
This bot trades with real money. Always be careful!
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            # System information
            db_stats = self.db.get_database_stats()
            config_summary = self.config.get_config_summary()
            
            # Exchange connection test
            try:
                balance = self.exchange_api.get_balance("USDT")
                exchange_status = f"✅ Connected (USDT: {balance:.2f})"
            except Exception as e:
                exchange_status = f"❌ Connection error: {str(e)[:50]}..."
            
            # Active positions
            active_positions = self.db.get_active_positions()
            
            # Recent signals
            recent_signals = self.db.get_recent_signals(limit=5)
            
            status_text = f"""
📊 **Bot Status Report**

**🤖 System Status:**
• Bot: ✅ Active
• Exchange: {exchange_status}
• Database: ✅ Connected ({db_stats.get('db_size_mb', 0)} MB)
• Signal Engine: ✅ Active

**📈 Trading Status:**
• Active Positions: {len(active_positions)}
• Tracked Coins: {db_stats.get('watched_coins_count', 0)}
• Last 24h Signals: {db_stats.get('signals_24h', 0)}
• Last 24h Trades: {db_stats.get('trades_24h', 0)}

**⚙️ Settings:**
• Trade Amount: {config_summary['trading']['trade_amount']} USDT
• Max Positions: {config_summary['trading']['max_positions']}
• Auto Trading: {'✅' if config_summary['trading']['auto_trading_enabled'] else '❌'}
• Paper Trading: {'✅' if config_summary['trading']['paper_trading_enabled'] else '❌'}

**🔔 Notifications:**
• Signals: {'✅' if config_summary['monitoring']['notifications_enabled'] else '❌'}
• Log Level: {config_summary['monitoring']['log_level']}

**⏰ Last Update:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Quick action buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="status"),
                    InlineKeyboardButton("💰 Portfolio", callback_data="portfolio")
                ],
                [
                    InlineKeyboardButton("📈 Signals", callback_data="signals"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                status_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in status command: {str(e)}")
            await update.message.reply_text(
                f"❌ Error getting status information:\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Portfolio komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            # Active positions
            active_positions = self.db.get_active_positions()
            
            if not active_positions:
                portfolio_text = """
💰 **Portföy Raporu**

📭 **Aktif pozisyon bulunmuyor.**

Pozisyon açmak için:
• `/watchlist` ile takip edilen coinleri görebilirsiniz
• `/signals` ile trading sinyallerini kontrol edebilirsiniz
• `/add_coin [SYMBOL]` ile yeni coin ekleyebilirsiniz
                """
            else:
                portfolio_text = "💰 **Portföy Raporu**\n\n"
                total_pnl = 0
                
                for pos in active_positions:
                    symbol = pos['symbol']
                    entry_price = pos['entry_price']
                    quantity = pos['quantity']
                    
                    # Current price
                    try:
                        current_price = self.exchange_api.get_current_price(pos['formatted_symbol'])
                        if current_price:
                            pnl = (current_price - entry_price) * quantity
                            pnl_pct = ((current_price - entry_price) / entry_price) * 100
                            total_pnl += pnl
                            
                            status_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                            
                            portfolio_text += f"""
{status_emoji} **{symbol}**
• Giriş: ${entry_price:.6f}
• Güncel: ${current_price:.6f}
• Miktar: {quantity:.6f}
• P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)
• TP: ${pos.get('take_profit', 0):.6f}
• SL: ${pos.get('stop_loss', 0):.6f}

                            """
                        else:
                            portfolio_text += f"""
⚪ **{symbol}**
• Giriş: ${entry_price:.6f}
• Miktar: {quantity:.6f}
• Fiyat alınamadı

                            """
                    except Exception as e:
                        logger.error(f"Error getting price for {symbol}: {str(e)}")
                
                total_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
                portfolio_text += f"\n{total_emoji} **Toplam P&L: ${total_pnl:.2f}**"
            
            # Portfolio actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Yenile", callback_data="portfolio"),
                    InlineKeyboardButton("💳 Bakiye", callback_data="balance")
                ],
                [
                    InlineKeyboardButton("📊 Sinyaller", callback_data="signals"),
                    InlineKeyboardButton("📜 Geçmiş", callback_data="history")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                portfolio_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in portfolio command: {str(e)}")
            await update.message.reply_text(
                f"❌ Portföy bilgisi alınırken hata oluştu:\n{str(e)}"
            )
    
    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Balance komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            # Get all balances
            balances = self.exchange_api.get_all_balances()
            
            if not balances:
                balance_text = """
💳 **Bakiye Raporu**

❌ **Bakiye bilgisi alınamadı**

Olası nedenler:
• Exchange API bağlantı sorunu
• API anahtarları hatalı
• Yetki problemi
                """
            else:
                balance_text = "💳 **Bakiye Raporu**\n\n"
                
                # Significant balances first
                significant_balances = [b for b in balances if b.available > 0.01]
                other_balances = [b for b in balances if b.available <= 0.01 and b.available > 0]
                
                if significant_balances:
                    balance_text += "**💰 Ana Bakiyeler:**\n"
                    for balance in significant_balances:
                        locked_info = f" (Kilitli: {balance.locked:.6f})" if balance.locked > 0 else ""
                        balance_text += f"• **{balance.currency}**: {balance.available:.6f}{locked_info}\n"
                
                if other_balances:
                    balance_text += f"\n**🪙 Diğer ({len(other_balances)} coin):**\n"
                    for balance in other_balances[:10]:  # Show only first 10
                        balance_text += f"• {balance.currency}: {balance.available:.6f}\n"
                    
                    if len(other_balances) > 10:
                        balance_text += f"• ... ve {len(other_balances) - 10} coin daha\n"
                
                # Trading status
                usdt_balance = next((b.available for b in balances if b.currency == "USDT"), 0)
                min_required = self.config.trading.min_balance_required
                
                if usdt_balance >= min_required:
                    balance_text += f"\n✅ **Trading için yeterli bakiye** (Min: {min_required} USDT)"
                else:
                    balance_text += f"\n⚠️ **Yetersiz USDT bakiyesi** (Min: {min_required} USDT)"
            
            # Balance actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Yenile", callback_data="balance"),
                    InlineKeyboardButton("💰 Portföy", callback_data="portfolio")
                ],
                [
                    InlineKeyboardButton("📊 Durum", callback_data="status")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                balance_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in balance command: {str(e)}")
            await update.message.reply_text(
                f"❌ Bakiye bilgisi alınırken hata oluştu:\n{str(e)}"
            )
    
    async def _cmd_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Watchlist komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            watched_coins = self.db.get_watched_coins()
            
            if not watched_coins:
                watchlist_text = """
📋 **Takip Listesi**

📭 **Hiç coin takip edilmiyor.**

Coin eklemek için:
• `/add_coin BTC` (komut ile)
• Aşağıdaki "Coin Ekle" butonunu kullanın
                """
            else:
                watchlist_text = f"📋 **Takip Listesi** ({len(watched_coins)} coin)\n\n"
                
                for coin in watched_coins:
                    symbol = coin['symbol']
                    formatted_symbol = coin['formatted_symbol']
                    added_date = coin['added_date']
                    
                    # Get current price
                    try:
                        current_price = self.exchange_api.get_current_price(formatted_symbol)
                        price_info = f"${current_price:.6f}" if current_price else "Fiyat alınamadı"
                    except:
                        price_info = "Fiyat alınamadı"
                    
                    # Check if we have active position
                    active_pos = self.db.get_active_positions(symbol)
                    position_info = "📈 Aktif pozisyon" if active_pos else ""
                    
                    watchlist_text += f"• **{symbol}** ({formatted_symbol})\n"
                    watchlist_text += f"  💰 {price_info} {position_info}\n"
                    watchlist_text += f"  📅 Eklendi: {added_date[:10]}\n\n"
            
            # Watchlist actions
            keyboard = [
                [
                    InlineKeyboardButton("➕ Coin Ekle", callback_data="add_coin"),
                    InlineKeyboardButton("➖ Coin Çıkar", callback_data="remove_coin")
                ],
                [
                    InlineKeyboardButton("🔄 Yenile", callback_data="watchlist"),
                    InlineKeyboardButton("📊 Analiz Et", callback_data="analyze")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                watchlist_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in watchlist command: {str(e)}")
            await update.message.reply_text(
                f"❌ Takip listesi alınırken hata oluştu:\n{str(e)}"
            )
    
    async def _cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Signals komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            recent_signals = self.db.get_recent_signals(limit=10)
            
            if not recent_signals:
                signals_text = """
📊 **Trading Sinyalleri**

📭 **Henüz sinyal üretilmemiş.**

Sinyal üretmek için:
• Takip listesine coin ekleyin (`/add_coin`)
• Sistem otomatik olarak analiz yapacak
• Manual analiz: `/analyze [SYMBOL]`
                """
            else:
                signals_text = f"📊 **Son Trading Sinyalleri** ({len(recent_signals)})\n\n"
                
                for signal in recent_signals[:5]:  # Show last 5
                    symbol = signal['symbol']
                    signal_type = signal['signal_type']
                    confidence = signal['confidence']
                    price = signal['price']
                    timestamp = signal['timestamp']
                    
                    # Signal emoji
                    if signal_type == "BUY":
                        emoji = "🟢"
                    elif signal_type == "SELL":
                        emoji = "🔴"
                    else:
                        emoji = "⚪"
                    
                    # Confidence bars
                    conf_bars = "█" * int(confidence * 5)
                    
                    signals_text += f"""
{emoji} **{symbol}** - {signal_type}
• Fiyat: ${price:.6f}
• Güven: {conf_bars} ({confidence:.0%})
• Zaman: {timestamp[:16]}

                    """
                
                if len(recent_signals) > 5:
                    signals_text += f"... ve {len(recent_signals) - 5} sinyal daha"
            
            # Signals actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Yenile", callback_data="signals"),
                    InlineKeyboardButton("📈 Tüm Sinyaller", callback_data="all_signals")
                ],
                [
                    InlineKeyboardButton("📊 Analiz Et", callback_data="analyze"),
                    InlineKeyboardButton("💰 Portföy", callback_data="portfolio")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                signals_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in signals command: {str(e)}")
            await update.message.reply_text(
                f"❌ Sinyal bilgisi alınırken hata oluştu:\n{str(e)}"
            )
    
    async def _cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """History komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            trade_history = self.db.get_trade_history(limit=10)
            
            if not trade_history:
                history_text = """
📜 **İşlem Geçmişi**

📭 **Henüz işlem geçmişi bulunmuyor.**

İşlem yaptıktan sonra burada görünecek.
                """
            else:
                history_text = f"📜 **Son İşlemler** ({len(trade_history)})\n\n"
                
                total_pnl = 0
                for trade in trade_history[:5]:  # Show last 5
                    symbol = trade['symbol']
                    action = trade['action']
                    price = trade['price']
                    quantity = trade['quantity']
                    pnl = trade.get('pnl', 0)
                    timestamp = trade['timestamp']
                    
                    action_emoji = "🟢" if action == "BUY" else "🔴"
                    pnl_emoji = "💚" if pnl > 0 else "❤️" if pnl < 0 else "💛"
                    
                    total_pnl += pnl
                    
                    history_text += f"""
{action_emoji} **{symbol}** - {action}
• Fiyat: ${price:.6f}
• Miktar: {quantity:.6f}
• P&L: {pnl_emoji} ${pnl:.2f}
• Tarih: {timestamp[:16]}

                    """
                
                if len(trade_history) > 5:
                    history_text += f"... ve {len(trade_history) - 5} işlem daha\n\n"
                
                pnl_emoji = "💚" if total_pnl > 0 else "❤️" if total_pnl < 0 else "💛"
                history_text += f"{pnl_emoji} **Toplam P&L: ${total_pnl:.2f}**"
            
            # History actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Yenile", callback_data="history"),
                    InlineKeyboardButton("📊 Detay", callback_data="detailed_history")
                ],
                [
                    InlineKeyboardButton("💰 Portföy", callback_data="portfolio"),
                    InlineKeyboardButton("📈 Sinyaller", callback_data="signals")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                history_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in history command: {str(e)}")
            await update.message.reply_text(
                f"❌ İşlem geçmişi alınırken hata oluştu:\n{str(e)}"
            )
    
    async def _cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Settings komutu - Yeni dinamik ayar sistemi"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            await self.settings_handlers.handle_settings_main(update)
            
        except Exception as e:
            logger.error(f"Error in settings command: {str(e)}")
            await update.message.reply_text(
                f"❌ Ayarlar alınırken hata oluştu:\n{str(e)}"
            )
    
    async def _cmd_add_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add coin komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        # Check if symbol provided in command
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
            await self._add_coin_to_watchlist(update, symbol)
        else:
            # Start conversation
            await update.message.reply_text(
                "➕ **Coin Ekle**\n\n"
                "Takip listesine eklemek istediğiniz coin sembolünü yazın:\n"
                "Örnek: `BTC`, `ETH`, `SUI`\n\n"
                "İptal etmek için `/cancel` yazın.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Set conversation state
            self.user_sessions[update.effective_user.id] = {
                'state': WAITING_FOR_COIN_SYMBOL,
                'action': 'add_coin'
            }
    
    async def _cmd_remove_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove coin komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        # Check if symbol provided in command
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
            await self._remove_coin_from_watchlist(update, symbol)
        else:
            # Show current watchlist with remove buttons
            watched_coins = self.db.get_watched_coins()
            
            if not watched_coins:
                await update.message.reply_text(
                    "📭 Takip listesinde coin bulunmuyor.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            remove_text = "➖ **Coin Çıkar**\n\nÇıkarmak istediğiniz coin'i seçin:"
            
            # Create keyboard with coins
            keyboard = []
            for coin in watched_coins:
                keyboard.append([
                    InlineKeyboardButton(
                        f"❌ {coin['symbol']}", 
                        callback_data=f"remove_coin_{coin['symbol']}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("🚫 İptal", callback_data="cancel")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                remove_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def _cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analyze komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        # Check if symbol provided
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
            await self._analyze_symbol(update, symbol)
        else:
            # Show watchlist for selection
            watched_coins = self.db.get_watched_coins()
            
            if not watched_coins:
                await update.message.reply_text(
                    "📭 Analiz edilecek coin bulunamadı.\n\n"
                    "Önce `/add_coin` ile coin ekleyin veya\n"
                    "`/analyze BTC` formatında kullanın.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            analyze_text = "📊 **Analiz Et**\n\nAnaliz etmek istediğiniz coin'i seçin:"
            
            # Create keyboard with coins
            keyboard = []
            for coin in watched_coins[:10]:  # Show max 10
                keyboard.append([
                    InlineKeyboardButton(
                        f"📊 {coin['symbol']}", 
                        callback_data=f"analyze_{coin['symbol']}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("🚫 İptal", callback_data="cancel")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                analyze_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def _cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Health check komutu"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            health_status = []
            overall_healthy = True
            
            # Database health
            try:
                self.db.get_database_stats()
                health_status.append("✅ Database: Sağlıklı")
            except Exception as e:
                health_status.append(f"❌ Database: {str(e)[:50]}")
                overall_healthy = False
            
            # Exchange API health
            try:
                balance = self.exchange_api.get_balance("USDT")
                health_status.append(f"✅ Exchange API: Sağlıklı (USDT: {balance:.2f})")
            except Exception as e:
                health_status.append(f"❌ Exchange API: {str(e)[:50]}")
                overall_healthy = False
            
            # Signal engine health
            try:
                # Test signal generation with a simple symbol
                test_signal = self.signal_engine.analyze_symbol("BTC_USDT")
                if test_signal:
                    health_status.append("✅ Signal Engine: Sağlıklı")
                else:
                    health_status.append("⚠️ Signal Engine: Test sinyali üretilemedi")
            except Exception as e:
                health_status.append(f"❌ Signal Engine: {str(e)[:50]}")
                overall_healthy = False
            
            # Memory and performance
            import psutil
            try:
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                
                if cpu_percent < 80 and memory_percent < 80:
                    health_status.append(f"✅ Sistem: CPU {cpu_percent:.1f}%, RAM {memory_percent:.1f}%")
                else:
                    health_status.append(f"⚠️ Sistem: CPU {cpu_percent:.1f}%, RAM {memory_percent:.1f}%")
            except:
                health_status.append("⚠️ Sistem: Metrik alınamadı")
            
            # Overall status
            status_emoji = "🟢" if overall_healthy else "🔴"
            overall_status = "Sağlıklı" if overall_healthy else "Problemli"
            
            health_text = f"""
🏥 **Sistem Sağlık Raporu**

{status_emoji} **Genel Durum: {overall_status}**

**📋 Detaylar:**
{chr(10).join(['• ' + status for status in health_status])}

**⏰ Kontrol Zamanı:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Health actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Tekrar Kontrol", callback_data="health"),
                    InlineKeyboardButton("📊 Durum", callback_data="status")
                ]
            ]
            
            if self._is_admin(update.effective_user.id):
                keyboard.append([
                    InlineKeyboardButton("📋 Detaylı Log", callback_data="detailed_logs")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                health_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in health command: {str(e)}")
            await update.message.reply_text(
                f"❌ Sağlık kontrolü sırasında hata oluştu:\n{str(e)}"
            )
    
    # ============ ADMIN COMMANDS ============
    
    async def _cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin komutu"""
        user_id = update.effective_user.id
        
        if not self._check_authorization(user_id):
            await self._send_unauthorized_message(update)
            return
        
        if not self._is_admin(user_id):
            await update.message.reply_text(
                "❌ Bu komut sadece admin kullanıcılar için mevcut.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        admin_text = """
👑 **Admin Paneli**

**📊 Sistem Bilgileri:**
• Bot çalışma zamanı
• Memory kullanımı
• Database boyutu
• API call sayısı

**🔧 Yönetim İşlemleri:**
• Kullanıcı yetkilendirme
• Sistem ayarları
• Database bakımı
• Log yönetimi

**⚠️ Dikkatli kullanın!**
        """
        
        # Admin actions
        keyboard = [
            [
                InlineKeyboardButton("👥 Kullanıcılar", callback_data="admin_users"),
                InlineKeyboardButton("📊 İstatistik", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton("⚙️ Ayarlar", callback_data="admin_settings"),
                InlineKeyboardButton("📋 Loglar", callback_data="admin_logs")
            ],
            [
                InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
                InlineKeyboardButton("🔄 Restart", callback_data="admin_restart")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            admin_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def _cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Logs komutu (admin only)"""
        user_id = update.effective_user.id
        
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ Bu komut sadece admin kullanıcılar için mevcut.")
            return
        
        try:
            recent_logs = self.db.get_recent_logs(limit=20)
            
            if not recent_logs:
                await update.message.reply_text("📋 Log bulunamadı.")
                return
            
            logs_text = "📋 **Son Sistem Logları**\n\n"
            
            for log in recent_logs[:10]:
                level_emoji = {
                    'INFO': 'ℹ️',
                    'WARNING': '⚠️', 
                    'ERROR': '❌',
                    'CRITICAL': '🚨'
                }.get(log['level'], '📝')
                
                logs_text += f"{level_emoji} `{log['timestamp'][:16]}`\n"
                logs_text += f"**{log['module']}**: {log['message'][:100]}\n\n"
            
            await update.message.reply_text(logs_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Log okuma hatası: {str(e)}")
    
    async def _cmd_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Backup komutu (admin only)"""
        user_id = update.effective_user.id
        
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ Bu komut sadece admin kullanıcılar için mevcut.")
            return
        
        try:
            success = self.db.backup_database()
            
            if success:
                await update.message.reply_text(
                    "✅ Database backup başarıyla oluşturuldu.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    "❌ Database backup oluşturulamadı.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            await update.message.reply_text(f"❌ Backup hatası: {str(e)}")
    
    # ============ CALLBACK HANDLERS ============
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback query handler"""
        query = update.callback_query
        await query.answer()
        
        if not self._check_authorization(query.from_user.id):
            await query.edit_message_text("❌ Yetkisiz erişim!")
            return
        
        data = query.data
        
        # Route callbacks to appropriate handlers
        if data == "status":
            await self._handle_status_callback(query)
        elif data == "portfolio":
            await self._handle_portfolio_callback(query)
        elif data == "balance":
            await self._handle_balance_callback(query)
        elif data == "watchlist":
            await self._handle_watchlist_callback(query)
        elif data == "signals":
            await self._handle_signals_callback(query)
        elif data == "history":
            await self._handle_history_callback(query)
        elif data == "settings" or data == "settings_main":
            await self.settings_handlers.handle_settings_main(query)
        elif data.startswith("settings_category_"):
            category = data.split("_", 2)[2]
            await self.settings_handlers.handle_settings_category(query, category)
        elif data.startswith("settings_edit_"):
            parts = data.split("_", 3)
            category, key = parts[2], parts[3]
            await self.settings_handlers.handle_setting_edit(query, category, key)
        elif data.startswith("settings_reset_category_"):
            category = data.split("_", 3)[3]
            await self.settings_handlers.handle_reset_category(query, category)
        elif data == "settings_export":
            await self.settings_handlers.handle_settings_export(query)
        elif data == "settings_status":
            await self.settings_handlers.handle_settings_status(query)
        elif data == "help":
            await self._handle_help_callback(query)
        elif data.startswith("remove_coin_"):
            symbol = data.split("_", 2)[2]
            await self._remove_coin_from_watchlist(query, symbol)
        elif data.startswith("analyze_"):
            symbol = data.split("_", 1)[1]
            await self._analyze_symbol(query, symbol)
        elif data == "cancel":
            await query.edit_message_text("❌ İşlem iptal edildi.")
        else:
            await query.edit_message_text(f"⚠️ Bilinmeyen komut: {data}")
    
    # ============ MESSAGE HANDLERS ============
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Text message handler for conversations"""
        user_id = update.effective_user.id
        
        if not self._check_authorization(user_id):
            await self._send_unauthorized_message(update)
            return
        
        # Check if user is in a conversation
        if user_id not in self.user_sessions:
            # No active conversation, ignore message
            return
        
        session = self.user_sessions[user_id]
        state = session.get('state')
        text = update.message.text.strip()
        
        # Handle cancel
        if text.lower() in ['/cancel', 'cancel', 'iptal']:
            del self.user_sessions[user_id]
            await update.message.reply_text("❌ İşlem iptal edildi.")
            return
        
        # Handle conversation states
        if state == WAITING_FOR_COIN_SYMBOL:
            symbol = text.upper()
            await self._add_coin_to_watchlist(update, symbol)
            del self.user_sessions[user_id]
    
    # ============ UTILITY METHODS ============
    
    async def _add_coin_to_watchlist(self, update_or_query, symbol: str):
        """Add coin to watchlist utility"""
        try:
            # Validate symbol format
            if not symbol.isalpha() or len(symbol) < 2 or len(symbol) > 10:
                await self._send_response(update_or_query, "❌ Geçersiz coin sembolü!")
                return
            
            # Check if already exists
            if self.db.is_coin_watched(symbol):
                await self._send_response(update_or_query, f"⚠️ {symbol} zaten takip listesinde!")
                return
            
            # Format for exchange
            formatted_symbol = f"{symbol}_USDT"
            
            # Validate with exchange
            if not self.exchange_api.validate_instrument(formatted_symbol):
                await self._send_response(
                    update_or_query, 
                    f"❌ {symbol} coin'i exchange'de bulunamadı!\n"
                    f"Desteklenen coinleri kontrol edin."
                )
                return
            
            # Add to database
            success = self.db.add_watched_coin(symbol, formatted_symbol)
            
            if success:
                await self._send_response(
                    update_or_query, 
                    f"✅ {symbol} takip listesine eklendi!\n\n"
                    f"🔄 Sistem otomatik olarak analiz yapacak.\n"
                    f"📊 Manuel analiz: `/analyze {symbol}`"
                )
                
                # Log activity
                self.db.log_event("INFO", "telegram_bot", f"Coin added to watchlist: {symbol}")
            else:
                await self._send_response(update_or_query, f"❌ {symbol} eklenirken hata oluştu!")
                
        except Exception as e:
            logger.error(f"Error adding coin {symbol}: {str(e)}")
            await self._send_response(update_or_query, f"❌ Hata: {str(e)}")
    
    async def _remove_coin_from_watchlist(self, update_or_query, symbol: str):
        """Remove coin from watchlist utility"""
        try:
            # Check if exists
            if not self.db.is_coin_watched(symbol):
                await self._send_response(update_or_query, f"⚠️ {symbol} takip listesinde değil!")
                return
            
            # Check for active positions
            active_positions = self.db.get_active_positions(symbol)
            if active_positions:
                await self._send_response(
                    update_or_query,
                    f"❌ {symbol} için aktif pozisyon var!\n"
                    f"Önce pozisyonu kapatın."
                )
                return
            
            # Remove from database
            success = self.db.remove_watched_coin(symbol)
            
            if success:
                await self._send_response(
                    update_or_query, 
                    f"✅ {symbol} takip listesinden çıkarıldı!"
                )
                
                # Log activity
                self.db.log_event("INFO", "telegram_bot", f"Coin removed from watchlist: {symbol}")
            else:
                await self._send_response(update_or_query, f"❌ {symbol} çıkarılırken hata oluştu!")
                
        except Exception as e:
            logger.error(f"Error removing coin {symbol}: {str(e)}")
            await self._send_response(update_or_query, f"❌ Hata: {str(e)}")
    
    async def _analyze_symbol(self, update_or_query, symbol: str):
        """Analyze symbol utility"""
        try:
            await self._send_response(update_or_query, f"📊 {symbol} analiz ediliyor...")
            
            # Format symbol
            formatted_symbol = f"{symbol}_USDT" if "_" not in symbol else symbol
            
            # Generate signal
            signal = self.signal_engine.analyze_symbol(formatted_symbol)
            
            if not signal:
                await self._send_response(
                    update_or_query,
                    f"❌ {symbol} için analiz yapılamadı!\n"
                    f"Coin mevcut değil veya veri yetersiz."
                )
                return
            
            # Format analysis result
            signal_emoji = {
                "BUY": "🟢",
                "SELL": "🔴", 
                "WAIT": "⚪"
            }.get(signal.signal_type, "⚪")
            
            confidence_bars = "█" * int(signal.confidence * 5)
            
            analysis_text = f"""
📊 **{symbol} Teknik Analiz**

{signal_emoji} **Sinyal: {signal.signal_type}**
📈 **Fiyat:** ${signal.price:.6f}
🎯 **Güven:** {confidence_bars} ({signal.confidence:.0%})
⚠️ **Risk:** {signal.risk_level}

**📋 Teknik Göstergeler:**
• RSI: {signal.indicators.rsi:.1f} 
• ATR: {signal.indicators.atr:.6f}
• MA20: ${signal.indicators.ma_20:.6f}
• EMA12: ${signal.indicators.ema_12:.6f}

**🔍 Analiz Sebepleri:**
{chr(10).join(['• ' + reason for reason in signal.reasoning])}

**📊 Piyasa Verileri:**
• 24h Değişim: {signal.market_data.change_24h:+.2f}%
• 24h Yüksek: ${signal.market_data.high_24h:.6f}
• 24h Düşük: ${signal.market_data.low_24h:.6f}
• Volume: {signal.market_data.volume:.0f}

⏰ **Analiz Zamanı:** {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Save signal to database
            self.signal_engine.save_signal_to_db(signal)
            
            await self._send_response(update_or_query, analysis_text)
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            await self._send_response(update_or_query, f"❌ Analiz hatası: {str(e)}")
    
    async def _send_response(self, update_or_query, text: str, reply_markup=None):
        """Send response utility (handles both Update and CallbackQuery)"""
        try:
            if hasattr(update_or_query, 'callback_query'):
                # It's a CallbackQuery
                await update_or_query.edit_message_text(
                    text, 
                    parse_mode=ParseMode.MARKDOWN, 
                    reply_markup=reply_markup
                )
            elif hasattr(update_or_query, 'message'):
                # It's an Update
                await update_or_query.message.reply_text(
                    text, 
                    parse_mode=ParseMode.MARKDOWN, 
                    reply_markup=reply_markup
                )
            else:
                # It's a CallbackQuery directly
                await update_or_query.edit_message_text(
                    text, 
                    parse_mode=ParseMode.MARKDOWN, 
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")
    
    # ============ CALLBACK UTILITIES ============
    
    async def _handle_status_callback(self, query):
        """Handle status callback"""
        # Create a mock update for reusing status command logic
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_status(mock_update, None)
    
    async def _handle_portfolio_callback(self, query):
        """Handle portfolio callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_portfolio(mock_update, None)
    
    async def _handle_balance_callback(self, query):
        """Handle balance callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_balance(mock_update, None)
    
    async def _handle_watchlist_callback(self, query):
        """Handle watchlist callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_watchlist(mock_update, None)
    
    async def _handle_signals_callback(self, query):
        """Handle signals callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_signals(mock_update, None)
    
    async def _handle_history_callback(self, query):
        """Handle history callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_history(mock_update, None)
    
    async def _handle_settings_callback(self, query):
        """Handle settings callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_settings(mock_update, None)
    
    async def _handle_help_callback(self, query):
        """Handle help callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_help(mock_update, None)
    
    # ============ ERROR HANDLER ============
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Global error handler"""
        try:
            logger.error(f"Update {update} caused error {context.error}")
            logger.error(traceback.format_exc())
            
            # Log to database
            error_details = {
                'update': str(update) if update else None,
                'error': str(context.error),
                'traceback': traceback.format_exc()
            }
            
            user_id = update.effective_user.id if update and update.effective_user else None
            self.db.log_event("ERROR", "telegram_bot", str(context.error), error_details, user_id)
            
            # Send user-friendly error message
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Beklenmedik bir hata oluştu. Lütfen tekrar deneyin.\n\n"
                         "Sorun devam ederse admin ile iletişime geçin.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.critical(f"Error in error handler: {str(e)}")
    
    # ============ BOT LIFECYCLE ============
    
    async def start(self):
        """Bot'u başlat"""
        try:
            logger.info("🚀 Starting Telegram Trading Bot...")
            
            # Initialize components
            if not await self.initialize():
                logger.error("❌ Bot initialization failed")
                return False
            
            # Start polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            logger.info("✅ Telegram Trading Bot started successfully!")
            
            # Send startup notification
            await self._send_startup_notification()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def stop(self):
        """Bot'u durdur"""
        try:
            logger.info("🛑 Stopping Telegram Trading Bot...")
            
            self.is_running = False
            
            # Send shutdown notification
            await self._send_shutdown_notification()
            
            # Stop application
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            # Close connections
            if self.exchange_api:
                self.exchange_api.close()
            
            if self.db:
                self.db.close()
            
            logger.info("✅ Telegram Trading Bot stopped successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error stopping bot: {str(e)}")
    
    async def _send_startup_notification(self):
        """Send startup notification"""
        try:
            startup_text = """
🤖 **Trading Bot Başlatıldı!**

✅ Sistem aktif ve işlem bekliyor
📊 Sinyal motoru çalışıyor
💰 Exchange bağlantısı aktif

Komutlar için `/help` yazın.
            """
            
            await self.application.bot.send_message(
                chat_id=self.telegram_config.chat_id,
                text=startup_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error sending startup notification: {str(e)}")
    
    async def _send_shutdown_notification(self):
        """Send shutdown notification"""
        try:
            shutdown_text = """
🛑 **Trading Bot Kapatılıyor**

⚠️ Sistem kapatılıyor
📊 Aktif işlemler korunuyor
💾 Veriler kaydediliyor

Bot tekrar başlatılana kadar işlem yapılmayacak.
            """
            
            await self.application.bot.send_message(
                chat_id=self.telegram_config.chat_id,
                text=shutdown_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error sending shutdown notification: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_running:
            asyncio.create_task(self.stop())

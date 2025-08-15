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
    """Main Telegram Trading Bot class"""
    
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
        """Initialize bot components"""
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
        """Setup command and callback handlers"""
        
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
        """Setup bot commands menu"""
        commands = [
            BotCommand("start", "Start bot and welcome message"),
            BotCommand("help", "Help and command list"),
            BotCommand("status", "Bot status and system information"),
            BotCommand("portfolio", "Active positions and portfolio"),
            BotCommand("balance", "Exchange balance information"),
            BotCommand("watchlist", "Tracked coins"),
            BotCommand("signals", "Recent trading signals"),
            BotCommand("history", "Trade history"),
            BotCommand("settings", "Bot settings"),
            BotCommand("add_coin", "Add coin to watchlist"),
            BotCommand("remove_coin", "Remove coin from watchlist"),
            BotCommand("analyze", "Analyze specific coin"),
            BotCommand("health", "System health check"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands menu setup complete")
    
    def _check_authorization(self, user_id: int) -> bool:
        """User authorization check"""
        try:
            # Check from database
            is_authorized = self.db.is_user_authorized(user_id)
            
            # Also check from config
            config_authorized = (
                user_id in self.telegram_config.authorized_users or
                user_id in self.telegram_config.admin_users
            )
            
            return is_authorized or config_authorized
            
        except Exception as e:
            logger.error(f"Error checking authorization: {str(e)}")
            return False
    
    def _is_admin(self, user_id: int) -> bool:
        """Admin check"""
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
        """Start command"""
        user = update.effective_user
        user_id = user.id
        
        # Add user to database
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
🤖 <b>Welcome to Telegram Trading Bot!</b>

Hello {user.first_name}! 👋

This bot allows you to manage your cryptocurrency trading operations through Telegram.

<b>🚀 Key Features:</b>
• 📊 Technical analysis and signal generation
• 💰 Automated buy/sell operations  
• 📈 Portfolio tracking and reporting
• 🔔 Real-time notifications
• ⚙️ Flexible settings management

<b>📋 Getting Started Commands:</b>
• <code>/help</code> - Show all commands
• <code>/status</code> - Check bot status
• <code>/portfolio</code> - View your portfolio
• <code>/watchlist</code> - Show tracked coins
• <code>/settings</code> - Configure bot settings

<b>⚠️ Important Warning:</b>
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
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        # Log user activity
        self.db.log_event("INFO", "telegram_bot", f"User {user_id} started bot", 
                         {"user": user.to_dict()}, user_id)
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        help_text = """
📚 <b>Telegram Trading Bot - Command Guide</b>

<b>📊 Information Commands:</b>
• <code>/status</code> - Bot status and system information
• <code>/portfolio</code> - Active positions and P&L
• <code>/balance</code> - Exchange balance information
• <code>/watchlist</code> - Tracked coin list
• <code>/signals</code> - Recent trading signals
• <code>/history</code> - Trade history
• <code>/health</code> - System health check

<b>🔧 Management Commands:</b>
• <code>/add_coin [SYMBOL]</code> - Add coin to watchlist
• <code>/remove_coin [SYMBOL]</code> - Remove coin from list
• <code>/analyze [SYMBOL]</code> - Analyze specific coin
• <code>/settings</code> - View/edit bot settings

<b>⚙️ Settings:</b>
• Trade amount, risk parameters
• Notification preferences
• Auto trading enable/disable

<b>🔐 Admin Commands:</b>
• <code>/admin</code> - Admin panel
• <code>/logs</code> - System logs
• <code>/backup</code> - Database backup

<b>💡 Tips:</b>
• Commands can be used alone or with parameters
• Example: <code>/analyze BTC</code> or just <code>/analyze</code>
• Use buttons for interactive menus

<b>⚠️ Risk Warning:</b>
This bot trades with real money. Always be careful!
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status command"""
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
📊 <b>Bot Status Report</b>

<b>🤖 System Status:</b>
• Bot: ✅ Active
• Exchange: {exchange_status}
• Database: ✅ Connected ({db_stats.get('db_size_mb', 0)} MB)
• Signal Engine: ✅ Active

<b>📈 Trading Status:</b>
• Active Positions: {len(active_positions)}
• Tracked Coins: {db_stats.get('watched_coins_count', 0)}
• Last 24h Signals: {db_stats.get('signals_24h', 0)}
• Last 24h Trades: {db_stats.get('trades_24h', 0)}

<b>⚙️ Settings:</b>
• Trade Amount: {config_summary['trading']['trade_amount']} USDT
• Max Positions: {config_summary['trading']['max_positions']}
• Auto Trading: {'✅' if config_summary['trading']['auto_trading_enabled'] else '❌'}
• Paper Trading: {'✅' if config_summary['trading']['paper_trading_enabled'] else '❌'}

<b>🔔 Notifications:</b>
• Signals: {'✅' if config_summary['monitoring']['notifications_enabled'] else '❌'}
• Log Level: {config_summary['monitoring']['log_level']}

<b>⏰ Last Update:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
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
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in status command: {str(e)}")
            await update.message.reply_text(
                f"❌ Error getting status information:\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Portfolio command"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            # Active positions
            active_positions = self.db.get_active_positions()
            
            if not active_positions:
                portfolio_text = """
💰 <b>Portfolio Report</b>

📭 <b>No active positions found.</b>

To open positions:
• <code>/watchlist</code> to view tracked coins
• <code>/signals</code> to check trading signals
• <code>/add_coin [SYMBOL]</code> to add new coins
                """
            else:
                portfolio_text = "💰 <b>Portfolio Report</b>\n\n"
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
{status_emoji} <b>{symbol}</b>
• Entry: ${entry_price:.6f}
• Current: ${current_price:.6f}
• Quantity: {quantity:.6f}
• P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)
• TP: ${pos.get('take_profit', 0):.6f}
• SL: ${pos.get('stop_loss', 0):.6f}

                            """
                        else:
                            portfolio_text += f"""
⚪ <b>{symbol}</b>
• Entry: ${entry_price:.6f}
• Quantity: {quantity:.6f}
• Price unavailable

                            """
                    except Exception as e:
                        logger.error(f"Error getting price for {symbol}: {str(e)}")
                
                total_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
                portfolio_text += f"\n{total_emoji} <b>Total P&L: ${total_pnl:.2f}</b>"
            
            # Portfolio actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="portfolio"),
                    InlineKeyboardButton("💳 Balance", callback_data="balance")
                ],
                [
                    InlineKeyboardButton("📊 Signals", callback_data="signals"),
                    InlineKeyboardButton("📜 History", callback_data="history")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                portfolio_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in portfolio command: {str(e)}")
            await update.message.reply_text(
                f"❌ Error getting portfolio information:\n{str(e)}"
            )
    
    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Balance command"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            # Get all balances
            balances = self.exchange_api.get_all_balances()
            
            if not balances:
                balance_text = """
💳 <b>Balance Report</b>

❌ <b>Could not retrieve balance information</b>

Possible reasons:
• Exchange API connection issue
• Incorrect API keys
• Authorization problem
                """
            else:
                balance_text = "💳 <b>Balance Report</b>\n\n"
                
                # Significant balances first
                significant_balances = [b for b in balances if b.available > 0.01]
                other_balances = [b for b in balances if b.available <= 0.01 and b.available > 0]
                
                if significant_balances:
                    balance_text += "<b>💰 Main Balances:</b>\n"
                    for balance in significant_balances:
                        locked_info = f" (Locked: {balance.locked:.6f})" if balance.locked > 0 else ""
                        balance_text += f"• <b>{balance.currency}</b>: {balance.available:.6f}{locked_info}\n"
                
                if other_balances:
                    balance_text += f"\n<b>🪙 Others ({len(other_balances)} coins):</b>\n"
                    for balance in other_balances[:10]:  # Show only first 10
                        balance_text += f"• {balance.currency}: {balance.available:.6f}\n"
                    
                    if len(other_balances) > 10:
                        balance_text += f"• ... and {len(other_balances) - 10} more coins\n"
                
                # Trading status
                usdt_balance = next((b.available for b in balances if b.currency == "USDT"), 0)
                min_required = self.config.trading.min_balance_required
                
                if usdt_balance >= min_required:
                    balance_text += f"\n✅ <b>Sufficient balance for trading</b> (Min: {min_required} USDT)"
                else:
                    balance_text += f"\n⚠️ <b>Insufficient USDT balance</b> (Min: {min_required} USDT)"
            
            # Balance actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="balance"),
                    InlineKeyboardButton("💰 Portfolio", callback_data="portfolio")
                ],
                [
                    InlineKeyboardButton("📊 Status", callback_data="status")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                balance_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in balance command: {str(e)}")
            await update.message.reply_text(
                f"❌ Error getting balance information:\n{str(e)}"
            )
    
    async def _cmd_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Watchlist command"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            watched_coins = self.db.get_watched_coins()
            
            if not watched_coins:
                watchlist_text = """
📋 <b>Watchlist</b>

📭 <b>No coins being tracked.</b>

To add coins:
• <code>/add_coin BTC</code> (via command)
• Use "Add Coin" button below
                """
            else:
                watchlist_text = f"📋 <b>Watchlist</b> ({len(watched_coins)} coins)\n\n"
                
                for coin in watched_coins:
                    symbol = coin['symbol']
                    formatted_symbol = coin['formatted_symbol']
                    added_date = coin['added_date']
                    
                    # Get current price
                    try:
                        current_price = self.exchange_api.get_current_price(formatted_symbol)
                        price_info = f"${current_price:.6f}" if current_price else "Price unavailable"
                    except:
                        price_info = "Price unavailable"
                    
                    # Check if we have active position
                    active_pos = self.db.get_active_positions(symbol)
                    position_info = "📈 Active position" if active_pos else ""
                    
                    watchlist_text += f"• <b>{symbol}</b> ({formatted_symbol})\n"
                    watchlist_text += f"  💰 {price_info} {position_info}\n"
                    watchlist_text += f"  📅 Added: {added_date[:10]}\n\n"
            
            # Watchlist actions
            keyboard = [
                [
                    InlineKeyboardButton("➕ Add Coin", callback_data="add_coin"),
                    InlineKeyboardButton("➖ Remove Coin", callback_data="remove_coin")
                ],
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="watchlist"),
                    InlineKeyboardButton("📊 Analyze", callback_data="analyze")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                watchlist_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in watchlist command: {str(e)}")
            await update.message.reply_text(
                f"❌ Error getting watchlist:\n{str(e)}"
            )
    
    async def _cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Signals command"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            recent_signals = self.db.get_recent_signals(limit=10)
            
            if not recent_signals:
                signals_text = """
📊 <b>Trading Signals</b>

📭 <b>No signals generated yet.</b>

To generate signals:
• Add coins to watchlist (<code>/add_coin</code>)
• System will analyze automatically
• Manual analysis: <code>/analyze [SYMBOL]</code>
                """
            else:
                signals_text = f"📊 <b>Recent Trading Signals</b> ({len(recent_signals)})\n\n"
                
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
{emoji} <b>{symbol}</b> - {signal_type}
• Price: ${price:.6f}
• Confidence: {conf_bars} ({confidence:.0%})
• Time: {timestamp[:16]}

                    """
                
                if len(recent_signals) > 5:
                    signals_text += f"... and {len(recent_signals) - 5} more signals"
            
            # Signals actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="signals"),
                    InlineKeyboardButton("📈 All Signals", callback_data="all_signals")
                ],
                [
                    InlineKeyboardButton("📊 Analyze", callback_data="analyze"),
                    InlineKeyboardButton("💰 Portfolio", callback_data="portfolio")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                signals_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in signals command: {str(e)}")
            await update.message.reply_text(
                f"❌ Error getting signal information:\n{str(e)}"
            )
    
    async def _cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """History command"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            trade_history = self.db.get_trade_history(limit=10)
            
            if not trade_history:
                history_text = """
📜 <b>Trade History</b>

📭 <b>No trade history found yet.</b>

Will appear here after trading.
                """
            else:
                history_text = f"📜 <b>Recent Trades</b> ({len(trade_history)})\n\n"
                
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
                    history_text += f"... ve {len(trade_history) - 5} more trades\n\n"
                
                pnl_emoji = "💚" if total_pnl > 0 else "❤️" if total_pnl < 0 else "💛"
                history_text += f"{pnl_emoji} **Toplam P&L: ${total_pnl:.2f}**"
            
            # History actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="history"),
                    InlineKeyboardButton("📊 Details", callback_data="detailed_history")
                ],
                [
                    InlineKeyboardButton("💰 Portfolio", callback_data="portfolio"),
                    InlineKeyboardButton("📈 Signals", callback_data="signals")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                history_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in history command: {str(e)}")
            await update.message.reply_text(
                f"❌ Error getting trade history:\n{str(e)}"
            )
    
    async def _cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Settings command - New dynamic settings system"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            await self.settings_handlers.handle_settings_main(update)
            
        except Exception as e:
            logger.error(f"Error in settings command: {str(e)}")
            await update.message.reply_text(
                f"❌ Error getting settings:\n{str(e)}"
            )
    
    async def _cmd_add_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add coin command"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        # Check if symbol provided in command
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
            await self._add_coin_to_watchlist(update, symbol)
        else:
            # Start conversation
            await self._send_response(
                update,
                "➕ <b>Add Coin</b>\n\n"
                "Enter the coin symbol you want to add to watchlist:\n"
                "Example: <code>BTC</code>, <code>ETH</code>, <code>SUI</code>\n\n"
                "To cancel type <code>/cancel</code>."
            )
            
            # Set conversation state
            self.user_sessions[update.effective_user.id] = {
                'state': WAITING_FOR_COIN_SYMBOL,
                'action': 'add_coin'
            }
    
    async def _cmd_remove_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove coin command"""
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
                await self._send_response(
                    update,
                    "📭 No coins in watchlist."
                )
                return
            
            remove_text = "➖ <b>Remove Coin</b>\n\nSelect the coin you want to remove:"
            
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
                InlineKeyboardButton("🚫 Cancel", callback_data="cancel")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_response(
                update,
                remove_text,
                reply_markup=reply_markup
            )
    
    async def _cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analyze command"""
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
                await self._send_response(
                    update,
                    "📭 No coins found to analyze.\n\n"
                    "First add coins with <code>/add_coin</code> or\n"
                    "use <code>/analyze BTC</code> format."
                )
                return
            
            analyze_text = "📊 <b>Analyze</b>\n\nSelect the coin you want to analyze:"
            
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
                InlineKeyboardButton("🚫 Cancel", callback_data="cancel")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_response(
                update,
                analyze_text,
                reply_markup=reply_markup
            )
    
    async def _cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Health check command"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            health_status = []
            overall_healthy = True
            
            # Database health
            try:
                self.db.get_database_stats()
                health_status.append("✅ Database: Healthy")
            except Exception as e:
                health_status.append(f"❌ Database: {str(e)[:50]}")
                overall_healthy = False
            
            # Exchange API health
            try:
                balance = self.exchange_api.get_balance("USDT")
                health_status.append(f"✅ Exchange API: Healthy (USDT: {balance:.2f})")
            except Exception as e:
                health_status.append(f"❌ Exchange API: {str(e)[:50]}")
                overall_healthy = False
            
            # Signal engine health
            try:
                # Test signal generation with a simple symbol
                test_signal = self.signal_engine.analyze_symbol("BTC_USDT")
                if test_signal:
                    health_status.append("✅ Signal Engine: Healthy")
                else:
                    health_status.append("⚠️ Signal Engine: Could not generate test signal")
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
                health_status.append("⚠️ Sistem: Metrics unavailable")
            
            # Overall status
            status_emoji = "🟢" if overall_healthy else "🔴"
            overall_status = "Healthy" if overall_healthy else "Problems"
            
            health_text = f"""
🏥 **System Health Report**

  {status_emoji} **Overall Status: {overall_status}**

**📋 Details:**
{chr(10).join(['• ' + status for status in health_status])}

**⏰ Check Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Health actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Check Again", callback_data="health"),
                    InlineKeyboardButton("📊 Status", callback_data="status")
                ]
            ]
            
            if self._is_admin(update.effective_user.id):
                keyboard.append([
                    InlineKeyboardButton("📋 Detailed Logs", callback_data="detailed_logs")
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
                f"❌ Error during health check:\n{str(e)}"
            )
    
    # ============ ADMIN COMMANDS ============
    
    async def _cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command"""
        user_id = update.effective_user.id
        
        if not self._check_authorization(user_id):
            await self._send_unauthorized_message(update)
            return
        
        if not self._is_admin(user_id):
            await update.message.reply_text(
                "❌ This command is only available for admin users.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        admin_text = """
👑 **Admin Paneli**

**📊 Sistem Bilgileri:**
• Bot runtime
• Memory usage
• Database size
• API call count

**🔧 Management Operations:**
• User authorization
• System settings
• Database maintenance
• Log management

**⚠️ Use carefully!**
        """
        
        # Admin actions
        keyboard = [
            [
                InlineKeyboardButton("👥 Users", callback_data="admin_users"),
                InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
                InlineKeyboardButton("📋 Logs", callback_data="admin_logs")
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
        """Logs command (admin only)"""
        user_id = update.effective_user.id
        
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ This command is only available for admin users.")
            return
        
        try:
            recent_logs = self.db.get_recent_logs(limit=20)
            
            if not recent_logs:
                await update.message.reply_text("📋 No logs found.")
                return
            
            logs_text = "📋 **Recent System Logs**\n\n"
            
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
            await update.message.reply_text(f"❌ Log reading error: {str(e)}")
    
    async def _cmd_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Backup command (admin only)"""
        user_id = update.effective_user.id
        
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ This command is only available for admin users.")
            return
        
        try:
            success = self.db.backup_database()
            
            if success:
                await update.message.reply_text(
                    "✅ Database backup created successfully.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    "❌ Could not create database backup.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            await update.message.reply_text(f"❌ Backup error: {str(e)}")
    
    # ============ CALLBACK HANDLERS ============
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback query handler"""
        query = update.callback_query
        await query.answer()
        
        if not self._check_authorization(query.from_user.id):
            await query.edit_message_text("❌ Unauthorized access!")
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
        elif data == "add_coin":
            await self._handle_add_coin_callback(query)
        elif data == "remove_coin":
            await self._handle_remove_coin_callback(query)
        elif data == "analyze":
            await self._handle_analyze_callback(query)
        elif data == "detailed_history":
            await self._handle_detailed_history_callback(query)
        elif data == "cancel":
            await query.edit_message_text("❌ Operation cancelled.")
        elif data == "main_menu":
            await self._handle_main_menu_callback(query)
        else:
            await query.edit_message_text(f"⚠️ Unknown command: {data}")
    
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
            await update.message.reply_text("❌ Operation cancelled.")
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
                await self._send_response(update_or_query, "❌ Invalid coin symbol!")
                return
            
            # Check if already exists
            if self.db.is_coin_watched(symbol):
                await self._send_response(update_or_query, f"⚠️ {symbol} already in watchlist!")
                return
            
            # Format for exchange
            formatted_symbol = f"{symbol}_USDT"
            
            # Validate with exchange
            if not self.exchange_api.validate_instrument(formatted_symbol):
                await self._send_response(
                    update_or_query, 
                    f"❌ {symbol} coin'i not found on exchange!\n"
                    f"Check supported coins."
                )
                return
            
            # Add to database
            success = self.db.add_watched_coin(symbol, formatted_symbol)
            
            if success:
                await self._send_response(
                    update_or_query, 
                    f"✅ {symbol} added to watchlist!\n\n"
                    f"🔄 System will analyze automatically.\n"
                    f"📊 Manual analysis: `/analyze {symbol}`"
                )
                
                # Log activity
                self.db.log_event("INFO", "telegram_bot", f"Coin added to watchlist: {symbol}")
            else:
                await self._send_response(update_or_query, f"❌ {symbol} error occurred while adding!")
                
        except Exception as e:
            logger.error(f"Error adding coin {symbol}: {str(e)}")
            await self._send_response(update_or_query, f"❌ Hata: {str(e)}")
    
    async def _remove_coin_from_watchlist(self, update_or_query, symbol: str):
        """Remove coin from watchlist utility"""
        try:
            # Check if exists
            if not self.db.is_coin_watched(symbol):
                await self._send_response(update_or_query, f"⚠️ {symbol} not in watchlist!")
                return
            
            # Check for active positions
            active_positions = self.db.get_active_positions(symbol)
            if active_positions:
                await self._send_response(
                    update_or_query,
                                         f"❌ {symbol} has active position!\n"
                     f"Close position first."
                )
                return
            
            # Remove from database
            success = self.db.remove_watched_coin(symbol)
            
            if success:
                await self._send_response(
                    update_or_query, 
                    f"✅ {symbol} removed from watchlist!"
                )
                
                # Log activity
                self.db.log_event("INFO", "telegram_bot", f"Coin removed from watchlist: {symbol}")
            else:
                await self._send_response(update_or_query, f"❌ {symbol} error occurred while removing!")
                
        except Exception as e:
            logger.error(f"Error removing coin {symbol}: {str(e)}")
            await self._send_response(update_or_query, f"❌ Hata: {str(e)}")
    
    async def _analyze_symbol(self, update_or_query, symbol: str):
        """Analyze symbol utility"""
        try:
            await self._send_response(update_or_query, f"📊 {symbol} analyzing...")
            
            # Format symbol
            formatted_symbol = f"{symbol}_USDT" if "_" not in symbol else symbol
            
            # Generate signal
            signal = self.signal_engine.analyze_symbol(formatted_symbol)
            
            if not signal:
                await self._send_response(
                    update_or_query,
                    f"❌ {symbol} could not analyze!\n"
                    f"Coin unavailable or insufficient data."
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
📊 <b>{symbol} Technical Analysis</b>

{signal_emoji} <b>Signal: {signal.signal_type}</b>
📈 <b>Price:</b> ${signal.price:.6f}
🎯 <b>Confidence:</b> {confidence_bars} ({signal.confidence:.0%})
⚠️ <b>Risk:</b> {signal.risk_level}

<b>📋 Technical Indicators:</b>
• RSI: {signal.indicators.rsi:.1f} 
• ATR: {signal.indicators.atr:.6f}
• MA20: ${signal.indicators.ma_20:.6f}
• EMA12: ${signal.indicators.ema_12:.6f}

<b>🔍 Analysis Reasons:</b>
{chr(10).join(['• ' + reason for reason in signal.reasoning])}

<b>📊 Market Data:</b>
• 24h Change: {signal.market_data.change_24h:+.2f}%
• 24h High: ${signal.market_data.high_24h:.6f}
• 24h Low: ${signal.market_data.low_24h:.6f}
• Volume: {signal.market_data.volume:.0f}

⏰ <b>Analysis Time:</b> {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Save signal to database
            self.signal_engine.save_signal_to_db(signal)
            
            await self._send_response(update_or_query, analysis_text)
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            await self._send_response(update_or_query, f"❌ Analysis error: {str(e)}")
    
    async def _send_response(self, update_or_query, text: str, reply_markup=None):
        """Send response utility (handles both Update and CallbackQuery)"""
        try:
            if hasattr(update_or_query, 'edit_message_text'):
                # It's a CallbackQuery
                await update_or_query.edit_message_text(
                    text, 
                    parse_mode=ParseMode.HTML, 
                    reply_markup=reply_markup
                )
            elif hasattr(update_or_query, 'message') and update_or_query.message:
                # It's an Update with message
                await update_or_query.message.reply_text(
                    text, 
                    parse_mode=ParseMode.HTML, 
                    reply_markup=reply_markup
                )
            elif hasattr(update_or_query, 'effective_chat'):
                # It's an Update but message might be None, use bot directly
                await self.application.bot.send_message(
                    chat_id=update_or_query.effective_chat.id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
            else:
                logger.error(f"Unknown update_or_query type: {type(update_or_query)}")
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")
            # Fallback - try with callback query answer
            if hasattr(update_or_query, 'answer'):
                try:
                    await update_or_query.answer(text[:200])  # Callback answers are limited
                except:
                    pass
    
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
    
    async def _handle_main_menu_callback(self, query):
        """Handle main menu callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_start(mock_update, None)
    
    async def _handle_add_coin_callback(self, query):
        """Handle add coin callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        class MockContext:
            def __init__(self):
                self.args = []
        
        mock_update = MockUpdate(query)
        mock_context = MockContext()
        await self._cmd_add_coin(mock_update, mock_context)
    
    async def _handle_remove_coin_callback(self, query):
        """Handle remove coin callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        class MockContext:
            def __init__(self):
                self.args = []
        
        mock_update = MockUpdate(query)
        mock_context = MockContext()
        await self._cmd_remove_coin(mock_update, mock_context)
    
    async def _handle_analyze_callback(self, query):
        """Handle analyze callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        class MockContext:
            def __init__(self):
                self.args = []
        
        mock_update = MockUpdate(query)
        mock_context = MockContext()
        await self._cmd_analyze(mock_update, mock_context)
    
    async def _handle_detailed_history_callback(self, query):
        """Handle detailed history callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        # For now, just show the same history but with more details
        await self._cmd_history(mock_update, None)
    
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
                    text="❌ An unexpected error occurred. Please try again.\n\n"
                         "If the problem persists, contact the admin.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.critical(f"Error in error handler: {str(e)}")
    
    # ============ BOT LIFECYCLE ============
    
    async def start(self):
        """Start the bot"""
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
🤖 **Trading Bot Started!**

✅ System active and waiting for trades
📊 Signal engine running
💰 Exchange connection active

Type `/help` for commands.
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
🛑 **Trading Bot Shutting Down**

⚠️ System shutting down
📊 Active trades protected
💾 Data being saved

No trades will be executed until bot is restarted.
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

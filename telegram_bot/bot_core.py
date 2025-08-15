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
        
        # Test commands
        self.application.add_handler(CommandHandler("test_buy", self._cmd_test_buy))
        self.application.add_handler(CommandHandler("test_sell", self._cmd_test_sell))
        self.application.add_handler(CommandHandler("force_signal", self._cmd_force_signal))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Combined message handler for conversations and settings
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
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

<b>🧪 Test Commands:</b>
• <code>/test_buy [SYMBOL]</code> - Create manual BUY signal
• <code>/test_sell [SYMBOL]</code> - Create manual SELL signal
• <code>/force_signal</code> - Generate signals for all coins

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
            # Refresh config from dynamic settings first
            self.dynamic_settings.apply_runtime_settings(self.config)
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
        """Portfolio command - get data directly from exchange"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            # Get all balances from exchange
            all_balances = self.exchange_api.get_all_balances()
            
            # Filter out zero balances and USDT (show separately)
            significant_balances = []
            usdt_balance = 0
            
            for balance in all_balances:
                if balance.available > 0.00001:  # Filter very small amounts
                    if balance.currency == "USDT":
                        usdt_balance = balance.available
                    else:
                        significant_balances.append(balance)
            
            if not significant_balances and usdt_balance < 1:
                portfolio_text = """
💰 <b>Portfolio Report</b>

📭 <b>No significant balances found.</b>

To start trading:
• Deposit funds to your exchange account
• Use <code>/signals</code> to view trading opportunities
• <code>/signals</code> to check trading signals
• <code>/add_coin [SYMBOL]</code> to add new coins
                """
            else:
                portfolio_text = "💰 <b>Portfolio Report</b>\n\n"
                
                # Show USDT balance first
                if usdt_balance > 0:
                    portfolio_text += f"💵 <b>USDT Balance:</b> ${usdt_balance:.2f}\n\n"
                
                # Show crypto balances
                portfolio_text += f"🪙 <b>Crypto Holdings</b> ({len(significant_balances)})\n"
                
                total_value_usd = usdt_balance
                
                for balance in significant_balances:
                    currency = balance.currency
                    available = balance.available
                    total = balance.total
                    locked = balance.locked
                    
                    # Get current price in USDT
                    try:
                        price_symbol = f"{currency}_USDT"
                        current_price = self.exchange_api.get_current_price(price_symbol)
                        
                        if current_price:
                            value_usd = available * current_price
                            total_value_usd += value_usd
                            
                            portfolio_text += f"""
💎 <b>{currency}</b>
• Available: {available:.6f}
• Total: {total:.6f}
• Locked: {locked:.6f}
• Price: ${current_price:.6f}
• Value: ${value_usd:.2f}

                            """
                        else:
                            portfolio_text += f"""
💎 <b>{currency}</b>
• Available: {available:.6f}
• Total: {total:.6f}
• Locked: {locked:.6f}
• Price: N/A

                            """
                    except Exception as e:
                        logger.error(f"Error getting price for {currency}: {str(e)}")
                        portfolio_text += f"""
💎 <b>{currency}</b>
• Available: {available:.6f}
• Total: {total:.6f}
• Locked: {locked:.6f}

                        """
                
                portfolio_text += f"\n💰 <b>Total Portfolio Value: ${total_value_usd:.2f}</b>"
            
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
            # Refresh config from dynamic settings
            self.dynamic_settings.apply_runtime_settings(self.config)
            
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
        """History command - get data directly from exchange"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            # Get trade history directly from exchange
            trade_history = self.exchange_api.get_trade_history(limit=20)
            order_history = self.exchange_api.get_order_history(limit=10)
            
            if not trade_history and not order_history:
                history_text = """
📜 <b>Trading History</b>

📭 <b>No trading history found.</b>

History will appear here after you place trades.
                """
            else:
                history_text = f"📜 <b>Recent Trading Activity</b>\n\n"
                
                # Show recent trades
                if trade_history:
                    history_text += f"💱 <b>Recent Trades</b> ({len(trade_history)})\n"
                    
                    for trade in trade_history[:5]:  # Show last 5
                        symbol = trade.instrument_name
                        action = trade.side
                        price = trade.price
                        quantity = trade.quantity
                        fee = trade.fee
                        timestamp = trade.timestamp if hasattr(trade, 'timestamp') else 'N/A'
                        
                        action_emoji = "🟢" if action == "BUY" else "🔴"
                        
                        history_text += f"""
{action_emoji} <b>{symbol}</b> - {action}
• Price: ${price:.6f}
• Quantity: {quantity:.6f}
• Fee: ${fee:.4f}
• Time: {timestamp[:16] if timestamp != 'N/A' else 'N/A'}

                        """
                    
                    if len(trade_history) > 5:
                        history_text += f"... and {len(trade_history) - 5} more trades\n\n"
                
                # Show recent orders
                if order_history:
                    history_text += f"📝 <b>Recent Orders</b> ({len(order_history)})\n"
                    
                    for order in order_history[:3]:  # Show last 3
                        symbol = order.instrument_name
                        side = order.side
                        status = order.status
                        price = order.price
                        quantity = order.quantity
                        filled_qty = order.filled_quantity
                        
                        status_emoji = {
                            "FILLED": "✅",
                            "ACTIVE": "🟡", 
                            "CANCELLED": "❌",
                            "REJECTED": "🚫",
                            "EXPIRED": "⏰"
                        }.get(status, "❓")
                        
                        side_emoji = "🟢" if side == "BUY" else "🔴"
                        
                        history_text += f"""
{side_emoji} <b>{symbol}</b> - {side} {status_emoji}
• Status: {status}
• Price: ${price:.6f}
• Quantity: {quantity:.6f}
• Filled: {filled_qty:.6f}

                        """
            
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
👑 <b>Admin Panel</b>

<b>📊 System Information:</b>
• Bot runtime
• Memory usage
• Database size
• API call count

<b>🔧 Management Operations:</b>
• User authorization
• System settings
• Database maintenance
• Log management

<b>⚠️ Use carefully!</b>
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
            parse_mode=ParseMode.HTML,
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
        # Admin callbacks
        elif data == "admin_users":
            await self._handle_admin_users_callback(query)
        elif data == "admin_stats":
            await self._handle_admin_stats_callback(query)
        elif data == "admin_settings":
            await self._handle_admin_settings_callback(query)
        elif data == "admin_logs":
            await self._handle_admin_logs_callback(query)
        elif data == "admin_backup":
            await self._handle_admin_backup_callback(query)
        elif data == "admin_restart":
            await self._handle_admin_restart_callback(query)
        elif data == "admin":
            await self._handle_admin_callback(query)
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
        """Text message handler for conversations and settings"""
        user_id = update.effective_user.id
        
        if not self._check_authorization(user_id):
            await self._send_unauthorized_message(update)
            return
        
        # First check if settings handler wants to handle this message
        try:
            # Check if user is in settings conversation
            if user_id in self.settings_handlers.user_sessions:
                session = self.settings_handlers.user_sessions[user_id]
                if session.get('state') == WAITING_FOR_SETTING_VALUE:
                    await self.settings_handlers.handle_setting_value_input(update, context)
                    return
        except Exception as e:
            logger.error(f"Error handling settings input: {str(e)}")
        
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
        """Handle detailed history callback - show comprehensive trading history"""
        try:
            if not self._check_authorization(query.from_user.id):
                await query.edit_message_text("❌ Unauthorized access!")
                return
            
            # Get more comprehensive history data
            trade_history = self.exchange_api.get_trade_history(limit=50)
            order_history = self.exchange_api.get_order_history(limit=25)
            
            if not trade_history and not order_history:
                history_text = """
📜 <b>Detailed Trading History</b>

📭 <b>No trading history found.</b>

History will appear here after you place trades.
                """
            else:
                history_text = f"📜 <b>Detailed Trading History</b>\n\n"
                
                # Statistics
                total_trades = len(trade_history)
                total_orders = len(order_history)
                total_fees = sum(trade.fee for trade in trade_history)
                
                history_text += f"""
📊 <b>Statistics</b>
• Total Trades: {total_trades}
• Total Orders: {total_orders}  
• Total Fees: ${total_fees:.4f}

                """
                
                # Show all trades with more details
                if trade_history:
                    history_text += f"💱 <b>All Trades</b> (Last {len(trade_history)})\n"
                    
                    for i, trade in enumerate(trade_history[:10], 1):  # Show last 10
                        symbol = trade.instrument_name
                        action = trade.side
                        price = trade.price
                        quantity = trade.quantity
                        fee = trade.fee
                        trade_id = trade.trade_id[:8] if trade.trade_id else 'N/A'
                        timestamp = trade.timestamp if hasattr(trade, 'timestamp') else 'N/A'
                        
                        action_emoji = "🟢" if action == "BUY" else "🔴"
                        
                        history_text += f"""
{i}. {action_emoji} <b>{symbol}</b> - {action}
   • Price: ${price:.6f}
   • Qty: {quantity:.6f}
   • Fee: ${fee:.4f}
   • ID: {trade_id}
   • Time: {timestamp[:16] if timestamp != 'N/A' else 'N/A'}

                        """
                    
                    if len(trade_history) > 10:
                        history_text += f"... and {len(trade_history) - 10} more trades\n\n"
                
                # Show order status breakdown
                if order_history:
                    status_counts = {}
                    for order in order_history:
                        status = order.status
                        status_counts[status] = status_counts.get(status, 0) + 1
                    
                    history_text += f"📝 <b>Order Status Breakdown</b>\n"
                    for status, count in status_counts.items():
                        emoji = {
                            "FILLED": "✅",
                            "ACTIVE": "🟡", 
                            "CANCELLED": "❌",
                            "REJECTED": "🚫",
                            "EXPIRED": "⏰"
                        }.get(status, "❓")
                        history_text += f"• {emoji} {status}: {count}\n"
            
            # Navigation buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="detailed_history"),
                    InlineKeyboardButton("📊 Summary", callback_data="history")
                ],
                [
                    InlineKeyboardButton("💰 Portfolio", callback_data="portfolio"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                history_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in detailed history callback: {str(e)}")
            await query.edit_message_text(
                f"❌ Error getting detailed history:\n{str(e)}"
            )
    
    # ============ ADMIN CALLBACK HANDLERS ============
    
    async def _handle_admin_users_callback(self, query):
        """Handle admin users callback"""
        if not self._is_admin(query.from_user.id):
            await query.answer("❌ Admin access required.")
            return
        
        try:
            users_text = "<b>👥 User Management</b>\n\n"
            users_text += f"<b>📊 Statistics:</b>\n"
            users_text += f"• Total users: {len(self.config.telegram.authorized_users)}\n"
            users_text += f"• Admin users: {len(self.config.telegram.admin_users)}\n\n"
            
            users_text += f"<b>👤 Authorized Users:</b>\n"
            for user_id in self.config.telegram.authorized_users:
                is_admin = user_id in self.config.telegram.admin_users
                role = "👑 Admin" if is_admin else "👤 User"
                users_text += f"• {role}: <code>{user_id}</code>\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                users_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in admin users callback: {str(e)}")
            await query.answer("❌ Error loading user information.")
    
    async def _handle_admin_stats_callback(self, query):
        """Handle admin stats callback"""
        if not self._is_admin(query.from_user.id):
            await query.answer("❌ Admin access required.")
            return
            
        try:
            # Refresh config from dynamic settings first
            self.dynamic_settings.apply_runtime_settings(self.config)
            
            stats_text = "<b>📊 System Statistics</b>\n\n"
            
            # Database stats
            db_stats = self.db.get_database_stats()
            stats_text += f"<b>🗄️ Database:</b>\n"
            stats_text += f"• Size: {db_stats.get('db_size_mb', 0):.2f} MB\n"
            stats_text += f"• Watched Coins: {db_stats.get('watched_coins_count', 0)}\n"
            stats_text += f"• Active Positions: {db_stats.get('active_positions_count', 0)}\n"
            stats_text += f"• Total Trades: {db_stats.get('total_trades', 0)}\n"
            stats_text += f"• Signals (24h): {db_stats.get('signals_24h', 0)}\n\n"
            
            # System stats
            try:
                import psutil
                stats_text += f"<b>🖥️ System:</b>\n"
                stats_text += f"• CPU Usage: {psutil.cpu_percent():.1f}%\n"
                stats_text += f"• Memory Usage: {psutil.virtual_memory().percent:.1f}%\n"
                stats_text += f"• Disk Usage: {psutil.disk_usage('.').percent:.1f}%\n\n"
            except ImportError:
                stats_text += f"<b>🖥️ System:</b>\n• System monitoring not available\n\n"
            
            # Trading stats
            stats_text += f"<b>💹 Trading:</b>\n"
            stats_text += f"• Paper Trading: {'✅' if self.config.trading.enable_paper_trading else '❌'}\n"
            stats_text += f"• Auto Trading: {'✅' if self.config.trading.enable_auto_trading else '❌'}\n"
            stats_text += f"• Trade Amount: {self.config.trading.trade_amount} USDT\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stats_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in admin stats callback: {str(e)}")
            await query.answer("❌ Error loading statistics.")
    
    async def _handle_admin_settings_callback(self, query):
        """Handle admin settings callback"""
        if not self._is_admin(query.from_user.id):
            await query.answer("❌ Admin access required.")
            return
        
        # Redirect to settings manager
        await self.settings_handlers.handle_settings_main(query)
    
    async def _handle_admin_logs_callback(self, query):
        """Handle admin logs callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_logs(mock_update, None)
    
    async def _handle_admin_backup_callback(self, query):
        """Handle admin backup callback"""
        class MockUpdate:
            def __init__(self, query):
                self.effective_user = query.from_user
                self.message = query.message
                self.callback_query = query
        
        mock_update = MockUpdate(query)
        await self._cmd_backup(mock_update, None)
    
    async def _handle_admin_restart_callback(self, query):
        """Handle admin restart callback"""
        if not self._is_admin(query.from_user.id):
            await query.answer("❌ Admin access required.")
            return
        
        try:
            await query.edit_message_text(
                "<b>🔄 System Restart</b>\n\n"
                "⚠️ <b>Warning:</b> This will restart the bot.\n\n"
                "Are you sure you want to continue?",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Yes, Restart", callback_data="confirm_restart"),
                        InlineKeyboardButton("❌ Cancel", callback_data="admin")
                    ]
                ])
            )
        except Exception as e:
            logger.error(f"Error in admin restart callback: {str(e)}")
            await query.answer("❌ Error processing restart request.")
    
    async def _handle_admin_callback(self, query):
        """Handle admin main callback - show admin panel"""
        if not self._is_admin(query.from_user.id):
            await query.answer("❌ Admin access required.")
            return
        
        try:
            admin_text = """
👑 <b>Admin Panel</b>

<b>📊 System Information:</b>
• Bot runtime
• Memory usage
• Database size
• API call count

<b>🔧 Management Operations:</b>
• User authorization
• System settings
• Database maintenance
• Log management

<b>⚠️ Use carefully!</b>
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
            
            await query.edit_message_text(
                admin_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in admin callback: {str(e)}")
            await query.answer("❌ Error loading admin panel.")
    
    # ============ TEST COMMANDS ============
    
    async def _cmd_test_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create manual BUY signal for testing"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        # Get symbol from args or ask for it
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
            await self._create_test_signal(update, symbol, "BUY")
        else:
            await self._send_response(
                update,
                "🧪 <b>Create Test BUY Signal</b>\n\n"
                "Enter coin symbol to create BUY signal:\n"
                "Example: <code>/test_buy BTC</code>\n\n"
                "⚠️ This will create a manual BUY signal for testing purposes."
            )
    
    async def _cmd_test_sell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create manual SELL signal for testing"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        # Get symbol from args or ask for it
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
            await self._create_test_signal(update, symbol, "SELL")
        else:
            await self._send_response(
                update,
                "🧪 <b>Create Test SELL Signal</b>\n\n"
                "Enter coin symbol to create SELL signal:\n"
                "Example: <code>/test_sell BTC</code>\n\n"
                "⚠️ This will create a manual SELL signal for testing purposes."
            )
    
    async def _cmd_force_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Force signal generation for all watched coins"""
        if not self._check_authorization(update.effective_user.id):
            await self._send_unauthorized_message(update)
            return
        
        try:
            await self._send_response(
                update,
                "🔄 <b>Force Signal Generation</b>\n\n"
                "Generating signals for all watched coins...\n"
                "This may take a few moments."
            )
            
            # Get watched coins
            watched_coins = self.db.get_watched_coins()
            signals_generated = 0
            
            for coin in watched_coins:
                try:
                    # Generate signal for this coin
                    signal = await self._generate_signal_for_coin(coin['symbol'])
                    if signal:
                        signals_generated += 1
                        # Save signal to database
                        self.db.save_signal(
                            symbol=coin['symbol'],
                            signal_type=signal['action'],
                            strength=signal.get('strength', 'medium'),
                            price=signal.get('current_price', 0.0),
                            indicators=signal.get('indicators', {}),
                            reasoning=signal.get('reasoning', 'Forced signal generation')
                        )
                        
                        # Send notification
                        await self._send_signal_notification(signal)
                        
                except Exception as e:
                    logger.error(f"Error generating signal for {coin['symbol']}: {str(e)}")
            
            result_text = f"✅ <b>Signal Generation Complete</b>\n\n"
            result_text += f"• Processed: {len(watched_coins)} coins\n"
            result_text += f"• Signals generated: {signals_generated}\n\n"
            result_text += f"Check <code>/signals</code> to view results."
            
            await self._send_response(update, result_text)
            
        except Exception as e:
            logger.error(f"Error in force signal command: {str(e)}")
            await self._send_response(
                update,
                f"❌ Error generating signals:\n{str(e)}"
            )
    
    async def _create_test_signal(self, update_or_query, symbol: str, action: str):
        """Create a manual test signal"""
        try:
            # Check if coin is in watchlist
            watched_coins = self.db.get_watched_coins()
            coin_symbols = [coin['symbol'] for coin in watched_coins]
            
            if symbol not in coin_symbols:
                await self._send_response(
                    update_or_query,
                    f"❌ <b>Coin not found in watchlist</b>\n\n"
                    f"Add <code>{symbol}</code> to watchlist first with:\n"
                    f"<code>/add_coin {symbol}</code>"
                )
                return
            
            # Get current price
            try:
                current_price = await self.signal_engine.get_current_price(symbol)
                if not current_price:
                    current_price = 1.0  # Fallback for testing
            except Exception as e:
                logger.warning(f"Could not get price for {symbol}: {str(e)}")
                current_price = 1.0
            
            # Create test signal
            test_signal = {
                'symbol': symbol,
                'action': action,
                'current_price': current_price,
                'strength': 'medium',
                'reasoning': f'Manual {action} signal created for testing',
                'indicators': {
                    'rsi': 50.0,
                    'test_mode': True
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Save to database
            signal_id = self.db.save_signal(
                symbol=symbol,
                formatted_symbol=f"{symbol}_USDT",
                signal_type=action,
                price=current_price,
                confidence=0.8,  # Default confidence for test signals
                indicators=test_signal['indicators'],
                notes="; ".join(test_signal['reasoning']) if test_signal['reasoning'] else "Test signal"
            )
            
            # Execute actual trade if enabled
            trade_executed = False
            if self.dynamic_settings.get_setting('trading', 'enable_auto_trading', False):
                trade_result = await self._execute_signal_trade(symbol, action, current_price)
                if trade_result:
                    trade_executed = True
            
            # Send notification
            await self._send_signal_notification(test_signal)
            
            # Confirm to user
            trade_status = "✅ Trade Executed" if trade_executed else "📊 Signal Only (Auto-trading disabled)"
            
            result_text = f"✅ <b>Test {action} Signal Created</b>\n\n"
            result_text += f"• Symbol: <code>{symbol}</code>\n"
            result_text += f"• Action: <b>{action}</b>\n"
            result_text += f"• Price: ${current_price:.6f}\n"
            result_text += f"• Status: {trade_status}\n"
            result_text += f"• Signal ID: {signal_id}\n\n"
            result_text += f"🤖 Bot processed this signal according to your settings.\n"
            result_text += f"Check <code>/signals</code> and <code>/portfolio</code> for updates."
            
            await self._send_response(update_or_query, result_text)
            
        except Exception as e:
            logger.error(f"Error creating test signal: {str(e)}")
            await self._send_response(
                update_or_query,
                f"❌ Error creating test signal:\n{str(e)}"
            )
    
    async def _generate_signal_for_coin(self, symbol: str):
        """Generate signal for a specific coin"""
        try:
            # Use signal engine to analyze
            indicators = await self.signal_engine.get_technical_indicators(symbol)
            if not indicators:
                return None
            
            # Simple signal logic for testing
            rsi = indicators.rsi
            if rsi and rsi < 30:
                return {
                    'symbol': symbol,
                    'action': 'BUY',
                    'current_price': indicators.current_price,
                    'strength': 'strong' if rsi < 25 else 'medium',
                    'reasoning': f'RSI oversold ({rsi:.1f})',
                    'indicators': {
                        'rsi': rsi,
                        'price': indicators.current_price
                    }
                }
            elif rsi and rsi > 70:
                return {
                    'symbol': symbol,
                    'action': 'SELL',
                    'current_price': indicators.current_price,
                    'strength': 'strong' if rsi > 75 else 'medium',
                    'reasoning': f'RSI overbought ({rsi:.1f})',
                    'indicators': {
                        'rsi': rsi,
                        'price': indicators.current_price
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {str(e)}")
            return None
    
    async def _execute_signal_trade(self, symbol: str, action: str, price: float) -> bool:
        """Execute actual trade based on signal"""
        try:
            # Check if auto trading is enabled
            auto_trading = self.dynamic_settings.get_setting('trading', 'enable_auto_trading', False)
            if not auto_trading:
                logger.info(f"Auto trading disabled - skipping trade execution for {symbol}")
                return False
            
            # Get trade amount
            trade_amount = self.dynamic_settings.get_setting('trading', 'trade_amount', 10.0)
            
            # Format symbol for exchange (BTC -> BTCUSDT)
            if '_' not in symbol and 'USDT' not in symbol:
                exchange_symbol = f"{symbol}USDT"
            else:
                exchange_symbol = symbol
            
            logger.info(f"Attempting to execute {action} trade for {exchange_symbol} with ${trade_amount}")
            
            # Execute trade via exchange API
            if action.upper() == "BUY":
                # Check balance first
                if not self.exchange_api.has_sufficient_balance():
                    logger.warning(f"Insufficient balance for ${trade_amount} trade")
                    return False
                
                # Execute buy order
                result = self.exchange_api.buy_coin(exchange_symbol, trade_amount)
                if result:
                    logger.info(f"✅ BUY order executed for {exchange_symbol}: ${trade_amount}")
                    
                    # Log trade to database
                    self.db.log_event(
                        level="INFO",
                        module="trade_execution", 
                        message=f"BUY trade executed: {exchange_symbol} @ ${price:.6f}",
                        details={
                            "symbol": exchange_symbol,
                            "action": "BUY",
                            "amount_usd": trade_amount,
                            "price": price,
                            "order_result": str(result)
                        }
                    )
                    return True
                else:
                    logger.error(f"❌ BUY order failed for {exchange_symbol}")
                    return False
                    
            elif action.upper() == "SELL":
                # Check if we have an existing position to sell
                if not hasattr(self, 'active_positions'):
                    self.active_positions = {}
                
                # Get current balance of the base currency
                base_currency = exchange_symbol.split('_')[0] if '_' in exchange_symbol else exchange_symbol.replace('USDT', '')
                balance = self.exchange_api.get_coin_balance(base_currency)
                
                logger.info(f"Balance for {base_currency}: {balance}")
                
                if balance and balance > 0:
                    # Calculate quantity to sell (99% of balance to avoid precision errors)
                    quantity_to_sell = balance * 0.99
                    logger.info(f"Executing SELL order for {exchange_symbol}, balance: {balance}, quantity_to_sell: {quantity_to_sell}")
                    
                    # Execute sell order with explicit quantity
                    order_id = self.exchange_api.sell_coin(exchange_symbol, quantity_to_sell)
                    
                    if order_id:
                        logger.info(f"✅ SELL order placed for {exchange_symbol} with ID: {order_id}")
                        
                        # Send success notification
                        for user_id in self.config.telegram.authorized_users:
                            try:
                                await self.application.bot.send_message(
                                    chat_id=user_id,
                                    text=f"✅ SELL order placed!\n📊 Symbol: {exchange_symbol}\n📈 Amount: {balance:.6f} {base_currency}\n🆔 Order ID: {order_id}",
                                    parse_mode=ParseMode.HTML
                                )
                            except Exception as e:
                                logger.error(f"Error sending SELL notification to {user_id}: {str(e)}")
                        
                        return True
                    else:
                        logger.error(f"❌ SELL order failed for {exchange_symbol}")
                        return False
                else:
                    logger.warning(f"No {base_currency} balance available for selling")
                    return False
                
            return False
            
        except Exception as e:
            logger.error(f"Error executing trade for {symbol}: {str(e)}")
            return False
    
    async def _send_signal_notification(self, signal):
        """Send signal notification to users"""
        try:
            action_emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
            strength_emoji = "🔥" if signal.get('strength') == 'strong' else "⚡"
            
            notification_text = f"""
{action_emoji} <b>{signal['action']} SIGNAL</b> {strength_emoji}

<b>📊 {signal['symbol']}/USDT</b>
• Price: ${signal.get('current_price', 0):.6f}
• Strength: {signal.get('strength', 'medium').title()}
• Reason: {signal.get('reasoning', 'Technical analysis')}

<b>📈 Indicators:</b>
• RSI: {signal.get('indicators', {}).get('rsi', 'N/A')}
• Price: ${signal.get('indicators', {}).get('price', 0):.6f}
            """
            
            # Send to all authorized users
            for user_id in self.config.telegram.authorized_users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=notification_text,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Error sending signal notification to {user_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error sending signal notification: {str(e)}")
    
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

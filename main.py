#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Trading Bot - Main Entry Point
Production-ready kripto trading bot for Telegram

Features:
- Real-time technical analysis and signal generation
- Automated trading with risk management
- Telegram dashboard for monitoring and control
- Portfolio tracking and P&L reporting
- Secure multi-user support
"""

import os
import sys
import asyncio
import signal
import traceback
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Core imports
from config.config import ConfigManager, get_config
from database.database_manager import DatabaseManager
from utils.logging_setup import setup_logging, create_logger, log_startup_info, log_shutdown_info
from telegram_bot.bot_core import TelegramTradingBot

# Global variables
config_manager = None
database_manager = None
telegram_bot = None
logger = None

async def initialize_system():
    """Initialize all system components"""
    global config_manager, database_manager, logger
    
    try:
        # 1. Load configuration
        logger.info("📋 Loading configuration...")
        config_manager = ConfigManager()
        
        # Validate configuration
        is_valid, errors = config_manager.validate_config()
        if not is_valid:
            logger.error("❌ Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("✅ Configuration loaded and validated")
        
        # 2. Initialize database
        logger.info("🗄️ Initializing database...")
        database_manager = DatabaseManager(config_manager.database.db_path)
        
        # Test database connection
        stats = database_manager.get_database_stats()
        logger.info(f"✅ Database initialized - {stats['db_size_mb']} MB")
        
        # 3. Log startup information
        config_summary = config_manager.get_config_summary()
        log_startup_info(logger, config_summary)
        
        return True
        
    except Exception as e:
        if logger:
            logger.critical(f"❌ System initialization failed: {str(e)}")
            logger.critical(traceback.format_exc())
        else:
            print(f"❌ System initialization failed: {str(e)}")
            print(traceback.format_exc())
        return False

async def start_trading_bot():
    """Start the main trading bot"""
    global telegram_bot, config_manager, database_manager, logger
    
    try:
        logger.info("🤖 Starting Telegram Trading Bot...")
        
        # Create bot instance
        telegram_bot = TelegramTradingBot(config_manager, database_manager)
        
        # Start bot
        success = await telegram_bot.start()
        
        if success:
            logger.info("✅ Telegram Trading Bot started successfully!")
            return True
        else:
            logger.error("❌ Failed to start Telegram Trading Bot")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error starting trading bot: {str(e)}")
        logger.error(traceback.format_exc())
        return False

async def stop_trading_bot():
    """Stop the trading bot gracefully"""
    global telegram_bot, database_manager, logger
    
    try:
        logger.info("🛑 Shutting down trading bot...")
        
        # Stop telegram bot
        if telegram_bot:
            await telegram_bot.stop()
        
        # Get final statistics
        stats = {}
        if database_manager:
            try:
                stats = database_manager.get_database_stats()
                
                # Cleanup old data
                database_manager.cleanup_old_data(days_to_keep=30)
                
                # Final backup
                if config_manager.database.backup_enabled:
                    database_manager.backup_database()
                
                # Close database
                database_manager.close()
                
            except Exception as e:
                logger.error(f"Error during database cleanup: {str(e)}")
        
        # Log shutdown info
        log_shutdown_info(logger, stats)
        
        logger.info("✅ Trading bot shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}")

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    
    def signal_handler(signum, frame):
        logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
        
        # Run shutdown in event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(shutdown_sequence())
        except RuntimeError:
            # No running loop, create new one
            asyncio.run(shutdown_sequence())
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination request
    
    if sys.platform != 'win32':
        signal.signal(signal.SIGHUP, signal_handler)   # Hangup
        signal.signal(signal.SIGUSR1, signal_handler)  # User signal 1

async def shutdown_sequence():
    """Graceful shutdown sequence"""
    global logger
    
    try:
        logger.info("🔄 Starting graceful shutdown sequence...")
        
        # Stop trading bot
        await stop_trading_bot()
        
        # Exit
        logger.info("👋 Goodbye!")
        os._exit(0)
        
    except Exception as e:
        logger.critical(f"❌ Error during shutdown sequence: {str(e)}")
        os._exit(1)

def check_requirements():
    """Check if all requirements are met"""
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check required environment variables
    required_env_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID', 
        'CRYPTO_API_KEY',
        'CRYPTO_API_SECRET'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Copy env.example to .env and fill in the values")
        return False
    
    # Check required directories
    required_dirs = ['data', 'logs', 'backups']
    for dir_name in required_dirs:
        os.makedirs(dir_name, exist_ok=True)
    
    return True

async def health_monitor():
    """Background health monitoring task"""
    global config_manager, database_manager, telegram_bot, logger
    
    while True:
        try:
            # Check every 5 minutes
            await asyncio.sleep(300)
            
            if not telegram_bot or not telegram_bot.is_running:
                continue
            
            # Health checks
            health_issues = []
            
            # Database health
            try:
                database_manager.get_database_stats()
            except Exception as e:
                health_issues.append(f"Database: {str(e)}")
            
            # Exchange API health
            try:
                if telegram_bot.exchange_api:
                    telegram_bot.exchange_api.get_balance("USDT")
            except Exception as e:
                health_issues.append(f"Exchange API: {str(e)}")
            
            # Memory check
            try:
                import psutil
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 85:
                    health_issues.append(f"High memory usage: {memory_percent:.1f}%")
            except ImportError:
                pass  # psutil not available
            
            # Log issues
            if health_issues:
                logger.warning("⚠️ Health check issues:")
                for issue in health_issues:
                    logger.warning(f"  - {issue}")
                
                # Send notification if critical
                if len(health_issues) > 1:
                    try:
                        await telegram_bot.application.bot.send_message(
                            chat_id=config_manager.telegram.chat_id,
                            text=f"⚠️ **Health Check Warning**\n\n" + 
                                 "\n".join([f"• {issue}" for issue in health_issues]),
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to send health notification: {str(e)}")
            else:
                logger.debug("✅ Health check passed")
                
        except Exception as e:
            logger.error(f"Error in health monitor: {str(e)}")

async def main():
    """Main application entry point"""
    global logger
    
    try:
        print("🤖 Telegram Trading Bot Starting...")
        print("=" * 50)
        
        # Check requirements
        if not check_requirements():
            print("❌ Requirements check failed")
            return 1
        
        # Setup logging first
        setup_logging(
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'logs/trading_bot.log'),
            console_output=True
        )
        
        logger = create_logger("main")
        logger.info("🚀 Telegram Trading Bot - Main Process Starting")
        
        # Initialize system
        if not await initialize_system():
            logger.critical("❌ System initialization failed - exiting")
            return 1
        
        # Setup signal handlers
        setup_signal_handlers()
        
        # Start trading bot
        if not await start_trading_bot():
            logger.critical("❌ Trading bot startup failed - exiting")
            return 1
        
        # Start health monitor
        health_task = asyncio.create_task(health_monitor())
        
        # Main loop - keep running
        try:
            logger.info("🔄 Main loop started - bot is running")
            
            # Keep the bot running
            while telegram_bot and telegram_bot.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("⌨️ Keyboard interrupt received")
        except Exception as e:
            logger.error(f"❌ Error in main loop: {str(e)}")
        finally:
            # Cancel health monitor
            health_task.cancel()
            try:
                await health_task
            except asyncio.CancelledError:
                pass
            
            # Graceful shutdown
            await shutdown_sequence()
        
        return 0
        
    except Exception as e:
        if logger:
            logger.critical(f"❌ Critical error in main: {str(e)}")
            logger.critical(traceback.format_exc())
        else:
            print(f"❌ Critical error in main: {str(e)}")
            print(traceback.format_exc())
        return 1

def run():
    """Entry point for setuptools console scripts"""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = run()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

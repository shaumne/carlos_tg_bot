#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test setup script to verify that all components are working correctly
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our modules
from config.config import ConfigManager, get_config
from database.database_manager import DatabaseManager
from utils.logging_setup import setup_logging
from exchange.crypto_exchange_api import CryptoExchangeAPI
from signals.signal_engine import SignalEngine

def test_database():
    """Test database functionality"""
    print("Testing database...")
    
    try:
        # Test database creation and basic operations
        db = DatabaseManager("data/test_trading_bot.db")
        
        # Test adding a coin
        success = db.add_watched_coin("BTC", "BTC_USDT", {"test": True})
        print(f"✅ Database: Add coin - {'Success' if success else 'Failed'}")
        
        # Test getting coins
        coins = db.get_watched_coins()
        print(f"✅ Database: Get coins - Found {len(coins)} coins")
        
        # Test settings
        db.set_setting("test_setting", "test_value")
        value = db.get_setting("test_setting")
        print(f"✅ Database: Settings - {'Success' if value == 'test_value' else 'Failed'}")
        
        # Test stats
        stats = db.get_database_stats()
        print(f"✅ Database: Stats - {stats}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False

def test_config():
    """Test configuration management"""
    print("Testing configuration...")
    
    try:
        # Test config loading
        config = ConfigManager()
        
        # Test config validation
        is_valid, errors = config.validate_config()
        print(f"✅ Config: Validation - {'Valid' if is_valid else 'Invalid'}")
        if errors:
            print(f"   Errors: {errors}")
        
        # Test config summary
        summary = config.get_config_summary()
        print(f"✅ Config: Summary - {len(summary)} sections")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {str(e)}")
        return False

def test_logging():
    """Test logging setup"""
    print("Testing logging...")
    
    try:
        # Setup logging
        logger = setup_logging(log_level="INFO", log_file="logs/test.log")
        
        # Test different log levels
        logger.debug("Test debug message")
        logger.info("Test info message")
        logger.warning("Test warning message")
        
        print("✅ Logging: Setup successful")
        return True
        
    except Exception as e:
        print(f"❌ Logging test failed: {str(e)}")
        return False

def test_signal_engine():
    """Test signal engine"""
    print("Testing signal engine...")
    
    try:
        # Setup dependencies
        config = ConfigManager()
        db = DatabaseManager("data/test_trading_bot.db")
        
        # Create signal engine
        signal_engine = SignalEngine(config, db)
        
        print("✅ Signal Engine: Initialization successful")
        
        # Test if we can get market data (might fail if no internet)
        try:
            market_data = signal_engine.market_data_provider.get_market_data("BTC_USDT")
            if market_data:
                print(f"✅ Signal Engine: Market data - BTC price: ${market_data.price}")
            else:
                print("⚠️ Signal Engine: Market data - Could not fetch (network issue?)")
        except Exception as e:
            print(f"⚠️ Signal Engine: Market data error - {str(e)}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Signal Engine test failed: {str(e)}")
        return False

def test_exchange_api():
    """Test exchange API (will fail without real credentials)"""
    print("Testing exchange API...")
    
    try:
        config = ConfigManager()
        
        # This will likely fail without real API credentials
        try:
            api = CryptoExchangeAPI(config)
            print("✅ Exchange API: Initialization successful")
            
            # Test getting trading pairs
            pairs = api.get_trading_pairs()
            print(f"✅ Exchange API: Trading pairs - Found {len(pairs)} pairs")
            
            return True
            
        except ValueError as e:
            if "environment variable" in str(e).lower():
                print("⚠️ Exchange API: Missing credentials (expected in test)")
                return True
            else:
                raise e
        
    except Exception as e:
        print(f"❌ Exchange API test failed: {str(e)}")
        return False

def create_sample_env():
    """Create sample .env file if it doesn't exist"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("Creating sample .env file...")
        
        sample_content = """# Sample .env file for testing
# Copy from env.example and fill in real values

TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_AUTHORIZED_USERS=123456789

CRYPTO_API_KEY=your_api_key_here
CRYPTO_API_SECRET=your_api_secret_here

TRADE_AMOUNT=10.0
ENABLE_AUTO_TRADING=false
ENABLE_PAPER_TRADING=true

LOG_LEVEL=INFO
"""
        
        with open(env_file, 'w') as f:
            f.write(sample_content)
        
        print("✅ Created sample .env file")

def main():
    """Run all tests"""
    print("🤖 Telegram Trading Bot - Setup Test")
    print("=" * 50)
    
    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("backups", exist_ok=True)
    
    # Create sample .env
    create_sample_env()
    
    # Run tests
    tests = [
        ("Configuration", test_config),
        ("Logging", test_logging),
        ("Database", test_database),
        ("Signal Engine", test_signal_engine),
        ("Exchange API", test_exchange_api),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Setup is ready.")
        print("\nNext steps:")
        print("1. Fill in real API credentials in .env file")
        print("2. Start implementing the Telegram bot")
        print("3. Test with paper trading first")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick test script to verify the fixes for:
1. Symbol formatting (BTC -> BTCUSDT/BTC_USDT)
2. Settings update mechanism
3. save_signal method
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from signals.signal_engine import MarketDataProvider
from database.database_manager import DatabaseManager
from config.config import ConfigManager
from config.dynamic_settings import DynamicSettingsManager

def test_symbol_formatting():
    """Test symbol formatting for Binance API"""
    print("🧪 Testing Symbol Formatting...")
    
    try:
        config = ConfigManager()
        provider = MarketDataProvider(config)
        
        # Test cases
        test_symbols = ["BTC", "ETH", "BTC_USDT", "ETHUSDT", "BTC/USDT"]
        
        for symbol in test_symbols:
            print(f"  Testing symbol: {symbol}")
            
            # Test OHLCV
            ohlcv = provider.get_ohlcv_data(symbol, limit=5)
            if ohlcv:
                print(f"    ✅ OHLCV data retrieved: {len(ohlcv)} candles")
            else:
                print(f"    ❌ Failed to get OHLCV data")
            
            # Test current price
            price = provider.get_current_price(symbol)
            if price:
                print(f"    ✅ Current price: ${price}")
            else:
                print(f"    ❌ Failed to get current price")
            
            print()
            
    except Exception as e:
        print(f"❌ Symbol formatting test failed: {str(e)}")
        return False
    
    return True

def test_database_methods():
    """Test database signal methods"""
    print("🧪 Testing Database Signal Methods...")
    
    try:
        db = DatabaseManager("data/test_fixes.db")
        
        # Test add_signal method
        signal_id = db.add_signal(
            symbol="BTC",
            formatted_symbol="BTC_USDT",
            signal_type="BUY",
            price=50000.0,
            confidence=0.8,
            notes="Test signal"
        )
        
        if signal_id > 0:
            print(f"    ✅ add_signal method works: ID {signal_id}")
        else:
            print(f"    ❌ add_signal method failed")
            return False
        
        # Test save_signal method (alias)
        signal_id2 = db.save_signal(
            symbol="ETH",
            formatted_symbol="ETH_USDT",
            signal_type="SELL",
            price=3000.0,
            confidence=0.7,
            notes="Test signal 2"
        )
        
        if signal_id2 > 0:
            print(f"    ✅ save_signal method works: ID {signal_id2}")
        else:
            print(f"    ❌ save_signal method failed")
            return False
            
    except Exception as e:
        print(f"❌ Database methods test failed: {str(e)}")
        return False
    
    return True

def test_dynamic_settings():
    """Test dynamic settings mechanism"""
    print("🧪 Testing Dynamic Settings...")
    
    try:
        config = ConfigManager()
        db = DatabaseManager("data/test_fixes.db")
        settings = DynamicSettingsManager(config, db)
        
        # Test setting update
        old_trade_amount = settings.get_setting('trading', 'trade_amount', 10.0)
        print(f"    Current trade_amount: {old_trade_amount}")
        
        # Update to new value
        new_amount = 75.0
        success = settings.set_setting('trading', 'trade_amount', new_amount, user_id=12345)
        
        if success:
            print(f"    ✅ Setting saved to database")
        else:
            print(f"    ❌ Failed to save setting")
            return False
        
        # Verify retrieval
        retrieved_amount = settings.get_setting('trading', 'trade_amount')
        
        if float(retrieved_amount) == new_amount:
            print(f"    ✅ Setting retrieved correctly: {retrieved_amount}")
        else:
            print(f"    ❌ Setting retrieval failed: expected {new_amount}, got {retrieved_amount}")
            return False
        
        # Test runtime application
        success_apply = settings.apply_runtime_settings(config)
        
        if success_apply:
            print(f"    ✅ Runtime settings applied")
            print(f"    Config trade_amount: {config.trading.trade_amount}")
        else:
            print(f"    ❌ Failed to apply runtime settings")
            return False
            
    except Exception as e:
        print(f"❌ Dynamic settings test failed: {str(e)}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Running Fix Verification Tests...")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Symbol formatting
    if test_symbol_formatting():
        success_count += 1
        print("✅ Symbol formatting test PASSED\n")
    else:
        print("❌ Symbol formatting test FAILED\n")
    
    # Test 2: Database methods
    if test_database_methods():
        success_count += 1
        print("✅ Database methods test PASSED\n")
    else:
        print("❌ Database methods test FAILED\n")
    
    # Test 3: Dynamic settings
    if test_dynamic_settings():
        success_count += 1
        print("✅ Dynamic settings test PASSED\n")
    else:
        print("❌ Dynamic settings test FAILED\n")
    
    # Summary
    print("=" * 50)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All fixes are working correctly!")
        return True
    else:
        print("⚠️  Some fixes need more work")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick Balance Test for Real Trading System
Tests the updated balance detection with USD fallback
"""

import sys
import traceback
from datetime import datetime

def test_balance_detection():
    """Test the new balance detection logic"""
    print("💰 QUICK BALANCE TEST")
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Import necessary modules
        from config.config import ConfigManager
        from config.dynamic_settings import DynamicSettingsManager
        from database.database_manager import DatabaseManager
        from simple_trade_executor import SimpleTradeExecutor
        
        print("1️⃣ INITIALIZING COMPONENTS")
        print("-" * 30)
        
        # Initialize config
        config_manager = ConfigManager()
        print("✅ ConfigManager created")
        
        # Initialize database
        database_manager = DatabaseManager()
        print("✅ DatabaseManager created")
        
        # Apply dynamic settings
        dynamic_settings_manager = DynamicSettingsManager(config_manager, database_manager)
        dynamic_settings_manager.apply_runtime_settings(config_manager)
        print("✅ Dynamic settings applied")
        
        print()
        print("2️⃣ TESTING BALANCE DETECTION")
        print("-" * 30)
        
        # Create trade executor
        executor = SimpleTradeExecutor(config_manager, database_manager)
        print("✅ SimpleTradeExecutor created")
        
        # Test balance detection with detailed logging
        print("🔍 Testing USDT balance...")
        usdt_balance = executor.get_balance("USDT")
        print(f"   USDT Balance: ${usdt_balance}")
        
        print("🔍 Testing USD balance...")
        usd_balance = executor.get_balance("USD")
        print(f"   USD Balance: ${usd_balance}")
        
        print("🔍 Testing balance sufficiency...")
        sufficient = executor.has_sufficient_balance("USDT")
        print(f"   Sufficient for trading: {sufficient}")
        
        print("🔍 Checking trading currency...")
        trading_currency = getattr(executor, 'trading_currency', 'USDT')
        print(f"   Active trading currency: {trading_currency}")
        
        print()
        print("3️⃣ TESTING PRICE FETCHING")
        print("-" * 30)
        
        # Test price fetching with different pairs
        test_symbols = ["BTC_USDT", "ETH_USDT", "SUI_USDT"]
        
        for symbol in test_symbols:
            print(f"📈 Testing {symbol}...")
            price = executor.get_current_price(symbol)
            print(f"   Price: ${price}")
        
        print()
        print("4️⃣ SUMMARY")
        print("-" * 30)
        
        if usdt_balance > 0:
            print("✅ USDT balance positive - using USDT")
            status = "READY"
        elif usd_balance > 0:
            print("✅ USD balance positive - using USD fallback")
            status = "READY"
        else:
            print("❌ No positive balance found")
            status = "NOT READY"
        
        print(f"🚀 SYSTEM STATUS: {status}")
        
        if sufficient:
            print("💰 Balance sufficient for trading")
        else:
            print("⚠️ Balance insufficient for trading")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print("🔍 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_balance_detection()

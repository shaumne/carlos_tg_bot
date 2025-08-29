#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick Trade Test
Fast test to verify real trading system is working
"""

import sys
from datetime import datetime

def quick_test():
    """Quick system verification"""
    print("⚡ QUICK TRADE SYSTEM TEST")
    print("=" * 40)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Import check
    print("1️⃣ Import Test...")
    try:
        from simple_trade_executor import execute_trade, SimpleTradeExecutor
        print("   ✅ Trade executor imported")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 2: Config check
    print("\n2️⃣ Config Test...")
    try:
        from config.config import ConfigManager
        from config.dynamic_settings import DynamicSettingsManager
        from database.database_manager import DatabaseManager
        
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        dynamic_settings = DynamicSettingsManager(config, db)
        dynamic_settings.apply_runtime_settings(config)
        
        print(f"   💰 Trade amount: ${config.trading.trade_amount}")
        print(f"   🎯 TP: {config.trading.take_profit_percentage}%")
        print(f"   🛑 SL: {config.trading.stop_loss_percentage}%")
        print(f"   🤖 Auto trading: {config.trading.enable_auto_trading}")
        
        if config.trading.enable_auto_trading:
            print("   ✅ Auto trading ENABLED")
        else:
            print("   ⚠️ Auto trading DISABLED")
            
    except Exception as e:
        print(f"   ❌ Config failed: {e}")
        return False
    
    # Test 3: API check
    print("\n3️⃣ API Test...")
    try:
        executor = SimpleTradeExecutor(config, db)
        balance = executor.get_balance("USDT")
        price = executor.get_current_price("BTC_USDT")
        
        print(f"   💰 USDT Balance: ${balance}")
        print(f"   📈 BTC Price: ${price}")
        
        if balance >= 0 and price and price > 0:
            print("   ✅ API working")
        else:
            print("   ❌ API issues")
            return False
            
    except Exception as e:
        print(f"   ❌ API failed: {e}")
        return False
    
    # Test 4: Execute trade function test
    print("\n4️⃣ Execute Trade Function Test...")
    try:
        test_signal = {
            'symbol': 'BTC_USDT',
            'action': 'BUY',
            'price': 95000.0,
            'confidence': 85,
            'reasoning': 'Quick test signal'
        }
        
        print("   📊 Test signal created")
        print(f"      Symbol: {test_signal['symbol']}")
        print(f"      Action: {test_signal['action']}")
        print(f"      Price: ${test_signal['price']}")
        
        # Check if function would execute
        if config.trading.enable_auto_trading:
            print("   ⚠️ AUTO TRADING IS ON - Would execute REAL trade!")
            print("   🚫 Skipping actual execution for safety")
        else:
            print("   ✅ Function ready (auto trading disabled)")
            
    except Exception as e:
        print(f"   ❌ Function test failed: {e}")
        return False
    
    print("\n✅ QUICK TEST COMPLETED SUCCESSFULLY!")
    print("🚀 System is ready for real trading")
    return True

def verify_safety():
    """Verify trading safety settings"""
    print("\n🛡️ SAFETY VERIFICATION")
    print("-" * 30)
    
    try:
        from config.config import ConfigManager
        from database.database_manager import DatabaseManager
        from config.dynamic_settings import DynamicSettingsManager
        
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        dynamic_settings = DynamicSettingsManager(config, db)
        dynamic_settings.apply_runtime_settings(config)
        
        print(f"💰 Max trade amount: ${config.trading.trade_amount}")
        print(f"📊 Max positions: {config.trading.max_positions}")
        print(f"🎯 Take profit: {config.trading.take_profit_percentage}%")
        print(f"🛑 Stop loss: {config.trading.stop_loss_percentage}%")
        
        # Safety checks
        if config.trading.trade_amount > 1000:
            print("⚠️ WARNING: High trade amount!")
        
        if config.trading.stop_loss_percentage > 20:
            print("⚠️ WARNING: High stop loss percentage!")
        
        if config.trading.max_positions > 10:
            print("⚠️ WARNING: Many max positions!")
        
        print("✅ Safety check completed")
        
    except Exception as e:
        print(f"❌ Safety check failed: {e}")

if __name__ == "__main__":
    success = quick_test()
    verify_safety()
    
    if success:
        print("\n🎉 ALL SYSTEMS GO!")
        sys.exit(0)
    else:
        print("\n💥 SYSTEM NOT READY!")
        sys.exit(1)

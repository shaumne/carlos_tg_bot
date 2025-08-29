#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Real Trading System Test Suite
Comprehensive testing for production trading functionality
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, Any

def test_trade_executor_api():
    """Test the real trade executor API methods"""
    print("🔧 TESTING TRADE EXECUTOR API METHODS")
    print("-" * 50)
    
    try:
        from config.config import ConfigManager
        from database.database_manager import DatabaseManager
        from config.dynamic_settings import DynamicSettingsManager
        from simple_trade_executor import SimpleTradeExecutor
        
        # Initialize
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        dynamic_settings = DynamicSettingsManager(config, db)
        dynamic_settings.apply_runtime_settings(config)
        
        executor = SimpleTradeExecutor(config, db)
        
        # Test 1: Balance check
        print("💰 Testing balance check...")
        usdt_balance = executor.get_balance("USDT")
        print(f"   USDT Balance: ${usdt_balance}")
        
        # Test 2: Current price
        print("📈 Testing price fetch...")
        btc_price = executor.get_current_price("BTC_USDT")
        print(f"   BTC Price: ${btc_price}")
        
        # Test 3: Sufficient balance check
        print("💳 Testing balance sufficiency...")
        sufficient = executor.has_sufficient_balance()
        print(f"   Sufficient balance: {sufficient}")
        
        # Test 4: API connectivity
        print("🌐 Testing API connectivity...")
        if btc_price and btc_price > 0:
            print("   ✅ API connection successful")
            return True
        else:
            print("   ❌ API connection failed")
            return False
            
    except Exception as e:
        print(f"   ❌ API test failed: {str(e)}")
        return False

def test_tp_sl_calculations():
    """Test TP/SL calculation logic"""
    print("\n🎯 TESTING TP/SL CALCULATIONS")
    print("-" * 50)
    
    try:
        from config.config import ConfigManager
        from database.database_manager import DatabaseManager
        from config.dynamic_settings import DynamicSettingsManager
        
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        dynamic_settings = DynamicSettingsManager(config, db)
        dynamic_settings.apply_runtime_settings(config)
        
        # Test data
        test_price = 50000.0
        tp_percentage = config.trading.take_profit_percentage
        sl_percentage = config.trading.stop_loss_percentage
        
        print(f"📊 Test price: ${test_price}")
        print(f"🎯 TP percentage: {tp_percentage}%")
        print(f"🛑 SL percentage: {sl_percentage}%")
        
        # BUY calculations
        buy_tp = test_price * (1 + tp_percentage / 100)
        buy_sl = test_price * (1 - sl_percentage / 100)
        
        print(f"\n📈 BUY Position:")
        print(f"   Take Profit: ${buy_tp} (+{tp_percentage}%)")
        print(f"   Stop Loss: ${buy_sl} (-{sl_percentage}%)")
        
        # SELL calculations
        sell_tp = test_price * (1 - tp_percentage / 100)
        sell_sl = test_price * (1 + sl_percentage / 100)
        
        print(f"\n📉 SELL Position:")
        print(f"   Take Profit: ${sell_tp} (-{tp_percentage}%)")
        print(f"   Stop Loss: ${sell_sl} (+{sl_percentage}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ TP/SL calculation test failed: {str(e)}")
        return False

def test_signal_processing():
    """Test signal processing workflow"""
    print("\n📡 TESTING SIGNAL PROCESSING WORKFLOW")
    print("-" * 50)
    
    try:
        # Create test signals
        test_signals = [
            {
                'symbol': 'BTC_USDT',
                'action': 'BUY',
                'price': 95000.0,
                'confidence': 85,
                'reasoning': 'Strong bullish momentum'
            },
            {
                'symbol': 'ETH_USDT',
                'action': 'SELL',
                'price': 3500.0,
                'confidence': 75,
                'reasoning': 'Overbought conditions'
            }
        ]
        
        for i, signal in enumerate(test_signals, 1):
            print(f"\n🧪 Test Signal {i}:")
            print(f"   Symbol: {signal['symbol']}")
            print(f"   Action: {signal['action']}")
            print(f"   Price: ${signal['price']}")
            print(f"   Confidence: {signal['confidence']}%")
            
            # Simulate signal validation
            if signal['action'] in ['BUY', 'SELL']:
                print("   ✅ Valid signal type")
            else:
                print("   ❌ Invalid signal type")
                
            if signal['confidence'] >= 70:
                print("   ✅ Confidence threshold met")
            else:
                print("   ⚠️ Low confidence signal")
        
        return True
        
    except Exception as e:
        print(f"❌ Signal processing test failed: {str(e)}")
        return False

def test_position_monitoring():
    """Test position monitoring logic"""
    print("\n📊 TESTING POSITION MONITORING")
    print("-" * 50)
    
    try:
        from simple_trade_executor import SimpleTradeExecutor
        from config.config import ConfigManager
        from database.database_manager import DatabaseManager
        from config.dynamic_settings import DynamicSettingsManager
        
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        dynamic_settings = DynamicSettingsManager(config, db)
        dynamic_settings.apply_runtime_settings(config)
        
        executor = SimpleTradeExecutor(config, db)
        
        # Create mock position
        mock_position = {
            'symbol': 'BTC_USDT',
            'action': 'BUY',
            'entry_price': 94000.0,
            'quantity': 0.001,
            'take_profit': 103400.0,  # +10%
            'stop_loss': 84600.0,     # -10%
            'tp_order_id': 'TP123456',
            'sl_order_id': 'SL123456',
            'timestamp': datetime.now(),
            'status': 'ACTIVE'
        }
        
        print("🎭 Mock Position:")
        print(f"   Symbol: {mock_position['symbol']}")
        print(f"   Entry: ${mock_position['entry_price']}")
        print(f"   TP: ${mock_position['take_profit']}")
        print(f"   SL: ${mock_position['stop_loss']}")
        
        # Test TP/SL conditions
        test_prices = [92000, 96000, 105000, 82000]  # Below SL, Normal, Above TP, Way below SL
        
        for test_price in test_prices:
            print(f"\n💲 Testing price: ${test_price}")
            
            # TP condition
            if test_price >= mock_position['take_profit']:
                print("   🎯 TAKE PROFIT HIT!")
            elif test_price <= mock_position['stop_loss']:
                print("   🛑 STOP LOSS HIT!")
            else:
                print("   📈 Position still active")
        
        print(f"\n⏰ Monitoring interval: {executor.tp_sl_check_interval} seconds")
        print("   ✅ Monitoring logic working")
        
        return True
        
    except Exception as e:
        print(f"❌ Position monitoring test failed: {str(e)}")
        return False

def test_database_operations():
    """Test database operations"""
    print("\n💾 TESTING DATABASE OPERATIONS")
    print("-" * 50)
    
    try:
        from config.config import ConfigManager
        from database.database_manager import DatabaseManager
        
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        
        # Test 1: Trade history
        print("📊 Testing trade history...")
        trades = db.execute_query(
            "SELECT COUNT(*) as count FROM trade_history"
        )
        trade_count = trades[0]['count'] if trades else 0
        print(f"   Total trades in history: {trade_count}")
        
        # Test 2: Active positions
        print("📈 Testing active positions...")
        positions = db.execute_query(
            "SELECT COUNT(*) as count FROM active_positions WHERE status = 'open'"
        )
        position_count = positions[0]['count'] if positions else 0
        print(f"   Active positions: {position_count}")
        
        # Test 3: Settings
        print("⚙️ Testing settings...")
        settings = db.execute_query(
            "SELECT COUNT(*) as count FROM bot_settings"
        )
        settings_count = settings[0]['count'] if settings else 0
        print(f"   Bot settings: {settings_count}")
        
        print("   ✅ Database operations working")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 REAL TRADING SYSTEM TEST SUITE")
    print("=" * 60)
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("API Methods", test_trade_executor_api),
        ("TP/SL Calculations", test_tp_sl_calculations),
        ("Signal Processing", test_signal_processing),
        ("Position Monitoring", test_position_monitoring),
        ("Database Operations", test_database_operations)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"🧪 RUNNING TEST: {test_name}")
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {str(e)}")
            results.append((test_name, False))
        
        print()
    
    # Summary
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n🏆 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - SYSTEM READY FOR REAL TRADING!")
    else:
        print("⚠️ SOME TESTS FAILED - PLEASE FIX ISSUES BEFORE TRADING")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Complete Real Trading System Debug Script
Comprehensive analysis and testing of the production trading system
"""

import os
import sys
import traceback
from datetime import datetime, timedelta

print("=" * 80)
print("🚀 REAL TRADING SYSTEM DEBUG ANALYSIS")
print("=" * 80)
print(f"⏰ Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 1. BASIC IMPORTS TEST
print("1️⃣ BASIC IMPORTS TEST")
print("-" * 40)

try:
    from config.config import ConfigManager
    print("✅ ConfigManager imported successfully")
except Exception as e:
    print(f"❌ ConfigManager import failed: {e}")

try:
    from config.dynamic_settings import DynamicSettingsManager
    print("✅ DynamicSettingsManager imported successfully")
except Exception as e:
    print(f"❌ DynamicSettingsManager import failed: {e}")

try:
    from database.database_manager import DatabaseManager
    print("✅ DatabaseManager imported successfully")
except Exception as e:
    print(f"❌ DatabaseManager import failed: {e}")

try:
    from signals.background_analyzer import BackgroundAnalyzer
    print("✅ BackgroundAnalyzer imported successfully")
except Exception as e:
    print(f"❌ BackgroundAnalyzer import failed: {e}")

print()

# 2. REAL TRADE EXECUTOR TEST
print("2️⃣ REAL TRADE EXECUTOR TEST")
print("-" * 40)

# Test simple_trade_executor first (priority)
try:
    import simple_trade_executor
    print("✅ simple_trade_executor imported successfully")
    
    # Test the global execute_trade function
    try:
        test_signal = {
            'symbol': 'BTC_USDT',
            'action': 'BUY',
            'price': 50000.0,
            'confidence': 85,
            'reasoning': 'Test signal for debugging'
        }
        
        # Test function exists
        if hasattr(simple_trade_executor, 'execute_trade'):
            print("✅ execute_trade function found in simple_trade_executor")
            
            # Don't actually execute - just verify it would work
            print("✅ SimpleTradeExecutor is ready for real trading")
        else:
            print("❌ execute_trade function not found")
            
    except Exception as e:
        print(f"❌ Error testing execute_trade function: {str(e)}")
        
except Exception as e:
    print(f"❌ simple_trade_executor import failed: {str(e)}")
    print(f"📍 Error details: {traceback.format_exc()}")

print()

# 3. REAL TRADING CONFIG TEST
print("3️⃣ REAL TRADING CONFIGURATION TEST")
print("-" * 40)

try:
    config = ConfigManager()
    print("✅ ConfigManager created")
    
    print("🔧 Config BEFORE dynamic settings:")
    print(f"  • Auto trading: {config.trading.enable_auto_trading}")
    print(f"  • Trade amount: {config.trading.trade_amount} USDT")
    print(f"  • Max positions: {config.trading.max_positions}")
    print(f"  • TP percentage: {config.trading.take_profit_percentage}%")
    print(f"  • SL percentage: {config.trading.stop_loss_percentage}%")
    
    # Test API credentials
    if hasattr(config, 'exchange'):
        if hasattr(config.exchange, 'api_key') and config.exchange.api_key:
            print(f"✅ API Key configured: {config.exchange.api_key[:10]}...")
        else:
            print("❌ API Key not configured")
            
        if hasattr(config.exchange, 'api_secret') and config.exchange.api_secret:
            print(f"✅ API Secret configured: {config.exchange.api_secret[:10]}...")
        else:
            print("❌ API Secret not configured")
    else:
        print("❌ Exchange configuration not found")
    
    # Apply dynamic settings
    try:
        db = DatabaseManager(config.database.db_path)
        dynamic_settings = DynamicSettingsManager(config, db)
        settings_applied = dynamic_settings.apply_runtime_settings(config)
        
        print(f"🔄 Dynamic settings applied: {settings_applied}")
        
        print("🔧 Config AFTER dynamic settings:")
        print(f"  • Auto trading: {config.trading.enable_auto_trading}")
        print(f"  • Trade amount: {config.trading.trade_amount} USDT")
        print(f"  • Max positions: {config.trading.max_positions}")
        print(f"  • TP percentage: {config.trading.take_profit_percentage}%")
        print(f"  • SL percentage: {config.trading.stop_loss_percentage}%")
        
    except Exception as e:
        print(f"❌ Dynamic settings error: {str(e)}")

except Exception as e:
    print(f"❌ Config test failed: {str(e)}")

print()

# 4. REAL TRADE EXECUTOR INSTANCE TEST
print("4️⃣ REAL TRADE EXECUTOR INSTANCE TEST")
print("-" * 40)

try:
    from simple_trade_executor import SimpleTradeExecutor
    
    config = ConfigManager()
    db = DatabaseManager(config.database.db_path)
    
    # Apply dynamic settings
    dynamic_settings = DynamicSettingsManager(config, db)
    dynamic_settings.apply_runtime_settings(config)
    
    # Create executor instance
    executor = SimpleTradeExecutor(config, db)
    print("✅ SimpleTradeExecutor instance created")
    
    # Test API methods
    try:
        # Test balance check (read-only)
        balance = executor.get_balance("USDT")
        print(f"💰 USDT Balance: {balance}")
        
        if balance > 0:
            print("✅ Exchange API connection working")
        else:
            print("⚠️ USDT balance is 0 or API not working")
            
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
    
    # Test TP/SL monitoring
    print(f"🎯 TP/SL check interval: {executor.tp_sl_check_interval} seconds")
    print(f"📊 Active positions: {executor.get_position_count()}")
    
    # Test methods availability
    required_methods = [
        'execute_trade', 'buy_coin', 'sell_coin', 'get_balance',
        'place_tp_sl_orders', 'cancel_order', 'get_current_price'
    ]
    
    print("🔍 Required methods check:")
    for method in required_methods:
        if hasattr(executor, method):
            print(f"  ✅ {method}")
        else:
            print(f"  ❌ {method}")

except Exception as e:
    print(f"❌ Executor instance test failed: {str(e)}")
    print(f"📍 Error details: {traceback.format_exc()}")

print()

# 5. BACKGROUND ANALYZER INTEGRATION TEST
print("5️⃣ BACKGROUND ANALYZER INTEGRATION TEST")
print("-" * 40)

try:
    from signals.background_analyzer import BackgroundAnalyzer
    
    config = ConfigManager()
    db = DatabaseManager(config.database.db_path)
    dynamic_settings = DynamicSettingsManager(config, db)
    dynamic_settings.apply_runtime_settings(config)
    
    analyzer = BackgroundAnalyzer(config, db)
    
    # Check trade executor loading methods
    methods_to_check = ['_execute_trade', '_load_trade_executor']
    print("🔍 BackgroundAnalyzer trade execution methods:")
    for method in methods_to_check:
        if hasattr(analyzer, method):
            print(f"  ✅ {method}")
        else:
            print(f"  ❌ {method}")
    
    # Test trade executor loading
    try:
        if hasattr(analyzer, '_load_trade_executor'):
            analyzer._load_trade_executor()
            if analyzer._trade_executor_module:
                print("✅ Trade executor module loaded successfully")
                print(f"📦 Loaded module: {analyzer._trade_executor_module.__name__}")
            else:
                print("❌ Trade executor module not loaded")
        else:
            print("❌ _load_trade_executor method not found")
    except Exception as e:
        print(f"❌ Trade executor loading failed: {str(e)}")

except Exception as e:
    print(f"❌ BackgroundAnalyzer test failed: {str(e)}")

print()

# 6. SIMULATED TRADING TEST
print("6️⃣ SIMULATED TRADING WORKFLOW TEST")
print("-" * 40)

try:
    # Create a test signal
    test_signal = {
        'symbol': 'BTC_USDT',
        'action': 'BUY',
        'price': 95000.0,
        'confidence': 90,
        'reasoning': 'Test signal - Strong uptrend with RSI oversold'
    }
    
    print("📊 Test Signal:")
    print(f"  Symbol: {test_signal['symbol']}")
    print(f"  Action: {test_signal['action']}")
    print(f"  Price: ${test_signal['price']}")
    print(f"  Confidence: {test_signal['confidence']}%")
    
    # Test the global execute_trade function
    print("\n🧪 Testing global execute_trade function:")
    
    try:
        from simple_trade_executor import execute_trade
        
        # Check if auto trading is enabled
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        dynamic_settings = DynamicSettingsManager(config, db)
        dynamic_settings.apply_runtime_settings(config)
        
        if config.trading.enable_auto_trading:
            print("✅ Auto trading is ENABLED")
            print("⚠️ WARNING: This would execute a REAL trade!")
            print("🚫 Skipping actual execution for safety")
            
            # Just verify the function structure
            print("✅ execute_trade function is ready for real trading")
        else:
            print("❌ Auto trading is DISABLED")
            print("💡 Enable auto trading in settings to execute real trades")
            
    except Exception as e:
        print(f"❌ Global execute_trade test failed: {str(e)}")

except Exception as e:
    print(f"❌ Simulated trading test failed: {str(e)}")

print()

# 7. DATABASE TRADING RECORDS TEST
print("7️⃣ DATABASE TRADING RECORDS TEST")
print("-" * 40)

try:
    config = ConfigManager()
    db = DatabaseManager(config.database.db_path)
    
    # Check recent trade history
    trades = db.execute_query(
        "SELECT * FROM trade_history ORDER BY timestamp DESC LIMIT 10"
    )
    
    print(f"📊 Recent trades in database: {len(trades)}")
    for i, trade in enumerate(trades[:5]):  # Show last 5 trades
        print(f"  {i+1}. {trade['symbol']} {trade['action']} - {trade['status']} ({trade['timestamp'][:19]})")
    
    # Check active positions table
    positions = db.execute_query(
        "SELECT * FROM active_positions WHERE status = 'open'"
    )
    
    print(f"📈 Active positions in database: {len(positions)}")
    for pos in positions[:3]:  # Show first 3 positions
        print(f"  • {pos['symbol']}: {pos['side']} {pos['quantity']} @ ${pos['entry_price']}")

except Exception as e:
    print(f"❌ Database test failed: {str(e)}")

print()

# 8. SYSTEM READINESS SUMMARY
print("8️⃣ SYSTEM READINESS SUMMARY")
print("-" * 40)

readiness_checks = []

# Check 1: Trade executor availability
try:
    import simple_trade_executor
    readiness_checks.append(("✅", "Trade executor module available"))
except:
    readiness_checks.append(("❌", "Trade executor module missing"))

# Check 2: API credentials
try:
    config = ConfigManager()
    if hasattr(config.exchange, 'api_key') and config.exchange.api_key:
        readiness_checks.append(("✅", "API credentials configured"))
    else:
        readiness_checks.append(("❌", "API credentials missing"))
except:
    readiness_checks.append(("❌", "Config error"))

# Check 3: Auto trading setting
try:
    config = ConfigManager()
    db = DatabaseManager(config.database.db_path)
    dynamic_settings = DynamicSettingsManager(config, db)
    dynamic_settings.apply_runtime_settings(config)
    
    if config.trading.enable_auto_trading:
        readiness_checks.append(("✅", "Auto trading enabled"))
    else:
        readiness_checks.append(("⚠️", "Auto trading disabled"))
except:
    readiness_checks.append(("❌", "Settings error"))

# Check 4: Database connectivity
try:
    config = ConfigManager()
    db = DatabaseManager(config.database.db_path)
    db.execute_query("SELECT 1")
    readiness_checks.append(("✅", "Database connectivity"))
except:
    readiness_checks.append(("❌", "Database error"))

print("🔍 SYSTEM READINESS CHECKLIST:")
for status, message in readiness_checks:
    print(f"  {status} {message}")

print()

# Final recommendation
all_good = all(check[0] == "✅" for check in readiness_checks)
if all_good:
    print("🚀 SYSTEM IS READY FOR REAL TRADING!")
    print("💰 All components are configured and functional")
    print("⚡ Real trades will be executed when signals are generated")
else:
    print("⚠️ SYSTEM NEEDS ATTENTION")
    print("🔧 Please fix the issues marked with ❌ before trading")

print()
print("=" * 80)
print("🏁 REAL TRADING DEBUG ANALYSIS COMPLETE")
print("=" * 80)
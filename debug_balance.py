#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Balance Debug Script
Detailed analysis of Crypto.com Exchange account balances
"""

import json
from datetime import datetime

def debug_accounts():
    """Debug all account types and balances"""
    print("💰 CRYPTO.COM BALANCE DEBUG")
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
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
        
        print("1️⃣ ACCOUNT SUMMARY API")
        print("-" * 30)
        
        # Raw API call to get-account-summary
        response = executor.send_request("private/get-account-summary", {})
        
        if response.get("code") == 0:
            result = response.get("result", {})
            accounts = result.get("accounts", [])
            
            print(f"📊 Found {len(accounts)} accounts:")
            print()
            
            for i, account in enumerate(accounts, 1):
                currency = account.get("currency", "Unknown")
                available = account.get("available", 0)
                balance = account.get("balance", 0)
                frozen = account.get("frozen", 0)
                balance_type = account.get("balance_type", "unknown")
                
                print(f"Account {i}:")
                print(f"  💱 Currency: {currency}")
                print(f"  💰 Available: {available}")
                print(f"  🏦 Total Balance: {balance}")
                print(f"  🧊 Frozen: {frozen}")
                print(f"  📋 Type: {balance_type}")
                print()
                
                # Focus on USDT
                if currency == "USDT":
                    print(f"  🎯 USDT DETAILS:")
                    print(f"     Available: {available}")
                    print(f"     Balance Type: {balance_type}")
                    if float(available) < 0:
                        print(f"     ⚠️ NEGATIVE BALANCE - This might be MARGIN account")
                    else:
                        print(f"     ✅ POSITIVE BALANCE - This might be SPOT account")
                    print()
        else:
            print(f"❌ API Error: {response.get('code')} - {response.get('message', 'Unknown')}")
        
        print("\n2️⃣ ALTERNATIVE ACCOUNTS API")
        print("-" * 30)
        
        # Try alternative API
        response2 = executor.send_request("private/get-accounts", {})
        
        if response2.get("code") == 0:
            accounts2 = response2.get("result", {}).get("accounts", [])
            
            print(f"📊 Found {len(accounts2)} accounts via alternative API:")
            print()
            
            for i, account in enumerate(accounts2, 1):
                account_type = account.get("account_type", "unknown")
                balances = account.get("balances", [])
                
                print(f"Account {i}:")
                print(f"  📋 Account Type: {account_type}")
                print(f"  💰 Balances ({len(balances)}):")
                
                for balance in balances:
                    currency = balance.get("currency", "Unknown")
                    available = balance.get("available", 0)
                    balance_total = balance.get("balance", 0)
                    
                    if currency == "USDT" or float(available) > 0:
                        print(f"     {currency}: {available} (total: {balance_total})")
                print()
        else:
            print(f"❌ Alternative API Error: {response2.get('code')} - {response2.get('message', 'Unknown')}")
        
        print("\n3️⃣ BALANCE TEST RESULTS")
        print("-" * 30)
        
        # Test our balance methods
        primary_balance = executor.get_balance("USDT")
        spot_balance = executor.get_spot_balance("USDT")
        sufficient = executor.has_sufficient_balance("USDT")
        
        print(f"🔧 Primary balance method: ${primary_balance}")
        print(f"🔧 Spot balance method: ${spot_balance}")
        print(f"🔧 Sufficient balance: {sufficient}")
        print(f"🔧 Required minimum: ${executor.min_balance_required}")
        
        print("\n4️⃣ RECOMMENDATIONS")
        print("-" * 30)
        
        if primary_balance < 0:
            print("⚠️ NEGATIVE balance detected - This is likely MARGIN account")
            print("💡 Suggestion: Check if you have separate SPOT account")
            print("🔧 Action: Transfer funds from margin to spot if needed")
        elif primary_balance == 0:
            print("⚠️ ZERO balance detected")
            print("💡 Suggestion: Deposit USDT to spot account for trading")
        else:
            print("✅ POSITIVE balance detected")
            print("🚀 Ready for trading!")
        
        if spot_balance > 0 and spot_balance != primary_balance:
            print(f"💡 Alternative API found different balance: ${spot_balance}")
            print("🔧 Using alternative API might be better")
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        print(f"📍 Details: {traceback.format_exc()}")

if __name__ == "__main__":
    debug_accounts()

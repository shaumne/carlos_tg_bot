#!/usr/bin/env python3
"""
🔍 BALANCE DEBUG KODU
====================
Bu kod tüm hesap detaylarını listeler
"""

import logging
import sys
from datetime import datetime

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Balance debug"""
    
    print(f"""
{'='*80}
🔍 BALANCE DEBUG KODU
{'='*80}
⏰ Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Bu kod tüm hesap detaylarınızı listeler
""")
    
    try:
        # Import our modules
        from config.config import ConfigManager
        from config.dynamic_settings import DynamicSettingsManager
        from database.database_manager import DatabaseManager
        import simple_trade_executor
        
        # Initialize
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        settings = DynamicSettingsManager(config, db)
        settings.apply_runtime_settings(config)
        
        # Create executor
        executor = simple_trade_executor.SimpleTradeExecutor(config, db)
        
        print(f"🔗 API bağlantısı test ediliyor...")
        
        # Call the API directly to see all accounts
        method = "private/get-account-summary"
        params = {}
        
        response = executor.send_request(method, params)
        
        print(f"📊 API Response:")
        print(f"   • Code: {response.get('code')}")
        print(f"   • Message: {response.get('message', 'N/A')}")
        
        if response.get("code") == 0:
            result = response.get("result", {})
            accounts = result.get("accounts", [])
            
            print(f"\n📋 HESAP DETAYLARI ({len(accounts)} hesap bulundu):")
            print(f"{'='*80}")
            
            for i, account in enumerate(accounts, 1):
                currency = account.get("currency", "UNKNOWN")
                available = account.get("available", 0)
                balance_type = account.get("balance_type", "unknown")
                
                print(f"Hesap {i}:")
                print(f"   • Currency: {currency}")
                print(f"   • Available: {available}")
                print(f"   • Balance Type: {balance_type}")
                print(f"   • Positive: {'✅' if float(available) > 0 else '❌'}")
                print(f"   • Raw Data: {account}")
                print()
            
            # Specific balance checks
            print(f"{'='*80}")
            print(f"💰 SPECIFIC BALANCE CHECKS:")
            print(f"{'='*80}")
            
            currencies_to_check = ["USDT", "USD", "USDC"]
            
            for currency in currencies_to_check:
                balance = executor.get_balance(currency)
                print(f"   • {currency}: ${balance}")
            
            # Check trading currency setting
            print(f"\n🎯 TRADING CURRENCY:")
            if hasattr(executor, 'trading_currency'):
                print(f"   • Current: {executor.trading_currency}")
            else:
                print(f"   • Not set")
            
        else:
            print(f"❌ API error: {response.get('message', 'Unknown error')}")
            
        # Try alternative API endpoint
        print(f"\n{'='*80}")
        print(f"🔄 ALTERNATIVE API ENDPOINT TEST:")
        print(f"{'='*80}")
        
        method2 = "private/get-accounts"
        response2 = executor.send_request(method2, {})
        
        print(f"📊 Alternative API Response:")
        print(f"   • Code: {response2.get('code')}")
        print(f"   • Message: {response2.get('message', 'N/A')}")
        
        if response2.get("code") == 0:
            accounts2 = response2.get("result", {}).get("accounts", [])
            print(f"   • Found {len(accounts2)} accounts")
            
            for account in accounts2:
                account_type = account.get("account_type", "")
                balances = account.get("balances", [])
                print(f"   📝 Account Type: {account_type}")
                
                for balance in balances:
                    currency = balance.get("currency")
                    available = balance.get("available", 0)
                    print(f"      • {currency}: {available}")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to check available trading instruments and format validation
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import ConfigManager
from exchange.crypto_exchange_api import CryptoExchangeAPI

def test_instruments():
    """Test instrument formatting and validation"""
    print("🧪 Testing Instrument Name Formatting...")
    
    try:
        config = ConfigManager()
        exchange_api = CryptoExchangeAPI(config)
        
        # Test symbols
        test_symbols = ["ALGO", "BTC", "ETH", "ALGO_USDT", "ALGOUSDT"]
        
        print("\n📋 Getting available trading pairs...")
        available_pairs = exchange_api.get_trading_pairs()
        print(f"Total available pairs: {len(available_pairs)}")
        
        # Filter for ALGO
        algo_pairs = [pair for pair in available_pairs if 'ALGO' in pair.upper()]
        print(f"ALGO related pairs: {algo_pairs}")
        
        # Show first 20 pairs for reference
        print(f"\nFirst 20 available pairs:")
        for i, pair in enumerate(available_pairs[:20]):
            print(f"  {i+1}: {pair}")
        
        print("\n🔍 Testing symbol formatting...")
        for symbol in test_symbols:
            print(f"\nTesting symbol: {symbol}")
            formatted = exchange_api._format_instrument_name(symbol)
            if formatted:
                print(f"  ✅ Formatted to: {formatted}")
                # Test validation
                is_valid = exchange_api.validate_instrument(formatted)
                print(f"  📊 Validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
            else:
                print(f"  ❌ Could not format symbol: {symbol}")
        
        print("\n" + "="*50)
        print("📊 Instrument Test Results Complete!")
        
    except Exception as e:
        print(f"❌ Error in instrument test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_instruments()

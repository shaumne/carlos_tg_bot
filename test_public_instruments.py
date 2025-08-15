#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to check available trading instruments from public API
"""

import requests
import json

def test_public_instruments():
    """Test public instruments endpoint"""
    print("🧪 Testing Public Instruments API...")
    
    try:
        # Public endpoint for instruments
        url = "https://api.crypto.com/v2/public/get-instruments"
        
        print(f"📡 Calling: {url}")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("code") == 0:
                instruments = data.get("result", {}).get("data", [])
                print(f"✅ Found {len(instruments)} instruments")
                
                # Filter for USDT pairs
                usdt_pairs = []
                algo_pairs = []
                
                for instrument in instruments:
                    inst_name = instrument.get("instrument_name", "")
                    quote_currency = instrument.get("quote_currency", "")
                    base_currency = instrument.get("base_currency", "")
                    
                    # Look for USDT pairs
                    if quote_currency == "USDT":
                        usdt_pairs.append(inst_name)
                        
                        # Look for ALGO specifically
                        if "ALGO" in base_currency.upper():
                            algo_pairs.append(inst_name)
                            print(f"🎯 Found ALGO pair: {inst_name} (base: {base_currency}, quote: {quote_currency})")
                
                print(f"\n📊 Total USDT pairs: {len(usdt_pairs)}")
                print(f"🎯 ALGO pairs: {algo_pairs}")
                
                # Show first 20 USDT pairs for reference
                print(f"\nFirst 20 USDT pairs:")
                for i, pair in enumerate(usdt_pairs[:20]):
                    print(f"  {i+1}: {pair}")
                
                # Look for specific coins
                test_coins = ["BTC", "ETH", "ALGO", "DOGE", "SOL"]
                print(f"\n🔍 Looking for specific coins:")
                for coin in test_coins:
                    matches = [pair for pair in usdt_pairs if pair.startswith(coin)]
                    print(f"  {coin}: {matches}")
                
            else:
                print(f"❌ API Error: {data.get('message', 'Unknown error')}")
                
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
        
        print("\n" + "="*50)
        print("📊 Public Instrument Test Complete!")
        
    except Exception as e:
        print(f"❌ Error in public instrument test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_public_instruments()

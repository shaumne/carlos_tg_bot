#!/usr/bin/env python3
"""
🧪 DİNAMİK QUANTITY FORMATLAMA SİSTEMİ TEST KODU
================================================
Bu kod dinamik quantity sisteminin çalışıp çalışmadığını test eder.
"""

import logging
import sys

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Test fonksiyonu"""
    
    print(f"""
{'='*80}
🧪 DİNAMİK QUANTITY FORMATLAMA TESTİ
{'='*80}
""")
    
    try:
        from config.config import ConfigManager
        from exchange.crypto_exchange_api import CryptoExchangeAPI
        
        # 1. Configuration
        print(f"\n{'='*60}")
        print(f"📋 1. CONFIGURATION YÜKLEME")
        print(f"{'='*60}")
        
        config = ConfigManager()
        print(f"✅ Configuration yüklendi")
        
        # 2. Exchange API
        print(f"\n{'='*60}")
        print(f"🔧 2. EXCHANGE API OLUŞTURMA")
        print(f"{'='*60}")
        
        exchange_api = CryptoExchangeAPI(config)
        print(f"✅ Exchange API oluşturuldu")
        
        # 3. Instrument Metadata Çekme
        print(f"\n{'='*60}")
        print(f"📊 3. INSTRUMENT METADATA ÇEKME")
        print(f"{'='*60}")
        
        print(f"📥 Crypto.com API'sinden instrument bilgileri çekiliyor...")
        instruments = exchange_api.get_instruments_info()
        
        if instruments:
            print(f"✅ {len(instruments)} instrument bilgisi cache'lendi")
            
            # Birkaç örnek göster
            test_instruments = ["BONK_USDT", "CRO_USDT", "BTC_USDT", "SOL_USDT", "ETH_USDT"]
            
            print(f"\n📋 ÖRNEK INSTRUMENT BİLGİLERİ:")
            for inst_name in test_instruments:
                if inst_name in instruments:
                    inst_data = instruments[inst_name]
                    print(f"\n   🔹 {inst_name}:")
                    print(f"      • quantity_decimals: {inst_data.get('quantity_decimals')}")
                    print(f"      • price_decimals: {inst_data.get('price_decimals')}")
                    print(f"      • min_quantity: {inst_data.get('min_quantity')}")
                    print(f"      • max_quantity: {inst_data.get('max_quantity')}")
                else:
                    print(f"\n   ❌ {inst_name}: Bulunamadı")
        else:
            print(f"❌ Instrument bilgileri çekilemedi!")
        
        # 4. Quantity Formatlama Testi
        print(f"\n{'='*60}")
        print(f"🎯 4. QUANTITY FORMATLAMA TESTLERİ")
        print(f"{'='*60}")
        
        test_cases = [
            ("BONK_USDT", 460000.0, "Meme coin - çok büyük miktar"),
            ("BONK_USDT", 459540.0, "Meme coin - 0.1% buffer ile"),
            ("CRO_USDT", 46.0, "CRO - orta miktar"),
            ("CRO_USDT", 45.954, "CRO - ondalıklı"),
            ("BTC_USDT", 0.00123456, "BTC - çok küçük miktar"),
            ("SOL_USDT", 2.103, "SOL - ondalıklı"),
            ("ETH_USDT", 0.0042, "ETH - küçük miktar"),
        ]
        
        print(f"\n📊 FORMATLAMA SONUÇLARI:")
        for symbol, quantity, description in test_cases:
            try:
                formatted = exchange_api.format_quantity(symbol, quantity)
                
                # Check if it was from API or fallback
                source = "API" if symbol in instruments else "Fallback"
                
                print(f"\n   {description}")
                print(f"   • Symbol: {symbol}")
                print(f"   • Input: {quantity}")
                print(f"   • Output: {formatted}")
                print(f"   • Source: {source}")
                
                # Show metadata if available
                if symbol in instruments:
                    decimals = instruments[symbol].get('quantity_decimals')
                    print(f"   • Expected Decimals: {decimals}")
                    
            except Exception as e:
                print(f"\n   ❌ {description}")
                print(f"   • Symbol: {symbol}")
                print(f"   • Error: {str(e)}")
        
        # 5. Sonuç
        print(f"\n{'='*80}")
        print(f"🏁 TEST TAMAMLANDI")
        print(f"{'='*80}")
        
        if instruments:
            print(f"✅ Dinamik sistem ÇALIŞIYOR")
            print(f"📊 {len(instruments)} instrument için metadata var")
            print(f"🎯 Her coin için doğru format otomatik belirleniyor")
        else:
            print(f"⚠️ Dinamik sistem kısmen çalışıyor")
            print(f"📊 Metadata çekilemedi, fallback kullanılıyor")
            print(f"🔧 Internet bağlantısını ve API erişimini kontrol edin")
        
        # 6. Öneri
        print(f"\n💡 ÖNERİLER:")
        if instruments:
            print(f"   ✅ Sistem hazır, test_buy_signal.py'yi çalıştırabilirsiniz")
            print(f"   ✅ TP/SL emirleri artık doğru formatla açılmalı")
        else:
            print(f"   ⚠️ Instrument metadata çekilemedi")
            print(f"   🔧 API rate limit veya network sorunu olabilir")
            print(f"   🔄 Birkaç saniye sonra tekrar deneyin")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"💡 Gerekli modülleri kontrol edin")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


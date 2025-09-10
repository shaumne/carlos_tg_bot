#!/usr/bin/env python3
"""
🧪 TEK ALIM SİNYALİ TEST KODU
============================
Bu kod bir tek alım sinyali gönderir ve trade executor'un tepkisini gösterir.
Gerçek trade yapmama sebeplerini tespit eder.
"""

import logging
import sys
import time
from datetime import datetime

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Ana test fonksiyonu"""
    
    print(f"""
{'='*80}
🧪 TEK ALIM SİNYALİ TEST KODU  
{'='*80}
⏰ Test Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Bu test kod:
✅ Otomatik trading ayarlarını kontrol eder
✅ Tek bir alım sinyali gönderir  
✅ Trade executor'un tepkisini gösterir
✅ Satın alıp almama sebeplerini açıklar
""")
    
    try:
        # Import our modules
        from config.config import ConfigManager
        from config.dynamic_settings import DynamicSettingsManager
        from database.database_manager import DatabaseManager
        import simple_trade_executor
        
        # 1. CONFIGURATION CHECK
        print(f"\n{'='*60}")
        print(f"📋 1. CONFIGURATION KONTROLÜ")
        print(f"{'='*60}")
        
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        
        # Apply dynamic settings
        dynamic_settings = DynamicSettingsManager(config, db)
        dynamic_settings.apply_runtime_settings(config)
        
        print(f"📊 Mevcut Ayarlar:")
        print(f"   • Auto Trading: {config.trading.enable_auto_trading}")
        print(f"   • Trade Amount: ${config.trading.trade_amount}")
        print(f"   • Max Positions: {config.trading.max_positions}")
        print(f"   • Take Profit: {config.trading.take_profit_percentage}%")
        print(f"   • Stop Loss: {config.trading.stop_loss_percentage}%")
        
        # 2. API CREDENTIALS CHECK
        print(f"\n{'='*60}")
        print(f"🔐 2. API CREDENTIALS KONTROLÜ")
        print(f"{'='*60}")
        
        has_api_key = hasattr(config.exchange, 'api_key') and config.exchange.api_key
        has_api_secret = hasattr(config.exchange, 'api_secret') and config.exchange.api_secret
        
        print(f"   • API Key: {'✅' if has_api_key else '❌'}")
        print(f"   • API Secret: {'✅' if has_api_secret else '❌'}")
        
        if not has_api_key or not has_api_secret:
            print(f"   ⚠️ API credentials eksik - gerçek trade yapılamaz!")
        
        # 3. BALANCE CHECK
        print(f"\n{'='*60}")
        print(f"💰 3. BALANCE KONTROLÜ")
        print(f"{'='*60}")
        
        try:
            executor = simple_trade_executor.SimpleTradeExecutor(config, db)
            
            # Check USDT balance
            usdt_balance = executor.get_balance("USDT")
            print(f"   • USDT Balance: ${usdt_balance}")
            
            # Check USD balance 
            usd_balance = executor.get_balance("USD")
            print(f"   • USD Balance: ${usd_balance}")
            
            # Check which currency will be used
            sufficient_usdt = executor.has_sufficient_balance("USDT")
            sufficient_usd = executor.has_sufficient_balance("USD")
            
            print(f"   • Minimum Required: ${executor.min_balance_required}")
            print(f"   • USDT Sufficient: {'✅' if sufficient_usdt else '❌'}")
            print(f"   • USD Sufficient: {'✅' if sufficient_usd else '❌'}")
            
            # Determine which currency to use
            if sufficient_usdt:
                sufficient = True
                print(f"   🎯 USDT kullanılacak")
            elif sufficient_usd:
                sufficient = True
                print(f"   🎯 USD kullanılacak (USDT fallback)")
            else:
                sufficient = False
                print(f"   ❌ İkisi de yetersiz!")
            
            # Show executor's trading currency
            if hasattr(executor, 'trading_currency'):
                print(f"   • Trading Currency: {executor.trading_currency}")
            
        except Exception as e:
            print(f"   ❌ Balance kontrolü başarısız: {str(e)}")
            usdt_balance = 0
            usd_balance = 0
            sufficient = False
        
        # 4. TEST SİNYALİ OLUŞTUR
        print(f"\n{'='*60}")
        print(f"📡 4. TEST SİNYALİ OLUŞTURULUYOR")
        print(f"{'='*60}")
        
        test_signal = {
            'symbol': 'SOL_USDT',
            'action': 'BUY',
            'price': 200.0,  # Test fiyatı
            'confidence': 85.0,
            'original_symbol': 'SOL_USDT',
            'row_index': 1,
            'take_profit': 200.0 * 1.1,  # %10 kar
            'stop_loss': 200.0 * 0.95,   # %5 zarar
            'reasoning': 'TEST ALIM SİNYALİ - Manuel test için oluşturuldu'
        }
        
        print(f"🎯 Test Sinyali Hazırlandı:")
        print(f"   • Symbol: {test_signal['symbol']}")
        print(f"   • Action: {test_signal['action']}")
        print(f"   • Price: ${test_signal['price']}")
        print(f"   • Confidence: {test_signal['confidence']}%")
        print(f"   • Take Profit: ${test_signal['take_profit']}")
        print(f"   • Stop Loss: ${test_signal['stop_loss']}")
        
        # 5. TRADE EXECUTION TEST
        print(f"\n{'='*60}")
        print(f"🚀 5. TRADE EXECUTION TEST")
        print(f"{'='*60}")
        
        print(f"🔄 Trade executor'a sinyal gönderiliyor...")
        
        # Execute the trade
        result = simple_trade_executor.execute_trade(test_signal)
        
        print(f"\n📊 SONUÇ:")
        if result:
            print(f"   ✅ Trade başarılı!")
            print(f"   💰 SOL satın alındı (veya alınmaya çalışıldı)")
        else:
            print(f"   ❌ Trade başarısız!")
            print(f"   🔍 Olası sebepler:")
            
            if not config.trading.enable_auto_trading:
                print(f"      • Auto trading KAPALI")
                print(f"      • Çözüm: Auto trading'i açın")
            
            if not has_api_key or not has_api_secret:
                print(f"      • API credentials eksik")
                print(f"      • Çözüm: .env dosyasına API bilgilerinizi ekleyin")
            
            if not sufficient:
                print(f"      • Yetersiz bakiye")
                print(f"      • USDT: ${usdt_balance}, USD: ${usd_balance}")
                print(f"      • Gerekli: ${executor.min_balance_required}")
        
        # 6. AÇIKLAMALAR VE ÇÖZÜMLERİ
        print(f"\n{'='*60}")
        print(f"💡 6. ÇÖZÜM ÖNERİLERİ")
        print(f"{'='*60}")
        
        if not config.trading.enable_auto_trading:
            print(f"🔧 AUTO TRADING AÇMAK İÇİN:")
            print(f"   1. Telegram botunu açın")
            print(f"   2. /settings komutunu gönderen")
            print(f"   3. 'Trading Settings' seçin")
            print(f"   4. 'Auto Trading' açın")
            print(f"   VEYA")
            print(f"   demo_dynamic_settings.py çalıştırın")
        
        if not has_api_key or not has_api_secret:
            print(f"🔐 API CREDENTIALS EKLEMEK İÇİN:")
            print(f"   1. .env dosyasını açın")
            print(f"   2. CRYPTO_API_KEY='your_key_here' ekleyin")
            print(f"   3. CRYPTO_API_SECRET='your_secret_here' ekleyin")
        
        if not sufficient and has_api_key and has_api_secret:
            print(f"💰 BAKİYE ARTTIRMAK İÇİN:")
            print(f"   1. Crypto.com uygulamasını açın")
            print(f"   2. Exchange hesabınıza USDT veya USD yatırın")
            print(f"   3. Minimum ${executor.min_balance_required} olması gerekli")
            print(f"   4. Mevcut: USDT=${usdt_balance}, USD=${usd_balance}")
            print(f"   💡 Not: Sistem hem USDT hem USD kullanabilir")
        
        print(f"\n{'='*80}")
        print(f"🏁 TEST TAMAMLANDI")
        print(f"{'='*80}")
        
        # 7. AKTİF POZİSYON KONTROLÜ
        try:
            positions = db.execute_query("SELECT * FROM active_positions WHERE status = 'open'")
            if positions:
                print(f"📊 Aktif pozisyonlar var: {len(positions)} adet")
            else:
                print(f"📭 Aktif pozisyon bulunamadı")
        except:
            pass
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"💡 Çözüm: Gerekli modülleri kontrol edin")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

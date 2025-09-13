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
            # Try to get Telegram bot instance (optional)
            telegram_bot = None
            try:
                # Check if telegram configuration exists first
                if hasattr(config, 'telegram') and hasattr(config.telegram, 'bot_token'):
                    from telegram_bot.bot_core import TelegramBot
                    telegram_bot = TelegramBot(config, db)
                    print(f"   📞 Telegram bot: ✅ (Notifications will be sent)")
                else:
                    print(f"   📞 Telegram bot: ❌ (No bot token configured)")
                    telegram_bot = None
            except Exception as telegram_error:
                print(f"   📞 Telegram bot: ❌ (No notifications)")
                print(f"   📞 Reason: {str(telegram_error)}")
                logger.debug(f"Telegram bot init failed: {telegram_error}")
                # Continue without telegram bot
                telegram_bot = None
            
            executor = simple_trade_executor.SimpleTradeExecutor(config, db, telegram_bot=telegram_bot)
            
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
        
        # 4. TEST SİNYALİ OLUŞTUR - RANDOM COIN SEÇİMİ
        print(f"\n{'='*60}")
        print(f"📡 4. TEST SİNYALİ OLUŞTURULUYOR - RANDOM COIN")
        print(f"{'='*60}")
        
        # Database'den watched_coins listesini al
        try:
            watched_coins_query = "SELECT symbol, formatted_symbol FROM watched_coins WHERE is_active = 1"
            watched_coins = db.execute_query(watched_coins_query)
            
            if not watched_coins:
                # Fallback: Default coin ekle
                print(f"⚠️ Watchlist boş, default coin ekleniyor...")
                default_coins = [
                    ('SOL_USDT', 'SOL_USDT'),
                    ('BTC_USDT', 'BTC_USDT'), 
                    ('ETH_USDT', 'ETH_USDT'),
                    ('ADA_USDT', 'ADA_USDT')
                ]
                
                for symbol, formatted in default_coins:
                    try:
                        db.execute_update(
                            "INSERT OR IGNORE INTO watched_coins (symbol, formatted_symbol, is_active, created_by) VALUES (?, ?, ?, ?)",
                            (symbol, formatted, True, "test_script")
                        )
                    except:
                        pass
                
                # Tekrar dene
                watched_coins = db.execute_query(watched_coins_query)
            
            print(f"📊 Watchlist'te {len(watched_coins)} coin bulundu")
            
            # Random coin seç
            import random
            selected_coin = random.choice(watched_coins)
            test_symbol = selected_coin[0]  # symbol column
            
            print(f"🎲 Random seçilen coin: {test_symbol}")
            
            # Get current price for the selected coin (fallback to 100 if can't get)
            try:
                current_price = executor.get_current_price(test_symbol)
                if not current_price or current_price <= 0:
                    current_price = 100.0  # Fallback price
                print(f"💰 Mevcut fiyat: ${current_price}")
            except:
                current_price = 100.0
                print(f"⚠️ Fiyat alınamadı, fallback kullanılıyor: ${current_price}")
            
        except Exception as e:
            print(f"⚠️ Database'den coin seçimi başarısız: {e}")
            test_symbol = 'SOL_USDT'  # Fallback
            current_price = 200.0
            print(f"🔄 Fallback coin kullanılıyor: {test_symbol}")
        
        test_signal = {
            'symbol': test_symbol,
            'action': 'BUY',
            'price': current_price,
            'confidence': 85.0,
            'original_symbol': test_symbol,
            'row_index': 1,
            'take_profit': current_price * 1.1,  # %10 kar
            'stop_loss': current_price * 0.95,   # %5 zarar
            'reasoning': f'TEST ALIM SİNYALİ - {test_symbol} için random test'
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
        
        # Execute the trade using the same executor instance
        result = executor.execute_trade(test_signal)
        
        print(f"\n📊 SONUÇ:")
        if result:
            print(f"   ✅ Trade başarılı!")
            print(f"   💰 {test_signal['symbol']} satın alındı")
            
            # Check active positions to see TP/SL status
            try:
                active_positions = executor.get_active_positions()
                if test_signal['symbol'] in active_positions:
                    position = active_positions[test_signal['symbol']]
                    print(f"   📊 POZİSYON DETAYLARI:")
                    print(f"      💱 Symbol: {position.get('symbol', 'N/A')}")
                    print(f"      💰 Entry Price: ${position.get('entry_price', 'N/A')}")
                    print(f"      📊 Quantity: {position.get('quantity', 'N/A')}")
                    print(f"      🎯 Take Profit: ${position.get('take_profit', 'N/A')}")
                    print(f"      🛑 Stop Loss: ${position.get('stop_loss', 'N/A')}")
                    print(f"      🆔 Main Order: {position.get('main_order_id', 'N/A')}")
                    
                    # TP/SL Order Status
                    tp_order = position.get('tp_order_id')
                    sl_order = position.get('sl_order_id')
                    print(f"      📋 TP/SL ORDER STATUS:")
                    print(f"         🟢 TP Order: {'✅ Created' if tp_order else '❌ Failed'} (ID: {tp_order or 'None'})")
                    print(f"         🔴 SL Order: {'✅ Created' if sl_order else '❌ Failed'} (ID: {sl_order or 'None'})")
                else:
                    print(f"   ⚠️ Pozisyon aktif pozisyonlar listesinde bulunamadı")
                    
                # Check database for saved position
                db_positions = db.execute_query(
                    "SELECT * FROM active_positions WHERE symbol = ? AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1",
                    (test_signal['symbol'],)
                )
                if db_positions:
                    print(f"   💾 Pozisyon database'e kaydedildi ✅")
                else:
                    print(f"   💾 Pozisyon database'e kaydedilemedi ❌")
                    
            except Exception as pos_error:
                print(f"   ⚠️ Pozisyon detayları alınamadı: {pos_error}")
                
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
        
        # 7. AKTİF POZİSYON KONTROLÜ - DETAYLI
        print(f"\n{'='*60}")
        print(f"📊 7. AKTİF POZİSYONLAR KONTROLÜ")
        print(f"{'='*60}")
        
        try:
            # Memory'deki aktif pozisyonlar
            if 'executor' in locals():
                memory_positions = executor.get_active_positions()
                print(f"💾 Memory'deki aktif pozisyonlar: {len(memory_positions)}")
                
                for symbol, pos in memory_positions.items():
                    print(f"   🔸 {symbol}:")
                    print(f"      • Entry: ${pos.get('entry_price', 'N/A')}")
                    print(f"      • Quantity: {pos.get('quantity', 'N/A')}")
                    print(f"      • TP Order: {pos.get('tp_order_id', 'None')}")
                    print(f"      • SL Order: {pos.get('sl_order_id', 'None')}")
            
            # Database'deki aktif pozisyonlar
            db_positions = db.execute_query("SELECT * FROM active_positions WHERE status = 'ACTIVE'")
            print(f"🗃️ Database'deki aktif pozisyonlar: {len(db_positions) if db_positions else 0}")
            
            if db_positions:
                for pos in db_positions:
                    symbol = pos[1] if len(pos) > 1 else "Unknown"  # symbol column
                    print(f"   🔹 {symbol}:")
                    entry_price = pos[4] if len(pos) > 4 else "N/A"  # entry_price column
                    quantity = pos[5] if len(pos) > 5 else "N/A"     # quantity column  
                    main_order = pos[8] if len(pos) > 8 else "None"  # order_id column
                    tp_order = pos[9] if len(pos) > 9 else "None"    # tp_order_id column
                    sl_order = pos[10] if len(pos) > 10 else "None"  # sl_order_id column
                    print(f"      • Entry: ${entry_price}")
                    print(f"      • Quantity: {quantity}")
                    print(f"      • Main Order: {main_order}")
                    print(f"      • TP Order: {tp_order}")
                    print(f"      • SL Order: {sl_order}")
            else:
                print(f"   📭 Database'de aktif pozisyon bulunamadı")
                
        except Exception as pos_check_error:
            print(f"❌ Pozisyon kontrolü hatası: {pos_check_error}")
        
        # Trade history kontrolü
        try:
            recent_trades = db.execute_query(
                "SELECT * FROM trade_history WHERE timestamp >= datetime('now', '-1 hour') ORDER BY timestamp DESC LIMIT 5"
            )
            print(f"📈 Son 1 saat içindeki trade'ler: {len(recent_trades) if recent_trades else 0}")
        except Exception as trade_check_error:
            print(f"❌ Trade history kontrolü hatası: {trade_check_error}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"💡 Çözüm: Gerekli modülleri kontrol edin")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

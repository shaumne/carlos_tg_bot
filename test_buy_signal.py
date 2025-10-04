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
                    from telegram_bot.bot_core import TelegramTradingBot
                    telegram_bot = TelegramTradingBot(config, db)
                    
                    # Initialize telegram bot asynchronously
                    import asyncio
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(telegram_bot.initialize())
                        loop.close()
                        print(f"   📞 Telegram bot: ✅ (Fully initialized and ready)")
                    except Exception as init_error:
                        print(f"   📞 Telegram bot: ❌ (Init failed: {str(init_error)})")
                        telegram_bot = None
                else:
                    print(f"   📞 Telegram bot: ❌ (No bot token configured)")
                    telegram_bot = None
            except Exception as telegram_error:
                print(f"   📞 Telegram bot: ❌ (No notifications)")
                print(f"   📞 Reason: {str(telegram_error)}")
                logger.debug(f"Telegram bot init failed: {telegram_error}")
                # Continue without telegram bot
                telegram_bot = None
            
            # Create executor with exchange_api from telegram_bot if available
            exchange_api_instance = None
            if telegram_bot and hasattr(telegram_bot, 'exchange_api'):
                exchange_api_instance = telegram_bot.exchange_api
                logger.info("Using exchange_api from telegram_bot")
            
            executor = simple_trade_executor.SimpleTradeExecutor(
                config, 
                db, 
                exchange_api=exchange_api_instance,
                telegram_bot=telegram_bot
            )
            
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
            
            # Get initial position info
            try:
                active_positions = executor.get_active_positions()
                if test_signal['symbol'] in active_positions:
                    position = active_positions[test_signal['symbol']]
                    tp_order_id = position.get('tp_order_id')
                    sl_order_id = position.get('sl_order_id')
                    
                    print(f"   📊 POZİSYON DETAYLARI:")
                    print(f"      💱 Symbol: {position.get('symbol', 'N/A')}")
                    print(f"      💰 Entry Price: ${position.get('entry_price', 'N/A')}")
                    print(f"      📊 Quantity: {position.get('quantity', 'N/A')}")
                    print(f"      🎯 Take Profit: ${position.get('take_profit', 'N/A')}")
                    print(f"      🛑 Stop Loss: ${position.get('stop_loss', 'N/A')}")
                    print(f"      🆔 Main Order: {position.get('main_order_id', 'N/A')}")
                    print(f"      🟢 TP Order: {tp_order_id or 'None'}")
                    print(f"      🔴 SL Order: {sl_order_id or 'None'}")
                    
                    # 20 SANİYE İZLEME SİSTEMİ
                    print(f"\n{'='*60}")
                    print(f"⏰ 20 SANİYE POZİSYON İZLEME BAŞLIYOR...")
                    print(f"{'='*60}")
                    
                    for i in range(1, 21):
                        print(f"\n🕐 Saniye {i}/20:")
                        time.sleep(1)
                        
                        # Mevcut fiyat
                        try:
                            current_price = executor.get_current_price(test_signal['symbol'])
                            if current_price:
                                print(f"   💲 Mevcut Fiyat: ${current_price:.6f}")
                            else:
                                print(f"   ⚠️ Fiyat alınamadı")
                        except:
                            print(f"   ⚠️ Fiyat hatası")
                        
                        # TP/SL Order Status Kontrolü
                        if tp_order_id:
                            try:
                                tp_status = executor._get_order_status(tp_order_id)
                                print(f"   🟢 TP Order Status: {tp_status or 'Unknown'}")
                            except:
                                print(f"   🟢 TP Order Status: Kontrol edilemedi")
                        
                        if sl_order_id:
                            try:
                                sl_status = executor._get_order_status(sl_order_id)
                                print(f"   🔴 SL Order Status: {sl_status or 'Unknown'}")
                            except:
                                print(f"   🔴 SL Order Status: Kontrol edilemedi")
                        
                        # Memory pozisyon kontrolü
                        current_positions = executor.get_active_positions()
                        if test_signal['symbol'] in current_positions:
                            pos_status = current_positions[test_signal['symbol']].get('status', 'UNKNOWN')
                            print(f"   📊 Pozisyon Durumu: {pos_status}")
                        else:
                            print(f"   ⚠️ Pozisyon memory'de yok (kapanmış olabilir)")
                            
                            # Database'den kontrol et
                            try:
                                db_check = db.execute_query(
                                    "SELECT status, notes FROM active_positions WHERE symbol = ? ORDER BY created_at DESC LIMIT 1",
                                    (test_signal['symbol'],)
                                )
                                if db_check:
                                    db_status = db_check[0][0] if len(db_check[0]) > 0 else 'UNKNOWN'
                                    db_notes = db_check[0][1] if len(db_check[0]) > 1 else ''
                                    print(f"   💾 Database Status: {db_status}")
                                    if db_notes:
                                        print(f"   📝 Notes: {db_notes}")
                            except:
                                pass
                        
                        # Coin balance kontrolü
                        try:
                            coin_symbol = test_signal['symbol'].split('_')[0]
                            coin_balance = executor.get_balance(coin_symbol)
                            print(f"   💰 {coin_symbol} Balance: {coin_balance}")
                            
                            if float(coin_balance) <= 0.0001:
                                print(f"   ⚠️ UYARI: Coin satılmış görünüyor!")
                        except:
                            pass
                    
                    # 20 saniye sonunda final durum
                    print(f"\n{'='*60}")
                    print(f"🏁 20 SANİYE SONUNDA FİNAL DURUM")
                    print(f"{'='*60}")
                    
                    # Final TP/SL Status
                    if tp_order_id:
                        try:
                            final_tp_status = executor._get_order_status(tp_order_id)
                            print(f"🟢 TP Order Final Status: {final_tp_status or 'Unknown'}")
                        except:
                            print(f"🟢 TP Order: Kontrol edilemedi")
                    
                    if sl_order_id:
                        try:
                            final_sl_status = executor._get_order_status(sl_order_id)
                            print(f"🔴 SL Order Final Status: {final_sl_status or 'Unknown'}")
                        except:
                            print(f"🔴 SL Order: Kontrol edilemedi")
                    
                    # Final pozisyon durumu
                    final_positions = executor.get_active_positions()
                    if test_signal['symbol'] in final_positions:
                        print(f"📊 Pozisyon: AKTİF (memory'de)")
                        final_pos = final_positions[test_signal['symbol']]
                        print(f"   Status: {final_pos.get('status', 'UNKNOWN')}")
                    else:
                        print(f"📊 Pozisyon: KAPALI veya memory'de yok")
                    
                    # Database final kontrolü
                    try:
                        final_db_check = db.execute_query(
                            "SELECT status, notes, updated_at FROM active_positions WHERE symbol = ? ORDER BY updated_at DESC LIMIT 1",
                            (test_signal['symbol'],)
                        )
                        if final_db_check:
                            print(f"💾 Database Status: {final_db_check[0][0] if len(final_db_check[0]) > 0 else 'UNKNOWN'}")
                            if len(final_db_check[0]) > 1 and final_db_check[0][1]:
                                print(f"📝 Notes: {final_db_check[0][1]}")
                    except Exception as db_err:
                        print(f"💾 Database kontrolü başarısız: {db_err}")
                    
                    # Final coin balance
                    try:
                        coin_symbol = test_signal['symbol'].split('_')[0]
                        final_balance = executor.get_balance(coin_symbol)
                        print(f"💰 Final {coin_symbol} Balance: {final_balance}")
                        
                        if float(final_balance) <= 0.0001:
                            print(f"✅ Coin başarıyla satıldı!")
                        else:
                            print(f"ℹ️  Coin hala bakiyede mevcut")
                    except:
                        pass
                    
                else:
                    print(f"   ⚠️ Pozisyon aktif pozisyonlar listesinde bulunamadı")
                    
            except Exception as pos_error:
                print(f"   ⚠️ Pozisyon detayları alınamadı: {pos_error}")
                import traceback
                traceback.print_exc()
                
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
        print(f"🏁 TEST TAMAMLANDI - 20 SANİYELİK İZLEME BİTTİ")
        print(f"{'='*80}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"💡 Çözüm: Gerekli modülleri kontrol edin")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

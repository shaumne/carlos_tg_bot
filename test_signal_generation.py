#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Signal Generation
Bu script sinyal üretim sistemini test eder ve düzgün çalışıp çalışmadığını kontrol eder.
"""

import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Test signal generation system"""
    
    print(f"""
{'='*80}
🧪 SİNYAL ÜRETİM TEST KODU  
{'='*80}
⏰ Test Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Bu test:
✅ Sinyal engine'i başlatır
✅ Watchlist coinlerini analiz eder  
✅ Üretilen sinyalleri gösterir
✅ Sinyal koşullarını kontrol eder
""")
    
    try:
        # Import modules
        from config.config import ConfigManager
        from database.database_manager import DatabaseManager
        from signals.signal_engine import SignalEngine
        
        # 1. INITIALIZE SYSTEM
        print(f"\n{'='*60}")
        print(f"📋 1. SİSTEM BAŞLATILIYOR")
        print(f"{'='*60}")
        
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        signal_engine = SignalEngine(config, db)
        
        print(f"✅ Config ve Database yüklendi")
        print(f"✅ Signal Engine başlatıldı")
        
        # 2. GET WATCHED COINS
        print(f"\n{'='*60}")
        print(f"📊 2. WATCHLIST COİNLERİ ALINIYOR")
        print(f"{'='*60}")
        
        watched_coins = db.get_watched_coins()
        
        if not watched_coins:
            print(f"⚠️ Watchlist boş!")
            print(f"💡 Önce /add_coin komutu ile coin ekleyin")
            return
        
        print(f"📊 Watchlist'te {len(watched_coins)} coin bulundu:")
        for coin in watched_coins:
            print(f"   • {coin['symbol']}")
        
        # 3. ANALYZE COINS
        print(f"\n{'='*60}")
        print(f"🔍 3. COİNLER ANALİZ EDİLİYOR")
        print(f"{'='*60}")
        
        signals_generated = []
        
        for coin in watched_coins:
            symbol = coin['symbol']
            print(f"\n📡 Analyzing {symbol}...")
            
            try:
                signal = signal_engine.analyze_symbol(symbol)
                
                if signal:
                    print(f"   ✅ Sinyal üretildi: {signal.signal_type}")
                    print(f"   💰 Fiyat: ${signal.price:.4f}")
                    print(f"   📊 Confidence: {signal.confidence:.2%}")
                    print(f"   📝 Reasoning:")
                    for reason in signal.reasoning:
                        print(f"      - {reason}")
                    
                    # Show indicators
                    if signal.indicators:
                        print(f"   📈 Indicators:")
                        print(f"      RSI: {signal.indicators.rsi:.1f}" if signal.indicators.rsi else "      RSI: N/A")
                        print(f"      Volume Ratio: {signal.indicators.volume_ratio:.2f}x" if signal.indicators.volume_ratio else "      Volume Ratio: N/A")
                    
                    signals_generated.append(signal)
                else:
                    print(f"   ❌ Sinyal üretilemedi")
                    
            except Exception as e:
                print(f"   ❌ Hata: {str(e)}")
                logger.error(f"Error analyzing {symbol}: {str(e)}")
        
        # 4. SUMMARY
        print(f"\n{'='*60}")
        print(f"📊 4. ÖZET")
        print(f"{'='*60}")
        
        buy_signals = [s for s in signals_generated if s.signal_type == "BUY"]
        sell_signals = [s for s in signals_generated if s.signal_type == "SELL"]
        wait_signals = [s for s in signals_generated if s.signal_type == "WAIT"]
        
        print(f"📊 Toplam Analiz: {len(watched_coins)} coin")
        print(f"✅ Başarılı Sinyal: {len(signals_generated)}")
        print(f"🟢 BUY Sinyalleri: {len(buy_signals)}")
        print(f"🔴 SELL Sinyalleri: {len(sell_signals)}")
        print(f"⚪ WAIT Sinyalleri: {len(wait_signals)}")
        
        # Show BUY signals
        if buy_signals:
            print(f"\n🟢 BUY SİNYALLERİ:")
            for signal in buy_signals:
                print(f"   • {signal.symbol} @ ${signal.price:.4f} (Confidence: {signal.confidence:.1%})")
        
        # Show SELL signals
        if sell_signals:
            print(f"\n🔴 SELL SİNYALLERİ:")
            for signal in sell_signals:
                print(f"   • {signal.symbol} @ ${signal.price:.4f} (Confidence: {signal.confidence:.1%})")
        
        # 5. RECOMMENDATIONS
        print(f"\n{'='*60}")
        print(f"💡 5. ÖNERİLER")
        print(f"{'='*60}")
        
        if not buy_signals and not sell_signals:
            print(f"ℹ️ Şu anda BUY veya SELL sinyali yok")
            print(f"✅ Sinyal üretim sistemi düzgün çalışıyor")
            print(f"⏳ Piyasa koşulları sinyal için uygun değil")
            print(f"🔄 Background analyzer sürekli kontrol edecek")
        else:
            print(f"✅ Sinyal üretim sistemi çalışıyor!")
            print(f"📡 {len(buy_signals) + len(sell_signals)} aktif sinyal mevcut")
            
            if config.trading.enable_auto_trading:
                print(f"🤖 Auto trading AÇIK - Sinyaller otomatik execute edilecek")
            else:
                print(f"⚠️ Auto trading KAPALI - Sinyaller sadece bildirim olarak gönderilecek")
        
        print(f"\n{'='*80}")
        print(f"🏁 TEST TAMAMLANDI")
        print(f"{'='*80}")
        
    except ImportError as e:
        print(f"❌ Import hatası: {e}")
        print(f"💡 Gerekli modülleri kontrol edin")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
🔧 AUTO TRADING AYARı AÇMA KODU
===============================
Bu kod auto trading ayarını otomatik olarak açar
"""

import logging
import sys
from datetime import datetime

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Auto trading ayarını aç"""
    
    print(f"""
{'='*80}
🔧 AUTO TRADING AYARı AÇILIYOR
{'='*80}
⏰ Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    try:
        # Import our modules
        from config.config import ConfigManager
        from config.dynamic_settings import DynamicSettingsManager
        from database.database_manager import DatabaseManager
        
        # Initialize
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        settings = DynamicSettingsManager(config, db)
        
        # Check current status
        current_auto_trading = settings.get_setting('trading', 'enable_auto_trading', False)
        print(f"📊 Mevcut auto trading durumu: {current_auto_trading}")
        
        if current_auto_trading:
            print(f"✅ Auto trading zaten açık!")
            return
        
        # Enable auto trading
        print(f"🔄 Auto trading açılıyor...")
        success = settings.set_setting('trading', 'enable_auto_trading', True, user_id=123456)
        
        if success:
            print(f"✅ Auto trading başarıyla açıldı!")
            
            # Verify the change
            updated_status = settings.get_setting('trading', 'enable_auto_trading', False)
            print(f"✓ Yeni durum: {updated_status}")
            
            # Apply to runtime config
            settings.apply_runtime_settings(config)
            print(f"✓ Runtime config güncellendi: {config.trading.enable_auto_trading}")
            
        else:
            print(f"❌ Auto trading açılamadı!")
            return
        
        # Show other trading settings
        print(f"\n📋 GÜNCEL TRADING AYARLARI:")
        print(f"   • Auto Trading: {config.trading.enable_auto_trading}")
        print(f"   • Trade Amount: ${config.trading.trade_amount}")
        print(f"   • Max Positions: {config.trading.max_positions}")
        print(f"   • Take Profit: {config.trading.take_profit_percentage}%")
        print(f"   • Stop Loss: {config.trading.stop_loss_percentage}%")
        
        print(f"""
{'='*80}
✅ AUTO TRADING BAŞARIYLA AÇILDI!
{'='*80}

🎯 Şimdi yapabilecekleriniz:
   1. test_buy_signal.py çalıştırın
   2. fake_signal_generator.py çalıştırın  
   3. Telegram botunu çalıştırın ve gerçek sinyalleri bekleyin

⚠️ DİKKAT: 
   • API credentials'ı kontrol edin (.env dosyası)
   • Yeterli USDT bakiyeniz olduğundan emin olun
   • Bu GERÇEK PARA ile trade yapar!
""")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


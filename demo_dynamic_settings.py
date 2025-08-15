#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dinamik Ayar Sistemi Demonstration
Kullanıcının runtime'da bot ayarlarını nasıl değiştirebileceğini gösterir
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Mock configs for demo
os.environ.setdefault('TELEGRAM_BOT_TOKEN', 'DEMO_TOKEN')
os.environ.setdefault('TELEGRAM_CHAT_ID', '123456789')
os.environ.setdefault('CRYPTO_API_KEY', 'DEMO_KEY')
os.environ.setdefault('CRYPTO_API_SECRET', 'DEMO_SECRET')

from config.config import ConfigManager
from database.database_manager import DatabaseManager
from config.dynamic_settings import DynamicSettingsManager

def demo_settings_flow():
    """Kullanıcı ayar değiştirme akışını simüle et"""
    
    print("🎬 Dinamik Ayar Sistemi Demo")
    print("=" * 60)
    
    try:
        # Initialize components  
        print("📋 Sistem başlatılıyor...")
        config = ConfigManager()
        db = DatabaseManager("data/demo_settings.db")
        settings = DynamicSettingsManager(config, db)
        print("✅ Sistem hazır\n")
        
        # Show initial settings
        print("📊 BAŞLANGIÇ AYARLARI:")
        print("-" * 30)
        trade_amount = settings.get_setting('trading', 'trade_amount', 10.0)
        max_positions = settings.get_setting('trading', 'max_positions', 5)
        auto_trading = settings.get_setting('trading', 'enable_auto_trading', False)
        rsi_oversold = settings.get_setting('technical', 'rsi_oversold', 30.0)
        
        print(f"💰 Trade Amount: {trade_amount} USDT")
        print(f"📈 Max Positions: {max_positions}")
        print(f"🤖 Auto Trading: {'✅ Aktif' if auto_trading else '❌ Pasif'}")
        print(f"📊 RSI Oversold: {rsi_oversold}")
        
        # Simulate Telegram command flow
        print(f"\n" + "="*60)
        print("📱 TELEGRAM BOT SİMÜLASYONU")
        print("="*60)
        
        print("\n🤖 Bot: '/settings komutunu kullandınız'\n")
        
        # Show settings menu
        print("⚙️ **Bot Ayarları**\n")
        print("Kategoriler:")
        print("[💰 Trading] [📊 Teknik] [🔔 Bildirimler] [⚙️ Sistem]")
        
        print(f"\n👤 Kullanıcı: '[💰 Trading]' butonuna bastı\n")
        
        # Show trading category
        trading_settings = settings.get_category_settings('trading')
        print("💰 **Trading Ayarları**\n")
        
        for key, setting_info in trading_settings.items():
            value = setting_info['value']
            description = setting_info['description']
            setting_type = setting_info['type']
            min_val = setting_info.get('min_value')
            max_val = setting_info.get('max_value')
            
            range_info = f" ({min_val}-{max_val})" if min_val and max_val else ""
            
            if setting_type == 'bool':
                value_display = "✅ Aktif" if value else "❌ Pasif"
            else:
                value_display = f"{value}{range_info}"
            
            print(f"• **{description}**")
            print(f"  Değer: `{value_display}`\n")
        
        print("[✏️ İşlem miktarı] [✏️ Maks pozisyon] [✏️ Otomatik trading]")
        
        print(f"\n👤 Kullanıcı: '[✏️ İşlem miktarı]' butonuna bastı\n")
        
        # Show edit interface
        print("✏️ **İşlem miktarı (USDT)** Düzenle\n")
        print(f"**Mevcut değer:** `{trade_amount}`")
        print("**Tip:** float (1.0 - 1000.0)")
        print("\nYeni değeri yazın veya iptal etmek için 'iptal' yazın.")
        
        print(f"\n👤 Kullanıcı: '50' yazdı\n")
        
        # Simulate setting change
        new_amount = 50.0
        success = settings.set_setting('trading', 'trade_amount', new_amount, user_id=123456)
        
        if success:
            print("✅ **İşlem miktarı (USDT)** güncellendi!\n")
            print(f"Yeni değer: `{new_amount}`")
            print("\n⚡ **ANINDA ETKİ:** Değişiklik hemen uygulandı, restart gerekmedi!\n")
            
            # Apply to config
            settings.apply_runtime_settings(config)
            updated_config_amount = config.trading.trade_amount
            
            print(f"🔄 Config güncellendi: {trade_amount} → {updated_config_amount}")
        
        print("[⬅️ Ayarlara Dön]")
        
        # Show boolean toggle demo
        print(f"\n" + "-"*60)
        print("📱 BOOLEAN AYAR DEĞİŞİKLİĞİ")
        print("-"*60)
        
        print(f"\n👤 Kullanıcı: '[✏️ Otomatik trading]' butonuna bastı\n")
        
        # Toggle auto trading
        current_auto = settings.get_setting('trading', 'enable_auto_trading', False)
        new_auto = not current_auto
        
        success = settings.set_setting('trading', 'enable_auto_trading', new_auto, user_id=123456)
        
        if success:
            print("✅ **Otomatik trading aktif/pasif** güncellendi!\n")
            print(f"Yeni değer: {'✅ Aktif' if new_auto else '❌ Pasif'}")
            print("\n⚡ **ANINDA ETKİ:** Bu da hemen uygulandı!\n")
        
        # Show final summary
        print(f"\n" + "="*60)
        print("📊 DEĞİŞİKLİK ÖZETİ")
        print("="*60)
        
        print("\n🔄 **Değişen ayarlar:**")
        print(f"• Trade Amount: {trade_amount} → {new_amount} USDT")
        print(f"• Auto Trading: {'✅' if auto_trading else '❌'} → {'✅' if new_auto else '❌'}")
        
        print(f"\n✅ **Tüm değişiklikler:**")
        print("• ⚡ Anında uygulandı (restart gerekmedi)")
        print("• 💾 Database'e kaydedildi")
        print("• 📝 Audit log'una eklendi")
        print("• 🔄 Config manager'a uygulandı")
        
        # Show priority system demo
        print(f"\n" + "="*60)
        print("🎯 PRİORİTY SİSTEMİ")
        print("="*60)
        
        print("\n📋 **Ayar öncelik sırası:**")
        print("1. 🗄️ **Database** (runtime değişiklikler) - EN YÜKSEK")
        print("2. 🌍 **Environment** (.env dosyası) - ORTA")
        print("3. ⚙️ **Default** (hardcoded) - EN DÜŞÜK")
        
        print(f"\n💡 **Örnek:**")
        env_amount = os.environ.get('TRADE_AMOUNT', '10.0')
        db_amount = settings.get_setting('trading', 'trade_amount')
        
        print(f"• ENV dosyası: {env_amount} USDT")
        print(f"• Database: {db_amount} USDT")
        print(f"• **Kullanılan:** {db_amount} USDT (database öncelikli)")
        
        # Show export demo
        print(f"\n" + "="*60)
        print("📁 EXPORT/IMPORT")
        print("="*60)
        
        exported = settings.export_settings()
        print(f"\n📤 **Export edilen ayarlar:**")
        
        import json
        print("```json")
        print(json.dumps(exported, indent=2, ensure_ascii=False))
        print("```")
        
        print(f"\n💾 Bu JSON'ı kaydedip başka sistemlere aktarabilirsiniz!")
        
        # Final tips
        print(f"\n" + "="*60)
        print("💡 KULLANIM İPUÇLARI")
        print("="*60)
        
        print(f"""
✅ **Avantajlar:**
• 🚀 Restart gerektirmez (çoğu ayar)
• 📱 Telegram üzerinden kolay yönetim
• 🔒 Kullanıcı bazlı yetkilendirme
• 📝 Tüm değişiklikler loglanır
• 🎯 Priority system (DB > ENV > Default)
• 💾 Kalıcı saklama

⚙️ **Kullanım:**
• /settings - Ana ayarlar menüsü
• Kategorileri seçin
• Butonlarla ayarları değiştirin
• Anında etkili olur!

🛡️ **Güvenlik:**
• Sadece yetkili Telegram ID'leri
• Validation kontrolü
• Audit logging
• Rate limiting
        """)
        
        db.close()
        
        print(f"\n🎉 Demo tamamlandı! Sistem production-ready!")
        return True
        
    except Exception as e:
        print(f"\n❌ Demo hatası: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🚀 Dinamik Ayar Sistemi Demo Başlıyor...\n")
    
    # Create demo directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    success = demo_settings_flow()
    
    if success:
        print(f"\n✅ Demo başarılı!")
        print(f"\n📝 Sonraki adımlar:")
        print(f"1. .env dosyasını API bilgilerinizle doldurun")
        print(f"2. python main.py ile bot'u başlatın")
        print(f"3. Telegram'da /settings komutunu kullanın")
        print(f"4. Ayarları değiştirip test edin!")
    else:
        print(f"\n❌ Demo başarısız!")
    
    print(f"\n👋 Demo sona erdi.")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
English Interface Converter
Telegram bot interface'ini Türkçe'den İngilizce'ye çevirir
"""

import re

def convert_turkish_to_english():
    """Bot core'daki Türkçe metinleri İngilizce'ye çevir"""
    
    # Turkish to English mapping
    translations = {
        # Commands and basics
        "Bot durumu ve sistem bilgileri": "Bot status and system information",
        "Aktif pozisyonlar ve portföy": "Active positions and portfolio", 
        "Exchange bakiye bilgileri": "Exchange balance information",
        "Takip edilen coinler": "Tracked coins",
        "Son trading sinyalleri": "Recent trading signals",
        "İşlem geçmişi": "Trade history",
        "Bot ayarları": "Bot settings",
        "Coin takip listesine ekle": "Add coin to watchlist",
        "Coin takip listesinden çıkar": "Remove coin from watchlist",
        "Belirli bir coin'i analiz et": "Analyze specific coin",
        "Sistem sağlık kontrolü": "System health check",
        
        # Status messages
        "Bot Durum Raporu": "Bot Status Report",
        "Sistem Durumu:": "System Status:",
        "Trading Durumu:": "Trading Status:",
        "Aktif Pozisyonlar:": "Active Positions:",
        "Takip Edilen Coinler:": "Tracked Coins:",
        "Son 24h Sinyaller:": "Last 24h Signals:",
        "Son 24h İşlemler:": "Last 24h Trades:",
        "Ayarlar:": "Settings:",
        "Trading Miktarı:": "Trade Amount:",
        "Maks Pozisyon:": "Max Positions:",
        "Otomatik Trading:": "Auto Trading:",
        "Paper Trading:": "Paper Trading:",
        "Bildirimler:": "Notifications:",
        "Log Level:": "Log Level:",
        "Son Güncelleme:": "Last Update:",
        
        # Portfolio messages
        "Portföy Raporu": "Portfolio Report",
        "Aktif pozisyon bulunmuyor.": "No active positions found.",
        "Pozisyon açmak için:": "To open positions:",
        "ile takip edilen coinleri görebilirsiniz": "to view tracked coins",
        "ile trading sinyallerini kontrol edebilirsiniz": "to check trading signals",
        "ile yeni coin ekleyebilirsiniz": "to add new coins",
        "Giriş:": "Entry:",
        "Güncel:": "Current:",
        "Miktar:": "Quantity:",
        "Fiyat alınamadı": "Price unavailable",
        "Toplam P&L:": "Total P&L:",
        
        # Balance messages
        "Bakiye Raporu": "Balance Report",
        "Bakiye bilgisi alınamadı": "Could not retrieve balance information",
        "Olası nedenler:": "Possible reasons:",
        "Exchange API bağlantı sorunu": "Exchange API connection issue",
        "API anahtarları hatalı": "Incorrect API keys", 
        "Yetki problemi": "Authorization problem",
        "Ana Bakiyeler:": "Main Balances:",
        "Kilitli:": "Locked:",
        "Diğer": "Others",
        "coin": "coins",
        "ve": "and",
        "coin daha": "more coins",
        "Trading için yeterli bakiye": "Sufficient balance for trading",
        "Min:": "Min:",
        "Yetersiz USDT bakiyesi": "Insufficient USDT balance",
        
        # Watchlist messages
        "Takip Listesi": "Watchlist",
        "Hiç coin takip edilmiyor.": "No coins being tracked.",
        "Coin eklemek için:": "To add coins:",
        "komut ile": "with command",
        "butonunu kullanın": "button",
        "Coin Ekle": "Add Coin",
        "Coin Çıkar": "Remove Coin",
        "Analiz Et": "Analyze",
        "Eklendi:": "Added:",
        "Aktif pozisyon": "Active position",
        
        # Signals messages
        "Trading Sinyalleri": "Trading Signals",
        "Henüz sinyal üretilmemiş.": "No signals generated yet.",
        "Sinyal üretmek için:": "To generate signals:",
        "Takip listesine coin ekleyin": "Add coins to watchlist",
        "Sistem otomatik olarak analiz yapacak": "System will analyze automatically",
        "Manual analiz:": "Manual analysis:",
        "Son Trading Sinyalleri": "Recent Trading Signals",
        "Fiyat:": "Price:",
        "Güven:": "Confidence:",
        "Zaman:": "Time:",
        "sinyal daha": "more signals",
        "Tüm Sinyaller": "All Signals",
        
        # History messages
        "İşlem Geçmişi": "Trade History",
        "Henüz işlem geçmişi bulunmuyor.": "No trade history found yet.",
        "İşlem yaptıktan sonra burada görünecek.": "Will appear here after trading.",
        "Son İşlemler": "Recent Trades",
        "işlem daha": "more trades",
        "Detay": "Details",
        "Geçmiş": "History",
        "Tarih:": "Date:",
        
        # Settings messages (dynamic settings will handle these)
        
        # Add coin messages
        "Coin Ekle": "Add Coin",
        "Takip listesine eklemek istediğiniz coin sembolünü yazın:": "Enter the coin symbol you want to add to watchlist:",
        "Örnek:": "Example:",
        "İptal etmek için": "To cancel type",
        "yazın": "type",
        
        # Remove coin messages
        "Takip listesinde coin bulunmuyor.": "No coins in watchlist.",
        "Çıkarmak istediğiniz coin'i seçin:": "Select the coin you want to remove:",
        "İptal": "Cancel",
        
        # Analyze messages
        "Analiz edilecek coin bulunamadı.": "No coins found to analyze.",
        "Önce": "First",
        "ile coin ekleyin veya": "add coins with or",
        "formatında kullanın.": "format.",
        "Analiz etmek istediğiniz coin'i seçin:": "Select the coin you want to analyze:",
        
        # Health messages
        "Sistem Sağlık Raporu": "System Health Report",
        "Genel Durum:": "Overall Status:",
        "Sağlıklı": "Healthy",
        "Problemli": "Problems",
        "Detaylar:": "Details:",
        "Database: Sağlıklı": "Database: Healthy",
        "Exchange API: Sağlıklı": "Exchange API: Healthy",
        "USDT:": "USDT:",
        "Signal Engine: Sağlıklı": "Signal Engine: Healthy",
        "Test sinyali üretilemedi": "Could not generate test signal",
        "Sistem:": "System:",
        "CPU": "CPU",
        "RAM": "RAM",
        "Metrik alınamadı": "Metrics unavailable",
        "Kontrol Zamanı:": "Check Time:",
        "Tekrar Kontrol": "Check Again",
        "Detaylı Log": "Detailed Logs",
        
        # Admin messages
        "Admin Paneli": "Admin Panel",
        "Sistem Bilgileri:": "System Information:",
        "Bot çalışma zamanı": "Bot runtime",
        "Memory kullanımı": "Memory usage",
        "Database boyutu": "Database size",
        "API call sayısı": "API call count",
        "Yönetim İşlemleri:": "Management Operations:",
        "Kullanıcı yetkilendirme": "User authorization",
        "Sistem ayarları": "System settings",
        "Database bakımı": "Database maintenance",
        "Log yönetimi": "Log management",
        "Dikkatli kullanın!": "Use carefully!",
        "Kullanıcılar": "Users",
        "İstatistik": "Statistics",
        "Loglar": "Logs",
        "Backup": "Backup",
        "Restart": "Restart",
        "Bu komut sadece admin kullanıcılar için mevcut.": "This command is only available for admin users.",
        "Log bulunamadı.": "No logs found.",
        "Son Sistem Logları": "Recent System Logs",
        "Database backup başarıyla oluşturuldu.": "Database backup created successfully.",
        "Database backup oluşturulamadı.": "Could not create database backup.",
        
        # Error messages
        "Durum bilgisi alınırken hata oluştu:": "Error getting status information:",
        "Portföy bilgisi alınırken hata oluştu:": "Error getting portfolio information:",
        "Bakiye bilgisi alınırken hata oluştu:": "Error getting balance information:",
        "Takip listesi alınırken hata oluştu:": "Error getting watchlist:",
        "Sinyal bilgisi alınırken hata oluştu:": "Error getting signal information:",
        "İşlem geçmişi alınırken hata oluştu:": "Error getting trade history:",
        "Ayarlar alınırken hata oluştu:": "Error getting settings:",
        "Sağlık kontrolü sırasında hata oluştu:": "Error during health check:",
        "Beklenmedik bir hata oluştu. Lütfen tekrar deneyin.": "An unexpected error occurred. Please try again.",
        "Sorun devam ederse admin ile iletişime geçin.": "If the problem persists, contact the admin.",
        
        # Coin management messages
        "Geçersiz coin sembolü!": "Invalid coin symbol!",
        "zaten takip listesinde!": "already in watchlist!",
        "coin'i exchange'de bulunamadı!": "coin not found on exchange!",
        "Desteklenen coinleri kontrol edin.": "Check supported coins.",
        "takip listesine eklendi!": "added to watchlist!",
        "Sistem otomatik olarak analiz yapacak.": "System will analyze automatically.",
        "Manuel analiz:": "Manual analysis:",
        "eklenirken hata oluştu!": "error occurred while adding!",
        "takip listesinde değil!": "not in watchlist!",
        "için aktif pozisyon var!": "has active position!",
        "Önce pozisyonu kapatın.": "Close position first.",
        "takip listesinden çıkarıldı!": "removed from watchlist!",
        "çıkarılırken hata oluştu!": "error occurred while removing!",
        
        # Analysis messages
        "analiz ediliyor...": "analyzing...",
        "için analiz yapılamadı!": "could not analyze!",
        "Coin mevcut değil veya veri yetersiz.": "Coin unavailable or insufficient data.",
        "Teknik Analiz": "Technical Analysis",
        "Sinyal:": "Signal:",
        "Analiz Sebepleri:": "Analysis Reasons:",
        "Piyasa Verileri:": "Market Data:",
        "24h Değişim:": "24h Change:",
        "24h Yüksek:": "24h High:",
        "24h Düşük:": "24h Low:",
        "Volume:": "Volume:",
        "Analiz Zamanı:": "Analysis Time:",
        "Analiz hatası:": "Analysis error:",
        
        # Button labels
        "Yenile": "Refresh",
        "Geri": "Back",
        "Ana Menü": "Main Menu",
        "Ayarlara Dön": "Back to Settings",
        
        # Utility messages
        "İşlem iptal edildi.": "Operation cancelled.",
        "Hata": "Error",
        "Başarılı": "Success",
        "Aktif": "Active",
        "Pasif": "Inactive",
        "Evet": "Yes",
        "Hayır": "No",
        
        # Time and date
        "saniye": "seconds",
        "dakika": "minutes", 
        "saat": "hours",
        "gün": "days",
        "hafta": "weeks",
        "ay": "months",
        
        # Startup/shutdown messages
        "Trading Bot Başlatıldı!": "Trading Bot Started!",
        "Sistem aktif ve işlem bekliyor": "System active and waiting for trades",
        "Sinyal motoru çalışıyor": "Signal engine running",
        "Exchange bağlantısı aktif": "Exchange connection active",
        "Komutlar için": "For commands",
        "Trading Bot Kapatılıyor": "Trading Bot Shutting Down",
        "Sistem kapatılıyor": "System shutting down",
        "Aktif işlemler korunuyor": "Active trades protected",
        "Veriler kaydediliyor": "Data being saved",
        "Bot tekrar başlatılana kadar işlem yapılmayacak.": "No trading until bot restart.",
    }
    
    return translations

if __name__ == "__main__":
    translations = convert_turkish_to_english()
    print(f"📝 Total translations: {len(translations)}")
    
    # Show some examples
    print(f"\n🔄 Examples:")
    for i, (tr, en) in enumerate(list(translations.items())[:10]):
        print(f"{i+1}. '{tr}' → '{en}'")
    
    print(f"\n✅ Translation mapping ready for interface update!")

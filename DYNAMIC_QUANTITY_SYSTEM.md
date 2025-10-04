# 🎯 Dinamik Quantity Formatlama Sistemi

## 📋 Problem
Hard-coded coin listeleri sürdürülebilir değildi. Her yeni coin için kod değişikliği gerekiyordu:
```python
# ❌ ESKİ SİSTEM - Kötü
if base_currency in ["SUI", "BONK", "SHIB"]:
    formatted_quantity = str(int(available_quantity))
elif base_currency in ["SOL"]:
    formatted_quantity = "{:.3f}".format(available_quantity)
# ... her coin için ayrı kod
```

## ✅ Çözüm: 3 Katmanlı Dinamik Sistem

### 1️⃣ API Metadata (En Yüksek Öncelik)
Crypto.com API'sinden instrument bilgilerini çekip cache'leriz:
```python
# public/get-instruments endpoint'inden:
{
    "CRO_USDT": {
        "quantity_decimals": 0,      # Integer gerekiyor
        "price_decimals": 5,
        "min_quantity": "1",
        "max_quantity": "1000000"
    },
    "BTC_USDT": {
        "quantity_decimals": 8,      # 8 ondalık
        "min_quantity": "0.00000001"
    }
}
```

### 2️⃣ Smart Auto-Detection (Fallback)
API metadata yoksa, quantity değerine göre otomatik tespit:
```python
if quantity >= 1000:      # Meme coins -> integer
    formatted = str(int(quantity))
elif quantity >= 1:       # Normal coins -> 2 decimal
    formatted = "46.00"
elif quantity >= 0.01:    # Small amounts -> 4 decimal
    formatted = "0.0046"
else:                     # Very small -> 8 decimal
    formatted = "0.00000123"
```

### 3️⃣ Simple Fallback (Son Çare)
Her şey başarısız olursa basit 2 decimal:
```python
formatted = "{:.2f}".format(quantity)
```

## 🔧 Kullanım

### exchange/crypto_exchange_api.py
```python
# Otomatik cache sistemi
formatted_qty = self.format_quantity("CRO_USDT", 46.0)
# Output: "46" (API'den quantity_decimals=0 öğrendi)

formatted_qty = self.format_quantity("BTC_USDT", 0.00123456)
# Output: "0.00123456" (API'den quantity_decimals=8 öğrendi)
```

### simple_trade_executor.py
```python
# TP/SL emirleri için
if self.exchange_api:
    # Exchange API'nin dinamik sistemini kullan
    formatted_quantity = self.exchange_api.format_quantity(
        instrument_name, 
        available_quantity
    )
else:
    # Fallback: Smart auto-detection
    if available_quantity >= 1000:
        formatted_quantity = str(int(available_quantity))
    # ...
```

## 🎁 Avantajlar

✅ **Yeni Coin Desteği**: Otomatik, kod değişikliği gerektirmez
✅ **API'den Öğrenme**: Crypto.com'un kendi kurallarını kullanır
✅ **Cache Sistemi**: 1 saat cache, API limitlerini korur
✅ **Fallback Mekanizması**: API'ye erişilmezse akıllı tahmin
✅ **Maintenance-Free**: Crypto.com yeni coin eklediğinde otomatik çalışır

## 📊 Örnek Çıktılar

```
2025-10-04 07:38:23 | INFO | Fetching instrument metadata from Crypto.com API...
2025-10-04 07:38:23 | INFO | ✅ Cached metadata for 247 instruments
2025-10-04 07:38:23 | INFO | Formatted quantity for CRO_USDT: 46.0 -> 46 (decimals: 0, from API)
2025-10-04 07:38:24 | INFO | ✅ TP order placed: 5755600473200455512
2025-10-04 07:38:24 | INFO | ✅ SL order placed: 5755600473200455513
```

## 🔍 Debug

Eğer hala "Invalid quantity format" hatası alırsanız:

1. **API cache'i kontrol edin**:
```python
instruments = exchange_api.get_instruments_info()
print(instruments.get("CRO_USDT"))
```

2. **Manuel test**:
```python
formatted = exchange_api.format_quantity("CRO_USDT", 46.0)
print(f"Formatted: {formatted}")
```

3. **Log'ları kontrol edin**:
```
# "from API" görmelisiniz:
Formatted quantity for CRO_USDT: 46.0 -> 46 (decimals: 0, from API)

# Eğer "auto-detected" görürseniz, API cache çalışmıyor demektir:
Formatted quantity for CRO_USDT: 46.0 -> 46 (decimals: 0, auto-detected)
```

## 🚀 Test

```bash
# Bot'u başlatın
python main.py

# İlk başlatmada otomatik olarak:
# 1. Crypto.com'dan instrument metadata çekilir
# 2. 247 instrument için cache oluşturulur
# 3. 1 saat boyunca cache kullanılır
# 4. Trade emirleri doğru formatla açılır
```

## ⚠️ Notlar

- Cache TTL: 3600 saniye (1 saat)
- Public endpoint kullanır (auth gerektirmez)
- Thread-safe cache mekanizması
- Hataya dayanıklı: API çalışmazsa fallback devreye girer

## 📝 Kod Referansları

- **exchange/crypto_exchange_api.py**: 
  - `get_instruments_info()` (satır 442-495)
  - `format_quantity()` (satır 497-554)

- **simple_trade_executor.py**:
  - `place_tp_sl_orders()` (satır 525-546)
  - Dynamic formatting kullanımı


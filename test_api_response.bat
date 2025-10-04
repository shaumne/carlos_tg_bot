@echo off
REM Manuel API Test - Crypto.com Instruments Endpoint

echo ==========================================
echo 🧪 CRYPTO.COM API MANUEL TEST
echo ==========================================
echo.

echo 📡 Testing public/get-instruments endpoint...
echo.

REM Test the API endpoint
curl -s "https://api.crypto.com/exchange/v1/public/get-instruments" 

echo.
echo ==========================================
echo ✅ Test tamamlandı
echo ==========================================
pause


#!/bin/bash
# Manuel API Test - Crypto.com Instruments Endpoint

echo "=========================================="
echo "🧪 CRYPTO.COM API MANUEL TEST"
echo "=========================================="
echo ""

echo "📡 Testing public/get-instruments endpoint..."
echo ""

# Test the API endpoint
curl -s "https://api.crypto.com/exchange/v1/public/get-instruments" | python3 -m json.tool | head -50

echo ""
echo "=========================================="
echo "✅ Test tamamlandı"
echo "=========================================="


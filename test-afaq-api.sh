#!/bin/bash
# Direct AFAQ SMS API Test Script
# Tests the AFAQ API independently to diagnose issues

API_URL="http://connect-afaq.ntc.org.pk/api/v3/sms/send"
API_KEY="2|OKluq47xKffOFMhXQvQH0EL9p9tRzCmOLtiM8Mri"
PHONE="${1:-923001234567}"  # Use provided number or default

echo "=========================================="
echo "AFAQ SMS API Direct Test"
echo "=========================================="
echo "API URL: $API_URL"
echo "Phone: $PHONE"
echo "API Key: ${API_KEY:0:20}..."
echo ""

# Test 1: Basic payload (current structure)
echo "[Test 1] Current Payload Structure"
echo "-----------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{
    \"recipient\": \"$PHONE\",
    \"sender_id\": \"NTC\",
    \"message\": \"Test OTP: 123456\"
  }")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE"
echo "Response Body:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""

# Test 2: Alternative payload structure (Laravel standard)
echo "[Test 2] Alternative Payload (to/from/body)"
echo "-------------------------------------------"
RESPONSE2=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{
    \"to\": \"$PHONE\",
    \"from\": \"NTC\",
    \"body\": \"Test OTP: 123456\"
  }")

HTTP_CODE2=$(echo "$RESPONSE2" | grep "HTTP_CODE:" | cut -d: -f2)
BODY2=$(echo "$RESPONSE2" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE2"
echo "Response Body:"
echo "$BODY2" | python3 -m json.tool 2>/dev/null || echo "$BODY2"
echo ""

# Test 3: With additional fields
echo "[Test 3] With Additional Fields (report_id, etc)"
echo "------------------------------------------------"
RESPONSE3=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{
    \"recipient\": \"$PHONE\",
    \"sender_id\": \"NTC\",
    \"message\": \"Test OTP: 123456\",
    \"report_id\": 1,
    \"campaign_id\": 1
  }")

HTTP_CODE3=$(echo "$RESPONSE3" | grep "HTTP_CODE:" | cut -d: -f2)
BODY3=$(echo "$RESPONSE3" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE3"
echo "Response Body:"
echo "$BODY3" | python3 -m json.tool 2>/dev/null || echo "$BODY3"
echo ""

# Test 4: Check API health/status endpoint
echo "[Test 4] API Health Check"
echo "-------------------------"
HEALTH=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "${API_URL%/send}/health" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: application/json")

HEALTH_CODE=$(echo "$HEALTH" | grep "HTTP_CODE:" | cut -d: -f2)
HEALTH_BODY=$(echo "$HEALTH" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HEALTH_CODE"
echo "Response:"
echo "$HEALTH_BODY"
echo ""

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "Analysis:"
echo "---------"

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | grep -q '"status":"success"'; then
        echo "✓ Test 1: SUCCESS - Current payload works!"
    else
        echo "✗ Test 1: FAILED - Error: $(echo "$BODY" | grep -o '"message":"[^"]*"')"
    fi
else
    echo "✗ Test 1: HTTP Error $HTTP_CODE"
fi

if [ "$HTTP_CODE2" = "200" ]; then
    if echo "$BODY2" | grep -q '"status":"success"'; then
        echo "✓ Test 2: SUCCESS - Alternative payload works!"
    else
        echo "✗ Test 2: FAILED - Error: $(echo "$BODY2" | grep -o '"message":"[^"]*"')"
    fi
else
    echo "✗ Test 2: HTTP Error $HTTP_CODE2"
fi

if [ "$HTTP_CODE3" = "200" ]; then
    if echo "$BODY3" | grep -q '"status":"success"'; then
        echo "✓ Test 3: SUCCESS - Payload with additional fields works!"
    else
        echo "✗ Test 3: FAILED - Error: $(echo "$BODY3" | grep -o '"message":"[^"]*"')"
    fi
else
    echo "✗ Test 3: HTTP Error $HTTP_CODE3"
fi

echo ""
echo "Next Steps:"
echo "----------"
echo "1. If any test succeeded, update helpers.py to use that payload structure"
echo "2. If all failed, check AFAQ server logs: /var/log/laravel.log"
echo "3. Verify AFAQ database has required data: mysql -u root -p afaq_db"
echo ""

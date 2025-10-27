#!/bin/bash

echo "=== Testing SELF_EMPLOYED Mode for All Banks ==="
echo ""

# Test 1: TTB (Thanachart)
echo "1. TTB (Thanachart) - AccountStatement_24102025.pdf"
curl -s -X POST http://localhost:8001/api/v1/analyze-upload \
  -F "pdf_file=@Test/AccountStatement_24102025.pdf" \
  -F "user_id=test_ttb_self" \
  -F "income_type=self_employed" | jq -r '.analysis | "   Amount: \(.detected_amount) THB | Months: \(.months_detected) | Confidence: \(.confidence) | Approved: \(.approved)"'
echo ""

# Test 2: KBANK (Kasikorn)
echo "2. KBANK (Kasikorn) - kbank27051987.pdf"
curl -s -X POST http://localhost:8001/api/v1/analyze-upload \
  -F "pdf_file=@Test/kbank27051987.pdf" \
  -F "pdf_password=27051987" \
  -F "user_id=test_kbank_self" \
  -F "income_type=self_employed" | jq -r '.analysis | "   Amount: \(.detected_amount) THB | Months: \(.months_detected) | Confidence: \(.confidence) | Approved: \(.approved)"'
echo ""

# Test 3: SCB (Siam Commercial)
echo "3. SCB (Siam Commercial) - scb27051987.pdf"
curl -s -X POST http://localhost:8001/api/v1/analyze-upload \
  -F "pdf_file=@Test/scb27051987.pdf" \
  -F "pdf_password=27051987" \
  -F "user_id=test_scb_self" \
  -F "income_type=self_employed" | jq -r '.analysis | "   Amount: \(.detected_amount) THB | Months: \(.months_detected) | Confidence: \(.confidence) | Approved: \(.approved)"'
echo ""

echo "=== Test Complete ==="

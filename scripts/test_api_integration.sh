#!/bin/bash
# API and Database Integration Test Script
# Tests full stack: API endpoints + Database persistence + Audit logging
#
# Usage: ./scripts/test_api_integration.sh

set -e  # Exit on error

# Configuration
API_URL="${API_URL:-http://localhost:8001}"
DB_CONTAINER="${DB_CONTAINER:-bank_pdf_db}"
DB_NAME="${DB_NAME:-bank_statements}"
DB_USER="${DB_USER:-postgres}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print colored output
print_test() {
    echo -e "${BLUE}[TEST $((TESTS_RUN + 1))]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED+=1))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((TESTS_FAILED+=1))
}

print_info() {
    echo -e "${YELLOW}ℹ INFO:${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo "=== Checking Prerequisites ==="
    
    # Check if Docker is running
    if ! docker ps &> /dev/null; then
        echo -e "${RED}Error: Docker is not running${NC}"
        exit 1
    fi
    print_success "Docker is running"
    
    # Check if API container is running
    if ! docker ps --format "{{.Names}}" | grep -q "bank_statement_api"; then
        echo -e "${RED}Error: API container is not running${NC}"
        echo "Start with: docker compose up -d"
        exit 1
    fi
    print_success "API container is running"
    
    # Check if DB container is running
    if ! docker ps --format "{{.Names}}" | grep -q "bank_pdf_db"; then
        echo -e "${RED}Error: Database container is not running${NC}"
        exit 1
    fi
    print_success "Database container is running"
    
    # Check if API is responsive
    if ! curl -s "$API_URL/api/v1/health" &> /dev/null; then
        echo -e "${RED}Error: API is not responsive at $API_URL${NC}"
        exit 1
    fi
    print_success "API is responsive"
    
    echo ""
}

# Create test PDF
create_test_pdf() {
    local pdf_file="$1"
    cat > "$pdf_file" << 'EOF'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Bank Statement) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
409
%%EOF
EOF
}

# Query database
query_db() {
    local query="$1"
    local allow_errors="${2:-false}"

    if [ "$allow_errors" = "true" ]; then
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "$query"
    else
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "$query" 2>/dev/null
    fi
}

# Clean test data from database
cleanup_test_data() {
    local user_id="$1"
    print_info "Cleaning up test data for user: $user_id"
    query_db "DELETE FROM audit_logs WHERE user_id = '$user_id';" > /dev/null
    query_db "DELETE FROM analyses WHERE user_id = '$user_id';" > /dev/null
}

# Test 1: Health Endpoint
test_health_endpoint() {
    ((TESTS_RUN+=1))
    print_test "Health Endpoint"
    
    response=$(curl -s "$API_URL/api/v1/health")
    
    if echo "$response" | grep -q '"status":"healthy"'; then
        print_success "Health endpoint returns healthy status"
    else
        print_fail "Health endpoint did not return healthy status"
        return 1
    fi
    
    if echo "$response" | grep -q '"service":"bank-statement-analyzer"'; then
        print_success "Service name is correct"
    else
        print_fail "Service name is incorrect"
        return 1
    fi
}

# Test 2: Analyze Upload - Basic
test_analyze_upload_basic() {
    ((TESTS_RUN+=1))
    print_test "Analyze Upload - Basic Request"
    
    local test_user="test_integration_basic"
    local test_pdf="/tmp/test_statement.pdf"
    
    # Cleanup first
    cleanup_test_data "$test_user"
    
    # Create test PDF
    create_test_pdf "$test_pdf"
    
    # Make API request
    response=$(curl -s -X POST "$API_URL/api/v1/analyze-upload" \
        -F "pdf_file=@$test_pdf" \
        -F "user_id=$test_user")
    
    # Verify API response
    if echo "$response" | grep -q '"success":true'; then
        print_success "API returned success response"
    else
        print_fail "API did not return success"
        echo "Response: $response"
        rm -f "$test_pdf"
        return 1
    fi
    
    if echo "$response" | grep -q "\"user_id\":\"$test_user\""; then
        print_success "User ID matches in response"
    else
        print_fail "User ID mismatch in response"
    fi
    
    # Verify database entry
    sleep 1  # Wait for async database write
    
    db_count=$(query_db "SELECT COUNT(*) FROM analyses WHERE user_id = '$test_user';")
    if [ "${db_count// /}" = "1" ]; then
        print_success "Analysis saved to database"
    else
        print_fail "Analysis not found in database (count: $db_count)"
    fi
    
    # Verify audit log
    audit_count=$(query_db "SELECT COUNT(*) FROM audit_logs WHERE user_id = '$test_user' AND action = 'analyze_upload';")
    if [ "${audit_count// /}" = "1" ]; then
        print_success "Audit log created"
    else
        print_fail "Audit log not found (count: $audit_count)"
    fi
    
    # Verify audit status
    audit_status=$(query_db "SELECT status FROM audit_logs WHERE user_id = '$test_user' ORDER BY created_at DESC LIMIT 1;")
    if echo "$audit_status" | grep -q "success"; then
        print_success "Audit status is 'success'"
    else
        print_fail "Audit status is not 'success': $audit_status"
    fi
    
    # Cleanup
    cleanup_test_data "$test_user"
    rm -f "$test_pdf"
}

# Test 3: Analyze Upload - With Parameters
test_analyze_upload_with_params() {
    ((TESTS_RUN+=1))
    print_test "Analyze Upload - With Parameters"
    
    local test_user="test_integration_params"
    local test_pdf="/tmp/test_statement_params.pdf"
    
    cleanup_test_data "$test_user"
    create_test_pdf "$test_pdf"
    
    # Make API request with all parameters
    response=$(curl -s -X POST "$API_URL/api/v1/analyze-upload" \
        -F "pdf_file=@$test_pdf" \
        -F "user_id=$test_user" \
        -F "expected_gross=50000.00" \
        -F "employer=Test Company Ltd" \
        -F "pvd_rate=0.03" \
        -F "extra_deductions=500.00")
    
    if echo "$response" | grep -q '"success":true'; then
        print_success "API accepted request with parameters"
    else
        print_fail "API rejected request with parameters"
        rm -f "$test_pdf"
        return 1
    fi
    
    # Verify database stores parameters
    sleep 1
    
    db_employer=$(query_db "SELECT employer FROM analyses WHERE user_id = '$test_user';")
    if echo "$db_employer" | grep -q "Test Company Ltd"; then
        print_success "Employer parameter saved to database"
    else
        print_fail "Employer not saved correctly: $db_employer"
    fi
    
    db_expected=$(query_db "SELECT expected_gross FROM analyses WHERE user_id = '$test_user';")
    if echo "$db_expected" | grep -q "50000"; then
        print_success "Expected gross saved to database"
    else
        print_fail "Expected gross not saved: $db_expected"
    fi
    
    cleanup_test_data "$test_user"
    rm -f "$test_pdf"
}

# Test 4: Database Constraints
test_database_constraints() {
    ((TESTS_RUN+=1))
    print_test "Database Constraints Validation"
    
    local test_user="test_constraints"
    
    cleanup_test_data "$test_user"
    
    # Insert test data
    query_db "INSERT INTO analyses (user_id, confidence, transactions_analyzed) VALUES ('$test_user', 'high', 100);" > /dev/null
    
    # Verify confidence constraint
    confidence=$(query_db "SELECT confidence FROM analyses WHERE user_id = '$test_user';")
    if echo "$confidence" | grep -q "high"; then
        print_success "Confidence constraint allows valid values"
    else
        print_fail "Confidence value incorrect: $confidence"
    fi
    
    # Try invalid confidence (should fail)
    if query_db "INSERT INTO analyses (user_id, confidence, transactions_analyzed) VALUES ('$test_user', 'invalid', 100);" "true" 2>&1 | grep -q "violates check constraint"; then
        print_success "Database rejects invalid confidence values"
    else
        print_fail "Database did not enforce confidence constraint"
    fi
    
    # Verify timestamps
    created_at=$(query_db "SELECT created_at FROM analyses WHERE user_id = '$test_user';")
    if [ -n "$created_at" ] && [ "$created_at" != " " ]; then
        print_success "Timestamp auto-generated"
    else
        print_fail "Timestamp not generated"
    fi
    
    cleanup_test_data "$test_user"
}

# Test 5: Concurrent Requests
test_concurrent_requests() {
    ((TESTS_RUN+=1))
    print_test "Concurrent Requests Handling"
    
    local test_pdf="/tmp/test_concurrent.pdf"
    create_test_pdf "$test_pdf"
    
    # Cleanup
    for i in 1 2 3; do
        cleanup_test_data "test_concurrent_$i"
    done
    
    # Send 3 concurrent requests
    for i in 1 2 3; do
        curl -s -X POST "$API_URL/api/v1/analyze-upload" \
            -F "pdf_file=@$test_pdf" \
            -F "user_id=test_concurrent_$i" &
    done
    
    # Wait for all requests to complete
    wait
    sleep 2  # Wait for database writes
    
    # Verify all saved
    total_count=$(query_db "SELECT COUNT(*) FROM analyses WHERE user_id LIKE 'test_concurrent_%';")
    if [ "${total_count// /}" = "3" ]; then
        print_success "All concurrent requests processed"
    else
        print_fail "Not all concurrent requests saved (count: $total_count)"
    fi
    
    # Verify unique analysis IDs
    unique_ids=$(query_db "SELECT COUNT(DISTINCT id) FROM analyses WHERE user_id LIKE 'test_concurrent_%';")
    if [ "${unique_ids// /}" = "3" ]; then
        print_success "Each request got unique ID"
    else
        print_fail "Analysis IDs not unique (unique count: $unique_ids)"
    fi
    
    # Cleanup
    for i in 1 2 3; do
        cleanup_test_data "test_concurrent_$i"
    done
    rm -f "$test_pdf"
}

# Test 6: Audit Log Details
test_audit_log_details() {
    ((TESTS_RUN+=1))
    print_test "Audit Log Details"
    
    local test_user="test_audit_details"
    local test_pdf="/tmp/test_audit.pdf"
    
    cleanup_test_data "$test_user"
    create_test_pdf "$test_pdf"
    
    # Make request
    curl -s -X POST "$API_URL/api/v1/analyze-upload" \
        -F "pdf_file=@$test_pdf" \
        -F "user_id=$test_user" > /dev/null
    
    sleep 1
    
    # Verify audit log fields
    action=$(query_db "SELECT action FROM audit_logs WHERE user_id = '$test_user';")
    if echo "$action" | grep -q "analyze_upload"; then
        print_success "Audit action recorded correctly"
    else
        print_fail "Audit action incorrect: $action"
    fi
    
    # Verify processing time recorded
    processing_time=$(query_db "SELECT processing_time_ms FROM audit_logs WHERE user_id = '$test_user';")
    if [ -n "$processing_time" ] && [ "$processing_time" != " " ]; then
        print_success "Processing time recorded"
    else
        print_info "Processing time not recorded (optional)"
    fi
    
    # Verify analysis_id foreign key
    analysis_id=$(query_db "SELECT analysis_id FROM audit_logs WHERE user_id = '$test_user';")
    if [ -n "$analysis_id" ] && [ "$analysis_id" != " " ]; then
        print_success "Analysis ID linked in audit log"
    else
        print_info "Analysis ID not linked (may be NULL on error)"
    fi
    
    cleanup_test_data "$test_user"
    rm -f "$test_pdf"
}

# Test 7: API Error Handling
test_api_error_handling() {
    ((TESTS_RUN+=1))
    print_test "API Error Handling"
    
    # Test missing required field
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/analyze-upload" \
        -F "pdf_file=@/etc/hosts")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "422" ]; then
        print_success "API returns 422 for missing required field"
    else
        print_fail "API returned $http_code instead of 422"
    fi
    
    # Test invalid file type
    echo "not a pdf" > /tmp/invalid.txt
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/analyze-upload" \
        -F "pdf_file=@/tmp/invalid.txt" \
        -F "user_id=test_invalid")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "400" ] || [ "$http_code" = "422" ]; then
        print_success "API rejects invalid file type"
    else
        print_info "API returned $http_code for invalid file (may process anyway)"
    fi
    
    rm -f /tmp/invalid.txt
}

# Print summary
print_summary() {
    echo ""
    echo "========================================"
    echo "         TEST SUMMARY"
    echo "========================================"
    echo -e "Tests Run:    ${BLUE}$TESTS_RUN${NC}"
    echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
    echo "========================================"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo "========================================"
    echo "  API & Database Integration Tests"
    echo "========================================"
    echo ""
    
    check_prerequisites
    
    test_health_endpoint
    echo ""
    
    test_analyze_upload_basic
    echo ""
    
    test_analyze_upload_with_params
    echo ""
    
    test_database_constraints
    echo ""
    
    test_concurrent_requests
    echo ""
    
    test_audit_log_details
    echo ""
    
    test_api_error_handling
    echo ""
    
    print_summary
}

# Run main
main
exit $?

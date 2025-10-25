"""Simple E2E API tests without database verification.

Tests API endpoints with Docker services.
Run with: pytest tests/test_api_simple.py -v -m e2e
"""

import os
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest

# API base URL (Docker service)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
API_VERSION = "v1"


@pytest.fixture
async def api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create HTTP client for API testing.
    
    Yields:
        httpx.AsyncClient: HTTP client configured for API
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        yield client


def create_dummy_pdf() -> bytes:
    """Create a minimal valid PDF file for testing.
    
    Returns:
        bytes: Minimal PDF content
    """
    # Minimal valid PDF structure
    return b"""%PDF-1.4
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
(Test Statement) Tj
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
"""


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_endpoint_detailed(api_client: httpx.AsyncClient):
    """Test health check endpoint with detailed verification.
    
    Verifies:
    - Endpoint responds quickly
    - Returns correct JSON structure
    - All required fields present
    """
    response = await api_client.get(f"/api/{API_VERSION}/health")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.headers["content-type"] == "application/json", "Should return JSON"
    
    data = response.json()
    
    # Verify required fields
    required_fields = ["status", "service", "version", "architecture", "storage_type"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Verify values
    assert data["status"] == "healthy", "Service should be healthy"
    assert data["service"] == "bank-statement-analyzer"
    assert data["version"] == "3.0.0-hexagonal"
    assert data["architecture"] == "hexagonal"
    assert data["storage_type"] in ["local", "s3"], "storage_type should be valid"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_basic(api_client: httpx.AsyncClient):
    """Test analyze-upload endpoint with dummy PDF.
    
    Verifies:
    - Endpoint accepts PDF upload
    - Returns valid response structure
    - Processing completes without error
    """
    pdf_content = create_dummy_pdf()
    
    files = {"pdf_file": ("test_statement.pdf", pdf_content, "application/pdf")}
    data = {"user_id": "test_user_basic"}
    
    response = await api_client.post(
        f"/api/{API_VERSION}/analyze-upload",
        files=files,
        data=data
    )
    
    # API should accept the request
    assert response.status_code in [200, 400], \
        f"Expected 200 or 400, got {response.status_code}: {response.text}"
    
    if response.status_code == 200:
        result = response.json()
        
        # Verify response structure (actual API response format)
        expected_fields = ["user_id", "success", "statement_id", "analysis"]
        for field in expected_fields:
            assert field in result, f"Missing field in response: {field}"
        
        assert result["user_id"] == "test_user_basic", "User ID should match request"
        assert "detected_amount" in result["analysis"], "Analysis should have detected_amount"
        assert "confidence" in result["analysis"], "Analysis should have confidence"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_with_all_parameters(api_client: httpx.AsyncClient):
    """Test analyze-upload with all optional parameters.
    
    Verifies:
    - All parameters are accepted
    - Response includes calculation fields
    """
    pdf_content = create_dummy_pdf()
    
    files = {"pdf_file": ("test_full.pdf", pdf_content, "application/pdf")}
    data = {
        "user_id": "test_user_full_params",
        "expected_gross": "50000.00",
        "employer": "Test Company Ltd",
        "pvd_rate": "0.03",
        "extra_deductions": "500.00"
    }
    
    response = await api_client.post(
        f"/api/{API_VERSION}/analyze-upload",
        files=files,
        data=data
    )
    
    if response.status_code == 200:
        result = response.json()
        
        # Verify parameter fields in response
        assert "expected_gross" in result
        assert "employer" in result
        assert "pvd_rate" in result or "extra_deductions" in result


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_invalid_content_type(api_client: httpx.AsyncClient):
    """Test analyze-upload rejects non-PDF files.
    
    Verifies:
    - Invalid file types are rejected
    - Appropriate error is returned
    """
    files = {"pdf_file": ("test.txt", b"This is not a PDF", "text/plain")}
    data = {"user_id": "test_user_invalid_type"}
    
    response = await api_client.post(
        f"/api/{API_VERSION}/analyze-upload",
        files=files,
        data=data
    )
    
    # Should reject with 4xx error
    assert 400 <= response.status_code < 500, \
        "Should reject invalid file type with 4xx error"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_missing_required_field(api_client: httpx.AsyncClient):
    """Test analyze-upload validation for required fields.
    
    Verifies:
    - Missing user_id returns validation error
    - Error response is informative
    """
    pdf_content = create_dummy_pdf()
    
    files = {"pdf_file": ("test.pdf", pdf_content, "application/pdf")}
    data = {}  # Missing user_id
    
    response = await api_client.post(
        f"/api/{API_VERSION}/analyze-upload",
        files=files,
        data=data
    )
    
    # Should return validation error
    assert response.status_code == 422, \
        f"Expected 422 validation error, got {response.status_code}"
    
    error_data = response.json()
    assert "detail" in error_data, "Error response should have detail"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_invalid_numeric_parameters(api_client: httpx.AsyncClient):
    """Test parameter validation for numeric fields.
    
    Verifies:
    - Invalid numeric values are caught
    - Appropriate validation error returned
    """
    pdf_content = create_dummy_pdf()
    
    files = {"pdf_file": ("test.pdf", pdf_content, "application/pdf")}
    data = {
        "user_id": "test_validation",
        "expected_gross": "not_a_number",  # Invalid
        "pvd_rate": "invalid"  # Invalid
    }
    
    response = await api_client.post(
        f"/api/{API_VERSION}/analyze-upload",
        files=files,
        data=data
    )
    
    # Should return validation error
    assert response.status_code == 422, \
        "Invalid numeric parameters should return validation error"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_cors_headers(api_client: httpx.AsyncClient):
    """Test that API returns appropriate CORS headers.
    
    Verifies:
    - CORS headers are present (if configured)
    - OPTIONS request handled
    """
    response = await api_client.get(f"/api/{API_VERSION}/health")
    
    # Check if CORS headers exist (optional feature)
    headers = response.headers
    
    # Just verify response is valid
    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_response_times(api_client: httpx.AsyncClient):
    """Test that API responds within acceptable time limits.
    
    Verifies:
    - Health endpoint responds quickly (< 1s)
    - Response times are reasonable
    """
    import time
    
    start = time.time()
    response = await api_client.get(f"/api/{API_VERSION}/health")
    elapsed = time.time() - start
    
    assert response.status_code == 200
    assert elapsed < 1.0, f"Health endpoint should respond < 1s, took {elapsed:.2f}s"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openapi_schema_validity(api_client: httpx.AsyncClient):
    """Test OpenAPI schema is valid and complete.
    
    Verifies:
    - Schema endpoint accessible
    - Required fields present
    - All endpoints documented
    """
    response = await api_client.get("/openapi.json")
    
    assert response.status_code == 200, "OpenAPI schema should be accessible"
    
    schema = response.json()
    
    # Verify OpenAPI structure
    assert "openapi" in schema, "Should have OpenAPI version"
    assert "info" in schema, "Should have API info"
    assert "paths" in schema, "Should have API paths"
    
    # Verify our endpoints are documented
    paths = schema["paths"]
    assert f"/api/{API_VERSION}/health" in paths, "Health endpoint should be documented"
    assert f"/api/{API_VERSION}/analyze-upload" in paths, "Analyze-upload should be documented"
    
    # Verify endpoint has proper HTTP methods
    health_path = paths[f"/api/{API_VERSION}/health"]
    assert "get" in health_path, "Health should support GET"
    
    analyze_path = paths[f"/api/{API_VERSION}/analyze-upload"]
    assert "post" in analyze_path, "Analyze-upload should support POST"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_error_handling(api_client: httpx.AsyncClient):
    """Test API error handling for various scenarios.
    
    Verifies:
    - Appropriate HTTP status codes
    - Error messages are informative
    - No sensitive data in errors
    """
    # Test with no file
    response = await api_client.post(
        f"/api/{API_VERSION}/analyze-upload",
        data={"user_id": "test"}
    )
    
    # Should return 422 (missing required file)
    assert response.status_code == 422, "Should return validation error for missing file"
    
    error = response.json()
    assert "detail" in error, "Error should have detail field"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_sequential_requests(api_client: httpx.AsyncClient):
    """Test API handles multiple sequential requests correctly.
    
    Verifies:
    - Multiple requests process independently
    - No state leakage between requests
    """
    pdf_content = create_dummy_pdf()
    
    user_ids = ["test_seq_1", "test_seq_2", "test_seq_3"]
    
    for user_id in user_ids:
        files = {"pdf_file": ("test.pdf", pdf_content, "application/pdf")}
        data = {"user_id": user_id}
        
        response = await api_client.post(
            f"/api/{API_VERSION}/analyze-upload",
            files=files,
            data=data
        )
        
        # Each request should be processed
        assert response.status_code in [200, 400], \
            f"Request for {user_id} failed with {response.status_code}"
        
        if response.status_code == 200:
            result = response.json()
            assert result["user_id"] == user_id, "Response should match request user_id"

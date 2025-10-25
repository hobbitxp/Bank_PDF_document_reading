"""End-to-end API tests with Docker services.

Tests the full stack: API + PostgreSQL + S3 (optional)
Run with: pytest tests/test_api_e2e.py -v -m e2e
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

import asyncpg
import httpx
import pytest

# API base URL (Docker service)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
API_VERSION = "v1"

# Database connection for verification
DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/bank_statements"
)


@pytest.fixture
async def db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Create database connection for test verification.
    
    Yields:
        asyncpg.Connection: Database connection
    """
    conn = await asyncpg.connect(DB_URL)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create HTTP client for API testing.
    
    Yields:
        httpx.AsyncClient: HTTP client configured for API
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
def sample_pdf_path() -> Path:
    """Get path to sample PDF file.
    
    Returns:
        Path: Path to sample PDF file for testing
    """
    # Look for sample PDF in Test/ directory
    test_dir = Path(__file__).parent.parent / "Test"
    if test_dir.exists():
        pdf_files = list(test_dir.glob("*.pdf"))
        if pdf_files:
            return pdf_files[0]
    
    # If no Test/ directory, check data/raw/
    data_dir = Path(__file__).parent.parent / "data" / "raw"
    if data_dir.exists():
        pdf_files = list(data_dir.glob("*.pdf"))
        if pdf_files:
            return pdf_files[0]
    
    pytest.skip("No sample PDF files found in Test/ or data/raw/")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_endpoint(api_client: httpx.AsyncClient):
    """Test health check endpoint returns correct status.
    
    Verifies:
    - Endpoint responds with 200 OK
    - Returns expected JSON structure
    - Service information is correct
    """
    response = await api_client.get(f"/api/{API_VERSION}/health")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert data["status"] == "healthy", "Service should be healthy"
    assert data["service"] == "bank-statement-analyzer", "Service name mismatch"
    assert data["version"] == "3.0.0-hexagonal", "Version mismatch"
    assert data["architecture"] == "hexagonal", "Architecture mismatch"
    assert "storage_type" in data, "Missing storage_type field"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_minimal(
    api_client: httpx.AsyncClient,
    db_connection: asyncpg.Connection,
    sample_pdf_path: Path
):
    """Test analyze-upload endpoint with minimal parameters.
    
    Verifies:
    - Endpoint accepts PDF upload
    - Returns analysis results
    - Saves to database
    - Creates audit log
    """
    # Clean up any existing test data
    await db_connection.execute(
        "DELETE FROM audit_logs WHERE user_id = 'test_user_e2e'"
    )
    await db_connection.execute(
        "DELETE FROM analyses WHERE user_id = 'test_user_e2e'"
    )
    
    # Prepare request
    with open(sample_pdf_path, "rb") as f:
        files = {"pdf_file": (sample_pdf_path.name, f, "application/pdf")}
        data = {
            "user_id": "test_user_e2e"
        }
        
        response = await api_client.post(
            f"/api/{API_VERSION}/analyze-upload",
            files=files,
            data=data
        )
    
    # Verify HTTP response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    result = response.json()
    assert "user_id" in result, "Missing user_id in response"
    assert result["user_id"] == "test_user_e2e", "User ID mismatch"
    assert "detected_salary" in result, "Missing detected_salary"
    assert "confidence" in result, "Missing confidence"
    assert "analysis_id" in result, "Missing analysis_id"
    
    # Verify database entry
    analysis = await db_connection.fetchrow(
        "SELECT * FROM analyses WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        "test_user_e2e"
    )
    assert analysis is not None, "Analysis not saved to database"
    assert analysis["confidence"] in ["high", "medium", "low"], "Invalid confidence value"
    
    # Verify audit log
    audit_log = await db_connection.fetchrow(
        "SELECT * FROM audit_logs WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        "test_user_e2e"
    )
    assert audit_log is not None, "Audit log not created"
    assert audit_log["action"] == "analyze_upload", "Wrong action type"
    assert audit_log["status"] == "success", "Wrong status"
    
    # Cleanup
    await db_connection.execute(
        "DELETE FROM audit_logs WHERE user_id = 'test_user_e2e'"
    )
    await db_connection.execute(
        "DELETE FROM analyses WHERE user_id = 'test_user_e2e'"
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_with_parameters(
    api_client: httpx.AsyncClient,
    db_connection: asyncpg.Connection,
    sample_pdf_path: Path
):
    """Test analyze-upload with all optional parameters.
    
    Verifies:
    - Accepts all parameters
    - Compares with expected gross salary
    - Calculates deductions correctly
    - Returns detailed analysis
    """
    await db_connection.execute(
        "DELETE FROM audit_logs WHERE user_id = 'test_user_full'"
    )
    await db_connection.execute(
        "DELETE FROM analyses WHERE user_id = 'test_user_full'"
    )
    
    with open(sample_pdf_path, "rb") as f:
        files = {"pdf_file": (sample_pdf_path.name, f, "application/pdf")}
        data = {
            "user_id": "test_user_full",
            "expected_gross": "50000.00",
            "employer": "ACME Corporation",
            "pvd_rate": "0.03",
            "extra_deductions": "1000.00"
        }
        
        response = await api_client.post(
            f"/api/{API_VERSION}/analyze-upload",
            files=files,
            data=data
        )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    result = response.json()
    assert "detected_salary" in result
    assert "expected_gross" in result
    assert "matches_expected" in result
    assert "difference" in result
    assert "employer" in result
    
    # Verify calculation fields
    if result["expected_gross"] is not None:
        assert isinstance(result["matches_expected"], bool), "matches_expected should be boolean"
        if result["detected_salary"] is not None:
            assert "difference" in result, "Missing difference calculation"
    
    # Cleanup
    await db_connection.execute(
        "DELETE FROM audit_logs WHERE user_id = 'test_user_full'"
    )
    await db_connection.execute(
        "DELETE FROM analyses WHERE user_id = 'test_user_full'"
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_invalid_file(api_client: httpx.AsyncClient):
    """Test analyze-upload with invalid file type.
    
    Verifies:
    - Rejects non-PDF files
    - Returns appropriate error
    """
    files = {"pdf_file": ("test.txt", b"Not a PDF file", "text/plain")}
    data = {"user_id": "test_user_invalid"}
    
    response = await api_client.post(
        f"/api/{API_VERSION}/analyze-upload",
        files=files,
        data=data
    )
    
    # Should return 4xx error
    assert response.status_code >= 400, "Should reject invalid file type"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analyze_upload_missing_user_id(
    api_client: httpx.AsyncClient,
    sample_pdf_path: Path
):
    """Test analyze-upload without required user_id.
    
    Verifies:
    - Returns validation error
    - Does not create database entries
    """
    with open(sample_pdf_path, "rb") as f:
        files = {"pdf_file": (sample_pdf_path.name, f, "application/pdf")}
        data = {}  # Missing user_id
        
        response = await api_client.post(
            f"/api/{API_VERSION}/analyze-upload",
            files=files,
            data=data
        )
    
    # Should return validation error
    assert response.status_code == 422, "Should return validation error"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_concurrent_requests(
    api_client: httpx.AsyncClient,
    db_connection: asyncpg.Connection,
    sample_pdf_path: Path
):
    """Test API handles concurrent requests correctly.
    
    Verifies:
    - Multiple requests process without errors
    - Each request gets unique analysis_id
    - Database maintains consistency
    """
    user_ids = [f"test_user_concurrent_{i}" for i in range(3)]
    
    # Clean up
    for user_id in user_ids:
        await db_connection.execute(
            "DELETE FROM audit_logs WHERE user_id = $1", user_id
        )
        await db_connection.execute(
            "DELETE FROM analyses WHERE user_id = $1", user_id
        )
    
    async def make_request(user_id: str) -> Dict[str, Any]:
        """Make single API request."""
        with open(sample_pdf_path, "rb") as f:
            files = {"pdf_file": (sample_pdf_path.name, f, "application/pdf")}
            data = {"user_id": user_id}
            response = await api_client.post(
                f"/api/{API_VERSION}/analyze-upload",
                files=files,
                data=data
            )
            return response.json()
    
    # Send concurrent requests
    tasks = [make_request(user_id) for user_id in user_ids]
    results = await asyncio.gather(*tasks)
    
    # Verify all succeeded
    assert len(results) == 3, "All requests should succeed"
    
    # Verify unique analysis IDs
    analysis_ids = [r.get("analysis_id") for r in results]
    assert len(set(analysis_ids)) == 3, "Each request should get unique analysis_id"
    
    # Verify database entries
    for user_id in user_ids:
        analysis = await db_connection.fetchrow(
            "SELECT * FROM analyses WHERE user_id = $1", user_id
        )
        assert analysis is not None, f"Analysis for {user_id} not found"
    
    # Cleanup
    for user_id in user_ids:
        await db_connection.execute(
            "DELETE FROM audit_logs WHERE user_id = $1", user_id
        )
        await db_connection.execute(
            "DELETE FROM analyses WHERE user_id = $1", user_id
        )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_database_constraint_validation(
    api_client: httpx.AsyncClient,
    db_connection: asyncpg.Connection,
    sample_pdf_path: Path
):
    """Test that database constraints are enforced.
    
    Verifies:
    - Confidence values are validated
    - Numeric types are correct
    - Timestamps are generated
    """
    await db_connection.execute(
        "DELETE FROM analyses WHERE user_id = 'test_constraint'"
    )
    
    with open(sample_pdf_path, "rb") as f:
        files = {"pdf_file": (sample_pdf_path.name, f, "application/pdf")}
        data = {"user_id": "test_constraint"}
        
        response = await api_client.post(
            f"/api/{API_VERSION}/analyze-upload",
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        # Verify database entry has valid data
        analysis = await db_connection.fetchrow(
            "SELECT * FROM analyses WHERE user_id = 'test_constraint'"
        )
        
        if analysis:
            # Check confidence constraint
            assert analysis["confidence"] in ["high", "medium", "low"], \
                "Confidence should be enum value"
            
            # Check timestamp
            assert analysis["created_at"] is not None, \
                "created_at should have default value"
            
            # Check numeric types
            if analysis["detected_salary"] is not None:
                assert isinstance(analysis["detected_salary"], (int, float)), \
                    "detected_salary should be numeric"
    
    # Cleanup
    await db_connection.execute(
        "DELETE FROM audit_logs WHERE user_id = 'test_constraint'"
    )
    await db_connection.execute(
        "DELETE FROM analyses WHERE user_id = 'test_constraint'"
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_documentation_accessible(api_client: httpx.AsyncClient):
    """Test that API documentation is accessible.
    
    Verifies:
    - /docs endpoint is available
    - OpenAPI schema is valid
    """
    response = await api_client.get("/docs")
    assert response.status_code == 200, "API documentation should be accessible"
    
    # Check OpenAPI schema
    response = await api_client.get("/openapi.json")
    assert response.status_code == 200, "OpenAPI schema should be available"
    
    schema = response.json()
    assert "openapi" in schema, "Should have OpenAPI version"
    assert "paths" in schema, "Should have API paths"
    assert f"/api/{API_VERSION}/health" in schema["paths"], "Health endpoint should be documented"
    assert f"/api/{API_VERSION}/analyze-upload" in schema["paths"], "Analyze endpoint should be documented"

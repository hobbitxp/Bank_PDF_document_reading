"""
Integration tests for PostgresDatabase adapter.

REQUIRES: Running PostgreSQL instance
Run with: docker compose up -d db
Skip by default: pytest tests/ -v (skips @pytest.mark.integration)
Run explicitly: pytest tests/ -v -m integration

Environment variables required:
- TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/test_db
"""
import pytest
import os
from uuid import UUID

from infrastructure.database.postgres_adapter import PostgresDatabase


# Skip these tests unless explicitly requested
pytestmark = pytest.mark.integration


@pytest.fixture
async def db_connection():
    """
    Fixture for real database connection.
    
    Requires TEST_DATABASE_URL environment variable.
    Example: postgresql://postgres:postgres@localhost:5432/test_bank_statements
    """
    db_url = os.getenv("TEST_DATABASE_URL")
    
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not set - skipping integration tests")
    
    db = PostgresDatabase(
        connection_string=db_url,
        min_pool_size=2,
        max_pool_size=5
    )
    
    await db.connect()
    
    yield db
    
    # Cleanup: Close connection after test
    if db.pool:
        await db.pool.close()


@pytest.mark.asyncio
async def test_real_database_connection(db_connection):
    """Test actual connection to PostgreSQL."""
    db = db_connection
    
    assert db.pool is not None
    
    # Test simple query
    async with db.pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1


@pytest.mark.asyncio
async def test_save_and_retrieve_analysis(db_connection):
    """Test saving and retrieving analysis from real database."""
    db = db_connection
    
    # Save test analysis
    analysis_id = await db.save_analysis(
        user_id="test-user-integration",
        detected_salary=50000.00,
        confidence="high",
        transactions_analyzed=100,
        credit_transactions=50,
        debit_transactions=50,
        clusters_found=5,
        top_candidates_count=10,
        expected_gross=50000.00,
        matches_expected=True,
        difference=0.0,
        difference_percentage=0.0,
        employer="บริษัททดสอบ",
        pvd_rate=3.0,
        extra_deductions=1500.00,
        pdf_filename="test_integration.pdf",
        pages_processed=5,
        masked_items=20,
        metadata={"test": "integration", "status": "success"}
    )
    
    assert isinstance(analysis_id, UUID)
    
    # Retrieve analysis
    result = await db.get_analysis(str(analysis_id))
    
    assert result is not None
    assert result["user_id"] == "test-user-integration"
    assert result["detected_salary"] == 50000.00
    assert result["confidence"] == "high"
    
    # Cleanup: Delete test data
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM analyses WHERE id = $1", analysis_id)


@pytest.mark.asyncio
async def test_save_audit_log_real(db_connection):
    """Test saving audit log to real database."""
    db = db_connection
    
    await db.save_audit_log(
        user_id="test-user",
        action="integration_test",
        status="success",
        details={"test": "audit log integration"}
    )
    
    # Verify audit log was saved
    async with db.pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM audit_logs WHERE user_id = $1 AND action = $2 ORDER BY created_at DESC LIMIT 1",
            "test-user",
            "integration_test"
        )
        
        assert result is not None
        assert result["status"] == "success"
        
        # Cleanup
        await conn.execute("DELETE FROM audit_logs WHERE id = $1", result["id"])


@pytest.mark.asyncio
async def test_get_user_analyses_real(db_connection):
    """Test retrieving user analyses from real database."""
    db = db_connection
    
    # Create test analyses
    user_id = "test-user-list"
    analysis_ids = []
    
    for i in range(3):
        aid = await db.save_analysis(
            user_id=user_id,
            detected_salary=40000.00 + (i * 1000),
            confidence="medium",
            transactions_analyzed=50,
            credit_transactions=25,
            debit_transactions=25,
            clusters_found=3,
            top_candidates_count=5,
            expected_gross=None,
            matches_expected=None,
            difference=None,
            difference_percentage=None,
            employer=None,
            pvd_rate=None,
            extra_deductions=None,
            pdf_filename=f"test_{i}.pdf",
            pages_processed=3,
            masked_items=10,
            metadata={"iteration": i}
        )
        analysis_ids.append(aid)
    
    # Retrieve analyses
    results = await db.get_user_analyses(user_id, limit=10, offset=0)
    
    assert len(results) >= 3
    
    # Cleanup
    async with db.pool.acquire() as conn:
        for aid in analysis_ids:
            await conn.execute("DELETE FROM analyses WHERE id = $1", aid)


# Instructions for running integration tests
"""
Setup:
1. Start PostgreSQL:
   docker compose up -d db

2. Create test database:
   docker exec -it bank_pdf_db psql -U postgres -c "CREATE DATABASE test_bank_statements;"

3. Run schema:
   docker exec -i bank_pdf_db psql -U postgres -d test_bank_statements < database/schema.sql

4. Set environment variable:
   export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_bank_statements"

5. Run integration tests:
   pytest tests/test_database_integration.py -v -m integration

Or run all tests (skip integration):
   pytest tests/ -v -m "not integration"
"""

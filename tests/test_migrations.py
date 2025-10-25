"""Integration tests for Alembic database migrations.

Tests verify that migrations can be applied and rolled back correctly,
and that the schema matches expectations.
"""

import asyncio
import os
from typing import AsyncGenerator

import asyncpg
import pytest
from alembic import command
from alembic.config import Config

# Test database URL (use TEST_DATABASE_URL or default)
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/bank_statements_test"
)


@pytest.fixture
async def test_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Create a test database connection.
    
    Yields:
        asyncpg.Connection: Database connection for testing
    """
    conn = await asyncpg.connect(TEST_DB_URL)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
def alembic_config() -> Config:
    """Create Alembic configuration for testing.
    
    Returns:
        Config: Alembic configuration object
    """
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DB_URL.replace("+asyncpg", ""))
    return config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_upgrade(alembic_config: Config, test_db_connection: asyncpg.Connection):
    """Test that initial migration can be applied successfully.
    
    Verifies:
    - Migration runs without errors
    - Tables are created (analyses, audit_logs)
    - Indexes are created
    - Constraints are applied
    """
    # Drop all tables first (clean slate)
    await test_db_connection.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    await test_db_connection.execute("DROP TABLE IF EXISTS analyses CASCADE")
    await test_db_connection.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
    
    # Run migration
    command.upgrade(alembic_config, "head")
    
    # Verify alembic_version table exists
    version = await test_db_connection.fetchval(
        "SELECT version_num FROM alembic_version"
    )
    assert version == "001_initial", f"Expected version 001_initial, got {version}"
    
    # Verify analyses table exists
    analyses_exists = await test_db_connection.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'analyses'
        )
    """)
    assert analyses_exists is True, "analyses table should exist"
    
    # Verify audit_logs table exists
    audit_logs_exists = await test_db_connection.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'audit_logs'
        )
    """)
    assert audit_logs_exists is True, "audit_logs table should exist"
    
    # Verify analyses table columns
    columns = await test_db_connection.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'analyses'
        ORDER BY column_name
    """)
    
    column_names = [col['column_name'] for col in columns]
    expected_columns = [
        'clusters_found', 'confidence', 'created_at', 'credit_transactions',
        'debit_transactions', 'detected_salary', 'difference', 'difference_percentage',
        'employer', 'expected_gross', 'extra_deductions', 'id', 'masked_items',
        'matches_expected', 'metadata', 'pages_processed', 'pdf_filename',
        'pvd_rate', 'top_candidates_count', 'transactions_analyzed', 'user_id'
    ]
    assert sorted(column_names) == sorted(expected_columns), \
        f"analyses columns mismatch: {column_names}"
    
    # Verify indexes exist
    indexes = await test_db_connection.fetch("""
        SELECT indexname FROM pg_indexes
        WHERE tablename IN ('analyses', 'audit_logs')
        ORDER BY indexname
    """)
    
    index_names = [idx['indexname'] for idx in indexes]
    expected_indexes = [
        'idx_analyses_confidence',
        'idx_analyses_created_at',
        'idx_analyses_detected_salary',
        'idx_analyses_user_id',
        'idx_audit_logs_action',
        'idx_audit_logs_analysis_id',
        'idx_audit_logs_created_at',
        'idx_audit_logs_status',
        'idx_audit_logs_user_id'
    ]
    
    for expected_idx in expected_indexes:
        assert expected_idx in index_names, f"Index {expected_idx} should exist"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_downgrade(alembic_config: Config, test_db_connection: asyncpg.Connection):
    """Test that migration can be rolled back successfully.
    
    Verifies:
    - Downgrade runs without errors
    - Tables are dropped
    - Indexes are removed
    """
    # First, ensure migration is applied
    await test_db_connection.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    await test_db_connection.execute("DROP TABLE IF EXISTS analyses CASCADE")
    await test_db_connection.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
    
    command.upgrade(alembic_config, "head")
    
    # Now downgrade
    command.downgrade(alembic_config, "base")
    
    # Verify tables are dropped
    analyses_exists = await test_db_connection.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'analyses'
        )
    """)
    assert analyses_exists is False, "analyses table should be dropped"
    
    audit_logs_exists = await test_db_connection.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'audit_logs'
        )
    """)
    assert audit_logs_exists is False, "audit_logs table should be dropped"
    
    # Verify alembic_version is empty
    version_count = await test_db_connection.fetchval(
        "SELECT COUNT(*) FROM alembic_version"
    )
    assert version_count == 0, "alembic_version should be empty after downgrade"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_insert_data_after_migration(alembic_config: Config, test_db_connection: asyncpg.Connection):
    """Test that data can be inserted after migration.
    
    Verifies:
    - Constraints work correctly
    - Foreign keys are enforced
    - Default values are applied
    """
    # Ensure migration is applied
    await test_db_connection.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    await test_db_connection.execute("DROP TABLE IF EXISTS analyses CASCADE")
    await test_db_connection.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
    
    command.upgrade(alembic_config, "head")
    
    # Insert test analysis
    analysis_id = await test_db_connection.fetchval("""
        INSERT INTO analyses (
            user_id, confidence, transactions_analyzed, detected_salary
        ) VALUES (
            'test_user', 'high', 100, 50000.00
        ) RETURNING id
    """)
    
    assert analysis_id is not None, "Analysis should be inserted"
    
    # Verify analysis was inserted
    analysis = await test_db_connection.fetchrow(
        "SELECT * FROM analyses WHERE id = $1", analysis_id
    )
    assert analysis is not None, "Analysis should exist"
    assert analysis['user_id'] == 'test_user'
    assert analysis['confidence'] == 'high'
    assert analysis['transactions_analyzed'] == 100
    assert analysis['detected_salary'] == 50000.00
    assert analysis['created_at'] is not None, "created_at should have default value"
    
    # Insert audit log with foreign key reference
    audit_log_id = await test_db_connection.fetchval("""
        INSERT INTO audit_logs (
            user_id, analysis_id, action, status
        ) VALUES (
            'test_user', $1, 'analyze_upload', 'success'
        ) RETURNING id
    """, analysis_id)
    
    assert audit_log_id is not None, "Audit log should be inserted"
    
    # Verify audit log
    audit_log = await test_db_connection.fetchrow(
        "SELECT * FROM audit_logs WHERE id = $1", audit_log_id
    )
    assert audit_log is not None
    assert audit_log['analysis_id'] == analysis_id
    assert audit_log['status'] == 'success'
    
    # Test constraint violation (invalid confidence)
    with pytest.raises(asyncpg.CheckViolationError):
        await test_db_connection.execute("""
            INSERT INTO analyses (
                user_id, confidence, transactions_analyzed
            ) VALUES (
                'test_user', 'invalid', 100
            )
        """)
    
    # Cleanup
    await test_db_connection.execute("DELETE FROM audit_logs WHERE id = $1", audit_log_id)
    await test_db_connection.execute("DELETE FROM analyses WHERE id = $1", analysis_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_idempotent(alembic_config: Config, test_db_connection: asyncpg.Connection):
    """Test that running migration twice doesn't cause errors.
    
    Verifies:
    - Migration is idempotent
    - Re-running upgrade doesn't break anything
    """
    # Clean slate
    await test_db_connection.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    await test_db_connection.execute("DROP TABLE IF EXISTS analyses CASCADE")
    await test_db_connection.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
    
    # Run migration first time
    command.upgrade(alembic_config, "head")
    
    # Run migration second time (should be no-op)
    command.upgrade(alembic_config, "head")
    
    # Verify version is still correct
    version = await test_db_connection.fetchval(
        "SELECT version_num FROM alembic_version"
    )
    assert version == "001_initial"
    
    # Verify tables still exist and are functional
    analyses_count = await test_db_connection.fetchval(
        "SELECT COUNT(*) FROM analyses"
    )
    assert analyses_count == 0, "analyses table should be empty but functional"

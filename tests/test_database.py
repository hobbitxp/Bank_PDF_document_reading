"""
Unit tests for PostgresDatabase adapter.

Simplified tests focusing on initialization and method signatures.
Full integration tests should be done with real PostgreSQL instance.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from infrastructure.database.postgres_adapter import PostgresDatabase


class TestPostgresDatabase:
    """Test PostgresDatabase adapter implementation."""
    
    def test_init(self):
        """Test PostgresDatabase initialization."""
        connection_string = "postgresql://test_user:test_pass@localhost:5432/test_db"
        db = PostgresDatabase(
            connection_string=connection_string,
            min_pool_size=5,
            max_pool_size=20
        )
        
        assert db.connection_string == connection_string
        assert db.min_pool_size == 5
        assert db.max_pool_size == 20
        assert db.pool is None
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test database connection creates pool."""
        mock_pool = AsyncMock()
        
        async def mock_create_pool(*args, **kwargs):
            return mock_pool
        
        with patch('asyncpg.create_pool', side_effect=mock_create_pool):
            db = PostgresDatabase(
                connection_string="postgresql://test@localhost/test",
                min_pool_size=5,
                max_pool_size=20
            )
            await db.connect()
            
            assert db.pool is not None
    
    def test_save_analysis_signature(self):
        """Test save_analysis has correct method signature."""
        db = PostgresDatabase(connection_string="postgresql://test@localhost/test")
        
        # Verify method exists and signature
        import inspect
        sig = inspect.signature(db.save_analysis)
        params = list(sig.parameters.keys())
        
        # Check required parameters exist
        assert 'user_id' in params
        assert 'detected_salary' in params
        assert 'confidence' in params
        assert 'metadata' in params
    
    def test_save_audit_log_signature(self):
        """Test save_audit_log has correct method signature."""
        db = PostgresDatabase(connection_string="postgresql://test@localhost/test")
        
        import inspect
        sig = inspect.signature(db.save_audit_log)
        params = list(sig.parameters.keys())
        
        # Check required parameters exist
        assert 'user_id' in params
        assert 'action' in params
        assert 'status' in params
    
    def test_get_analysis_signature(self):
        """Test get_analysis has correct method signature."""
        db = PostgresDatabase(connection_string="postgresql://test@localhost/test")
        
        import inspect
        sig = inspect.signature(db.get_analysis)
        params = list(sig.parameters.keys())
        
        assert 'analysis_id' in params
    
    def test_get_user_analyses_signature(self):
        """Test get_user_analyses has correct method signature."""
        db = PostgresDatabase(connection_string="postgresql://test@localhost/test")
        
        import inspect
        sig = inspect.signature(db.get_user_analyses)
        params = list(sig.parameters.keys())
        
        assert 'user_id' in params
        assert 'limit' in params
        assert 'offset' in params


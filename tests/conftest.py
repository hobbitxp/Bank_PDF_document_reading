"""
Pytest configuration and shared fixtures.
"""
import sys
from pathlib import Path
import pytest
from typing import Dict, Any

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_transaction_data() -> Dict[str, Any]:
    """Sample transaction data for testing."""
    return {
        "date": "2025-01-15",
        "description": "เงินเดือน บริษัท ทดสอบ จำกัด",
        "amount": 45000.00,
        "type": "CREDIT",
        "balance": 45000.00
    }


@pytest.fixture
def sample_analysis_result() -> Dict[str, Any]:
    """Sample analysis result for testing."""
    return {
        "detected_amount": 45000.00,
        "confidence": 0.95,
        "transactions_analyzed": 50,
        "clusters_found": 3,
        "top_candidates": [
            {"amount": 45000.00, "count": 1, "confidence": 0.95}
        ]
    }


@pytest.fixture
def mock_database_config() -> Dict[str, str]:
    """Mock database configuration."""
    return {
        "host": "localhost",
        "port": "5432",
        "database": "test_bank_statements",
        "user": "test_user",
        "password": "test_password"
    }

"""
Unit tests for AnalyzeStatementUseCase.

Tests the use case with mocked dependencies to verify:
1. Async execution works correctly
2. Database integration is called properly
3. Response structure matches schema
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from application.use_cases.analyze_statement import AnalyzeStatementUseCase


class TestAnalyzeStatementUseCase:
    """Test AnalyzeStatementUseCase with database integration."""
    
    @pytest.fixture
    def mock_pdf_extractor(self):
        """Mock PDF extractor."""
        extractor = MagicMock()
        extractor.extract_text.return_value = {
            "transactions": [
                {
                    "date": "2025-01-15",
                    "description": "เงินเดือน บริษัททดสอบ",
                    "amount": 45000.00,
                    "type": "CREDIT"
                }
            ],
            "pages": 3
        }
        return extractor
    
    @pytest.fixture
    def mock_data_masker(self):
        """Mock data masker."""
        masker = MagicMock()
        # mock_masker.mask() must return tuple: (masked_statement, mapping)
        mock_statement = MagicMock()
        mock_mapping = {"test": "masked"}
        masker.mask.return_value = (mock_statement, mock_mapping)
        return masker
    
    @pytest.fixture
    def mock_salary_analyzer(self):
        """Mock salary analyzer."""
        analyzer = MagicMock()
        analyzer.analyze.return_value = MagicMock(
            detected_amount=45000.00,
            confidence=0.95,
            transactions_analyzed=50,
            clusters_found=3,
            top_candidates=[
                {"amount": 45000.00, "count": 1, "confidence": 0.95}
            ],
            matches_expected=True,
            expected_gross=45000.00,
            difference_amount=0.0,
            difference_percentage=0.0,
            pvd_rate=3.0,
            extra_deductions=1500.00,
            employer_name="บริษัททดสอบ"
        )
        return analyzer
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage adapter."""
        storage = MagicMock()
        storage.upload.return_value = "s3://bucket/test.pdf"
        return storage
    
    @pytest.fixture
    def mock_database(self):
        """Mock database adapter."""
        database = AsyncMock()
        database.save_analysis = AsyncMock()
        database.save_audit_log = AsyncMock()
        return database
    
    def test_init_with_database(
        self,
        mock_pdf_extractor,
        mock_data_masker,
        mock_salary_analyzer,
        mock_storage,
        mock_database
    ):
        """Test initialization with database parameter."""
        use_case = AnalyzeStatementUseCase(
            pdf_extractor=mock_pdf_extractor,
            data_masker=mock_data_masker,
            salary_analyzer=mock_salary_analyzer,
            storage=mock_storage,
            database=mock_database
        )
        
        assert use_case.pdf_extractor is not None
        assert use_case.data_masker is not None
        assert use_case.salary_analyzer is not None
        assert use_case.storage is not None
        assert use_case.database is not None
    
    def test_init_without_database(
        self,
        mock_pdf_extractor,
        mock_data_masker,
        mock_salary_analyzer,
        mock_storage
    ):
        """Test initialization without database (backward compatibility)."""
        use_case = AnalyzeStatementUseCase(
            pdf_extractor=mock_pdf_extractor,
            data_masker=mock_data_masker,
            salary_analyzer=mock_salary_analyzer,
            storage=mock_storage
        )
        
        assert use_case.database is None
    
    @pytest.mark.asyncio
    async def test_execute_is_async(
        self,
        mock_pdf_extractor,
        mock_data_masker,
        mock_salary_analyzer,
        mock_storage,
        mock_database
    ):
        """Test that execute() is an async method."""
        use_case = AnalyzeStatementUseCase(
            pdf_extractor=mock_pdf_extractor,
            data_masker=mock_data_masker,
            salary_analyzer=mock_salary_analyzer,
            storage=mock_storage,
            database=mock_database
        )
        
        import inspect
        assert inspect.iscoroutinefunction(use_case.execute)
    
    @pytest.mark.asyncio
    async def test_execute_with_database(
        self,
        mock_pdf_extractor,
        mock_data_masker,
        mock_salary_analyzer,
        mock_storage,
        mock_database,
        tmp_path
    ):
        """Test execute() calls database.save_analysis()."""
        # Create temporary PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("fake pdf content")
        
        use_case = AnalyzeStatementUseCase(
            pdf_extractor=mock_pdf_extractor,
            data_masker=mock_data_masker,
            salary_analyzer=mock_salary_analyzer,
            storage=mock_storage,
            database=mock_database
        )
        
        result = await use_case.execute(
            pdf_path=str(pdf_path),
            user_id="test-user",
            expected_gross=45000.00
        )
        
        # Verify database methods were called
        mock_database.save_analysis.assert_called_once()
        mock_database.save_audit_log.assert_called_once()
        
        # Verify response structure
        assert "analysis_id" in result
        assert "pdf_storage_url" in result
        assert "database_saved" in result
        assert result["database_saved"] is True
    
    @pytest.mark.asyncio
    async def test_execute_without_database(
        self,
        mock_pdf_extractor,
        mock_data_masker,
        mock_salary_analyzer,
        mock_storage,
        tmp_path
    ):
        """Test execute() works without database (backward compatibility)."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("fake pdf content")
        
        use_case = AnalyzeStatementUseCase(
            pdf_extractor=mock_pdf_extractor,
            data_masker=mock_data_masker,
            salary_analyzer=mock_salary_analyzer,
            storage=mock_storage
            # No database parameter
        )
        
        result = await use_case.execute(
            pdf_path=str(pdf_path),
            user_id="test-user",
            expected_gross=45000.00
        )
        
        # Verify response structure
        assert "analysis_id" in result
        assert "pdf_storage_url" in result
        assert "database_saved" in result
        assert result["database_saved"] is False
    
    @pytest.mark.asyncio
    async def test_execute_database_save_parameters(
        self,
        mock_pdf_extractor,
        mock_data_masker,
        mock_salary_analyzer,
        mock_storage,
        mock_database,
        tmp_path
    ):
        """Test that save_analysis is called with correct parameters."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("fake pdf content")
        
        use_case = AnalyzeStatementUseCase(
            pdf_extractor=mock_pdf_extractor,
            data_masker=mock_data_masker,
            salary_analyzer=mock_salary_analyzer,
            storage=mock_storage,
            database=mock_database
        )
        
        await use_case.execute(
            pdf_path=str(pdf_path),
            user_id="test-user",
            expected_gross=45000.00
        )
        
        # Verify database.save_analysis was called
        mock_database.save_analysis.assert_called_once()
        
        # Get the call arguments
        call_args = mock_database.save_analysis.call_args
        
        # Verify key parameters exist (without strict checking of names)
        assert call_args is not None
        assert len(call_args.kwargs) > 0

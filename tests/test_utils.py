"""
Tests for utility modules
"""
import pytest
from datetime import datetime
from utils import ThaiDateParser, DataCleaner, Validator


class TestThaiDateParser:
    """Test Thai date parsing."""

    def test_parse_buddhist_year(self):
        """Test Buddhist year conversion."""
        assert ThaiDateParser.buddhist_to_gregorian_year(2567) == 2024
        assert ThaiDateParser.gregorian_to_buddhist_year(2024) == 2567

    def test_parse_date_dd_mm_yyyy(self):
        """Test parsing DD/MM/YYYY format."""
        date = ThaiDateParser.parse_thai_date('15/01/2567')
        assert date is not None
        assert date.year == 2024
        assert date.month == 1
        assert date.day == 15

    def test_parse_date_with_thai_month(self):
        """Test parsing with Thai month name."""
        date = ThaiDateParser.parse_thai_date('15 มกราคม 2567')
        assert date is not None
        assert date.year == 2024
        assert date.month == 1

    def test_parse_invalid_date(self):
        """Test parsing invalid date."""
        date = ThaiDateParser.parse_thai_date('invalid')
        assert date is None


class TestDataCleaner:
    """Test data cleaning."""

    def test_clean_text(self):
        """Test text cleaning."""
        assert DataCleaner.clean_text('  hello   world  ') == 'hello world'
        assert DataCleaner.clean_text('') == ''
        assert DataCleaner.clean_text(None) == ''

    def test_normalize_amount(self):
        """Test amount normalization."""
        assert DataCleaner.normalize_amount('1,234.56') == 1234.56
        assert DataCleaner.normalize_amount(1234) == 1234.0
        assert DataCleaner.normalize_amount('฿500') == 500.0

    def test_detect_transaction_type(self):
        """Test transaction type detection."""
        assert DataCleaner.detect_transaction_type(-100, 'ซื้อของ') == 'debit'
        assert DataCleaner.detect_transaction_type(500, 'เงินเดือน') == 'credit'

    def test_auto_categorize(self):
        """Test auto-categorization."""
        assert DataCleaner.auto_categorize('7-ELEVEN', -50) == 'shopping'
        assert DataCleaner.auto_categorize('ร้านอาหาร', -200) == 'food'
        assert DataCleaner.auto_categorize('BTS', -42) == 'transport'
        assert DataCleaner.auto_categorize('เงินเดือน', 30000) == 'income'

    def test_remove_duplicates(self):
        """Test duplicate removal."""
        transactions = [
            {'date': '2024-01-01', 'amount': -100, 'description': 'Test'},
            {'date': '2024-01-01', 'amount': -100, 'description': 'Test'},  # Duplicate
            {'date': '2024-01-02', 'amount': -200, 'description': 'Other'},
        ]

        unique = DataCleaner.remove_duplicates(transactions)
        assert len(unique) == 2


class TestValidator:
    """Test data validation."""

    def test_validate_transaction_valid(self):
        """Test validating valid transaction."""
        txn = {
            'date': '2024-01-01',
            'amount': -100.0,
            'description': 'Test transaction',
        }

        result = Validator.validate_transaction(txn)
        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_transaction_missing_field(self):
        """Test validating transaction with missing field."""
        txn = {
            'date': '2024-01-01',
            # Missing 'amount'
            'description': 'Test',
        }

        result = Validator.validate_transaction(txn)
        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_balance(self):
        """Test balance validation."""
        balance = {
            'opening': 1000.0,
            'closing': 900.0,
        }

        result = Validator.validate_balance(balance)
        assert result['valid'] is True

    def test_validate_metadata(self):
        """Test metadata validation."""
        metadata = {
            'bank': 'SCB',
            'account_number': '123-4-56789-0',
            'statement_period': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
            }
        }

        result = Validator.validate_metadata(metadata)
        assert result['valid'] is True

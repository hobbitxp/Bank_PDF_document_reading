"""
Tests for bank parsers
"""
import pytest
from parsers import get_parser, list_supported_banks, BaseParser


class TestParserFactory:
    """Test parser factory functions."""

    def test_list_supported_banks(self):
        """Test listing supported banks."""
        banks = list_supported_banks()
        assert len(banks) == 5
        assert 'scb' in banks
        assert 'tmb' in banks
        assert 'bbl' in banks
        assert 'kbank' in banks
        assert 'ktb' in banks

    def test_get_parser_scb(self):
        """Test getting SCB parser."""
        parser = get_parser('scb')
        assert parser is not None
        assert isinstance(parser, BaseParser)
        assert parser.bank_code == 'scb'

    def test_get_parser_case_insensitive(self):
        """Test that bank code is case insensitive."""
        parser = get_parser('SCB')
        assert parser.bank_code == 'scb'

    def test_get_parser_invalid_bank(self):
        """Test getting parser for invalid bank."""
        with pytest.raises(ValueError):
            get_parser('invalid_bank')


class TestBaseParser:
    """Test base parser functionality."""

    def test_clean_amount(self):
        """Test amount cleaning."""
        parser = get_parser('scb')

        assert parser.clean_amount('1,234.56') == 1234.56
        assert parser.clean_amount('1234') == 1234.0
        assert parser.clean_amount('1,234') == 1234.0
        assert parser.clean_amount('-456.78') == -456.78
        assert parser.clean_amount('') == 0.0
        assert parser.clean_amount(None) == 0.0

    def test_generate_summary(self):
        """Test summary generation."""
        parser = get_parser('scb')

        transactions = [
            {'amount': -100.0, 'category': 'food', 'channel': 'mobile'},
            {'amount': -200.0, 'category': 'shopping', 'channel': 'mobile'},
            {'amount': 500.0, 'category': 'income', 'channel': 'transfer'},
        ]

        summary = parser.generate_summary(transactions)

        assert summary['total_transactions'] == 3
        assert summary['total_debit'] == 300.0
        assert summary['total_credit'] == 500.0
        assert summary['net_change'] == 200.0
        assert summary['by_type']['debit_count'] == 2
        assert summary['by_type']['credit_count'] == 1

"""
Tests for AI module
"""
import pytest
from ai import OllamaClient, FinancialAnalyzer, create_prompt, get_system_prompt


class TestPrompts:
    """Test prompt generation."""

    def test_get_system_prompt(self):
        """Test getting system prompts."""
        prompt = get_system_prompt('analyzer')
        assert prompt is not None
        assert len(prompt) > 0

        prompt = get_system_prompt('advisor')
        assert prompt is not None

    def test_create_prompt(self):
        """Test creating complete prompt."""
        statement_data = {
            'metadata': {'bank': 'SCB'},
            'balance': {'opening': 1000, 'closing': 900},
            'summary': {'total_transactions': 10},
            'transactions': []
        }

        prompt = create_prompt('test query', statement_data)
        assert 'test query' in prompt
        assert 'SCB' in prompt


class TestOllamaClient:
    """Test Ollama client (requires Ollama to be running)."""

    def test_client_initialization(self):
        """Test client initialization."""
        client = OllamaClient()
        assert client.host is not None
        assert client.model is not None

    def test_is_available(self):
        """Test checking if Ollama is available."""
        client = OllamaClient()
        # This will return True/False depending on whether Ollama is running
        # We just check it doesn't error
        result = client.is_available()
        assert isinstance(result, bool)


class TestFinancialAnalyzer:
    """Test financial analyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = FinancialAnalyzer()
        assert analyzer.client is not None

    def test_is_available(self):
        """Test checking analyzer availability."""
        analyzer = FinancialAnalyzer()
        result = analyzer.is_available()
        assert isinstance(result, bool)

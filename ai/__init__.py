"""
AI module for bank statement analysis
"""
from .ollama_client import OllamaClient
from .analyzer import FinancialAnalyzer
from .prompts import (
    QUERY_TEMPLATES,
    EXAMPLE_QUERIES,
    create_prompt,
    get_system_prompt,
    format_statement_context
)

__all__ = [
    'OllamaClient',
    'FinancialAnalyzer',
    'QUERY_TEMPLATES',
    'EXAMPLE_QUERIES',
    'create_prompt',
    'get_system_prompt',
    'format_statement_context',
]

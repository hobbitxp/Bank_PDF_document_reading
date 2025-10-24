"""
AI-powered financial analyzer
"""
from typing import Dict, Any, Optional, List
from .ollama_client import OllamaClient
from .prompts import (
    create_prompt,
    get_system_prompt,
    QUERY_TEMPLATES,
    format_statement_context
)


class FinancialAnalyzer:
    """
    AI-powered analyzer for bank statements.
    """

    def __init__(self, client: Optional[OllamaClient] = None):
        """
        Initialize analyzer.

        Args:
            client: Optional OllamaClient instance
        """
        self.client = client or OllamaClient()

    def analyze(self, statement_data: Dict[str, Any], query: str,
               role: str = "analyzer") -> str:
        """
        Analyze statement with a query.

        Args:
            statement_data: Parsed statement data
            query: User query
            role: AI role ('analyzer', 'advisor', 'planner')

        Returns:
            AI analysis response
        """
        system_prompt = get_system_prompt(role)
        prompt = create_prompt(query, statement_data)

        return self.client.generate(prompt, system=system_prompt)

    def quick_summary(self, statement_data: Dict[str, Any]) -> str:
        """
        Generate a quick summary of the statement.

        Args:
            statement_data: Parsed statement data

        Returns:
            Summary text
        """
        return self.analyze(statement_data, QUERY_TEMPLATES["summary"])

    def spending_analysis(self, statement_data: Dict[str, Any]) -> str:
        """
        Analyze spending patterns.

        Args:
            statement_data: Parsed statement data

        Returns:
            Analysis text
        """
        return self.analyze(statement_data, QUERY_TEMPLATES["spending_analysis"])

    def savings_advice(self, statement_data: Dict[str, Any]) -> str:
        """
        Get savings advice.

        Args:
            statement_data: Parsed statement data

        Returns:
            Advice text
        """
        return self.analyze(statement_data, QUERY_TEMPLATES["savings_advice"], role="advisor")

    def detect_anomalies(self, statement_data: Dict[str, Any]) -> str:
        """
        Detect anomalies in transactions.

        Args:
            statement_data: Parsed statement data

        Returns:
            Anomaly report
        """
        return self.analyze(statement_data, QUERY_TEMPLATES["anomaly_detection"])

    def budget_recommendation(self, statement_data: Dict[str, Any]) -> str:
        """
        Get budget recommendations.

        Args:
            statement_data: Parsed statement data

        Returns:
            Budget recommendations
        """
        return self.analyze(statement_data, QUERY_TEMPLATES["budget_recommendation"], role="planner")

    def category_breakdown(self, statement_data: Dict[str, Any]) -> str:
        """
        Get category breakdown with recommendations.

        Args:
            statement_data: Parsed statement data

        Returns:
            Category breakdown
        """
        return self.analyze(statement_data, QUERY_TEMPLATES["category_breakdown"])

    def merchant_analysis(self, statement_data: Dict[str, Any]) -> str:
        """
        Analyze merchants/vendors.

        Args:
            statement_data: Parsed statement data

        Returns:
            Merchant analysis
        """
        return self.analyze(statement_data, QUERY_TEMPLATES["merchant_analysis"])

    def financial_health_score(self, statement_data: Dict[str, Any]) -> str:
        """
        Calculate financial health score.

        Args:
            statement_data: Parsed statement data

        Returns:
            Health score and analysis
        """
        return self.analyze(statement_data, QUERY_TEMPLATES["financial_health"], role="advisor")

    def compare_statements(self, statements: List[Dict[str, Any]]) -> str:
        """
        Compare multiple statements (future feature).

        Args:
            statements: List of statement data

        Returns:
            Comparison analysis
        """
        # TODO: Implement multi-statement comparison
        raise NotImplementedError("Multi-statement comparison coming soon")

    def interactive_query(self, statement_data: Dict[str, Any]) -> None:
        """
        Start interactive query session.

        Args:
            statement_data: Parsed statement data
        """
        print("=== Interactive Financial Analyzer ===")
        print("พิมพ์คำถามของคุณ (พิมพ์ 'exit' เพื่อออก)")
        print()

        while True:
            query = input("คำถาม: ").strip()

            if query.lower() in ['exit', 'quit', 'ออก']:
                print("ขอบคุณที่ใช้บริการ")
                break

            if not query:
                continue

            try:
                response = self.analyze(statement_data, query)
                print(f"\nคำตอบ: {response}\n")
            except Exception as e:
                print(f"เกิดข้อผิดพลาด: {str(e)}\n")

    def is_available(self) -> bool:
        """
        Check if AI is available.

        Returns:
            True if AI client is available
        """
        return self.client.is_available()

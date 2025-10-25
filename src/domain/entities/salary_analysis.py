"""
Domain Entity: Salary Analysis Result
"""

from dataclasses import dataclass, field
from typing import Optional
from .transaction import Transaction


@dataclass
class SalaryAnalysis:
    """Result of salary detection analysis"""
    
    detected_amount: float
    confidence: str  # 'high', 'medium', 'low'
    transactions_analyzed: int
    clusters_found: int
    best_candidates: list[Transaction] = field(default_factory=list)
    all_scored_transactions: list[Transaction] = field(default_factory=list)
    expected_salary: Optional[float] = None
    
    @property
    def matches_expected(self) -> Optional[bool]:
        """Check if detected salary matches expected (within 5k THB)"""
        if self.expected_salary is None:
            return None
        return abs(self.detected_amount - self.expected_salary) < 5000
    
    @property
    def difference(self) -> Optional[float]:
        """Difference from expected salary"""
        if self.expected_salary is None:
            return None
        return self.detected_amount - self.expected_salary
    
    @property
    def difference_percentage(self) -> Optional[float]:
        """Percentage difference from expected"""
        if self.expected_salary is None or self.expected_salary == 0:
            return None
        return round((self.difference / self.expected_salary) * 100, 2)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "salary_detected": self.detected_amount,
            "confidence": self.confidence,
            "transactions_analyzed": self.transactions_analyzed,
            "clusters_found": self.clusters_found,
            "best_candidates": [t.to_dict() for t in self.best_candidates[:5]],
            "validation": {
                "matches_expected": self.matches_expected,
                "expected_salary": self.expected_salary,
                "detected_salary": self.detected_amount,
                "difference": self.difference,
                "difference_percentage": self.difference_percentage
            } if self.expected_salary else None
        }

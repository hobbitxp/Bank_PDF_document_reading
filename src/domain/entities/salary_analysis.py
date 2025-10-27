"""
Domain Entity: Salary Analysis Result
"""

from dataclasses import dataclass, field
from typing import Optional
from .transaction import Transaction
from ..enums import IncomeType


@dataclass
class SalaryAnalysis:
    """Result of salary detection analysis"""
    
    detected_amount: float
    confidence: str  # 'high', 'medium', 'low'
    transactions_analyzed: int
    clusters_found: int
    income_type: IncomeType = IncomeType.SALARIED  # Type of income detected
    best_candidates: list[Transaction] = field(default_factory=list)
    all_scored_transactions: list[Transaction] = field(default_factory=list)
    expected_salary: Optional[float] = None
    months_detected: int = 0  # Number of months with salary data
    approved: bool = False  # Approval status based on validation rules
    rejection_reason: Optional[str] = None  # Reason if rejected
    
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
            "income_type": self.income_type.value,
            "transactions_analyzed": self.transactions_analyzed,
            "clusters_found": self.clusters_found,
            "months_detected": self.months_detected,
            "approved": self.approved,
            "rejection_reason": self.rejection_reason,
            "best_candidates": [t.to_dict() for t in self.best_candidates[:5]],
            "validation": {
                "matches_expected": self.matches_expected,
                "expected_salary": self.expected_salary,
                "detected_salary": self.detected_amount,
                "difference": self.difference,
                "difference_percentage": self.difference_percentage
            }
        }

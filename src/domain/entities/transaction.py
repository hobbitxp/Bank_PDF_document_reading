"""
Domain Entity: Transaction
Represents a single bank transaction
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Transaction:
    """Bank transaction entity"""
    
    page: int
    line_index: int
    amount: float
    description: str
    is_credit: bool
    time: Optional[str] = None
    channel: Optional[str] = None
    payer: Optional[str] = None
    score: float = 0.0
    cluster_id: Optional[int] = None
    
    def is_excluded(self, exclusion_patterns: list[str]) -> bool:
        """Check if transaction matches exclusion patterns"""
        import re
        return any(re.search(pattern, self.description, re.I) for pattern in exclusion_patterns)
    
    def has_keyword(self, keyword_patterns: list[str]) -> bool:
        """Check if transaction contains salary keywords"""
        import re
        return any(re.search(pattern, self.description) for pattern in keyword_patterns)
    
    def is_early_morning(self) -> bool:
        """Check if transaction occurred during typical payroll hours (1-6 AM)"""
        if not self.time:
            return False
        try:
            hour = int(self.time.split(":")[0])
            return 1 <= hour <= 6
        except:
            return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "page": self.page,
            "line_index": self.line_index,
            "amount": self.amount,
            "description": self.description,
            "is_credit": self.is_credit,
            "time": self.time,
            "channel": self.channel,
            "payer": self.payer,
            "score": self.score,
            "cluster_id": self.cluster_id
        }

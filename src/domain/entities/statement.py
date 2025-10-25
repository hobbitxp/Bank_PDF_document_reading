"""
Domain Entity: Statement
Represents a bank statement document
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from .transaction import Transaction


@dataclass
class Statement:
    """Bank statement entity"""
    
    source_file: str
    total_pages: int
    extracted_at: datetime
    pages: list[dict] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    masked: bool = False
    masked_items_count: int = 0
    
    def add_transaction(self, transaction: Transaction):
        """Add a transaction to the statement"""
        self.transactions.append(transaction)
    
    def get_credit_transactions(self) -> list[Transaction]:
        """Get all credit (income) transactions"""
        return [t for t in self.transactions if t.is_credit]
    
    def get_debit_transactions(self) -> list[Transaction]:
        """Get all debit (expense) transactions"""
        return [t for t in self.transactions if not t.is_credit]
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "source_file": self.source_file,
            "total_pages": self.total_pages,
            "extracted_at": self.extracted_at.isoformat(),
            "pages": self.pages,
            "masked": self.masked,
            "masked_items_count": self.masked_items_count,
            "transaction_count": len(self.transactions)
        }

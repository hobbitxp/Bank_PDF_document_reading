"""
Base parser abstract class for bank statement parsers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import re


class BaseParser(ABC):
    """
    Abstract base class for all bank statement parsers.
    Each bank-specific parser should inherit from this class.
    """

    def __init__(self, bank_code: str, bank_name: str):
        """
        Initialize the parser.

        Args:
            bank_code: Bank code (e.g., 'scb', 'tmb')
            bank_name: Bank full name in Thai
        """
        self.bank_code = bank_code
        self.bank_name = bank_name

    @abstractmethod
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse a PDF statement file and extract all data.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing parsed statement data
        """
        pass

    @abstractmethod
    def extract_metadata(self, text: str, tables: List) -> Dict[str, Any]:
        """
        Extract metadata from the statement (account info, period, etc.).

        Args:
            text: Extracted text from PDF
            tables: Extracted tables from PDF

        Returns:
            Dictionary containing metadata
        """
        pass

    @abstractmethod
    def extract_balance(self, text: str, tables: List) -> Dict[str, float]:
        """
        Extract balance information (opening, closing, average).

        Args:
            text: Extracted text from PDF
            tables: Extracted tables from PDF

        Returns:
            Dictionary containing balance information
        """
        pass

    @abstractmethod
    def parse_transactions(self, tables: List) -> List[Dict[str, Any]]:
        """
        Parse transactions from the statement tables.

        Args:
            tables: Extracted tables from PDF

        Returns:
            List of transaction dictionaries
        """
        pass

    def generate_summary(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics from transactions.

        Args:
            transactions: List of parsed transactions

        Returns:
            Dictionary containing summary statistics
        """
        total_debit = 0
        total_credit = 0
        debit_count = 0
        credit_count = 0

        by_category = {}
        by_channel = {}

        for txn in transactions:
            amount = txn.get("amount", 0)
            category = txn.get("category", "other")
            channel = txn.get("channel", "unknown")

            if amount < 0:
                total_debit += abs(amount)
                debit_count += 1
            else:
                total_credit += amount
                credit_count += 1

            # Category summary
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += abs(amount)

            # Channel summary
            if channel not in by_channel:
                by_channel[channel] = 0
            by_channel[channel] += 1

        return {
            "total_transactions": len(transactions),
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "net_change": round(total_credit - total_debit, 2),
            "by_type": {
                "debit_count": debit_count,
                "credit_count": credit_count
            },
            "by_channel": by_channel,
            "by_category": {k: round(v, 2) for k, v in by_category.items()}
        }

    def extract_account_number(self, text: str, pattern: str) -> Optional[str]:
        """
        Extract account number using regex pattern.

        Args:
            text: Text to search in
            pattern: Regex pattern

        Returns:
            Account number or None
        """
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def extract_dates(self, text: str, pattern: str) -> Optional[tuple]:
        """
        Extract start and end dates using regex pattern.

        Args:
            text: Text to search in
            pattern: Regex pattern

        Returns:
            Tuple of (start_date, end_date) or None
        """
        match = re.search(pattern, text)
        if match:
            return match.group(1), match.group(2)
        return None

    def clean_amount(self, amount_str: str) -> float:
        """
        Clean and convert amount string to float.

        Args:
            amount_str: Amount as string (may contain commas, spaces, etc.)

        Returns:
            Amount as float
        """
        if not amount_str:
            return 0.0

        # Remove commas, spaces, and other non-numeric characters (except . and -)
        cleaned = re.sub(r'[^\d.-]', '', str(amount_str))

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    def standardize_output(self, metadata: Dict, balance: Dict,
                          transactions: List[Dict], validation: Dict) -> Dict[str, Any]:
        """
        Standardize the output format across all parsers.

        Args:
            metadata: Statement metadata
            balance: Balance information
            transactions: List of transactions
            validation: Validation results

        Returns:
            Standardized output dictionary
        """
        summary = self.generate_summary(transactions)

        return {
            "metadata": {
                **metadata,
                "bank": self.bank_code.upper(),
                "generated_at": datetime.now().isoformat() + "Z"
            },
            "balance": balance,
            "transactions": transactions,
            "summary": summary,
            "validation": validation
        }

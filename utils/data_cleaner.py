"""
Data cleaning utilities for bank statement data
"""
import re
from typing import Dict, List, Any, Optional
from config import CATEGORY_KEYWORDS


class DataCleaner:
    """
    Utility class for cleaning and normalizing bank statement data.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text by removing extra whitespace and normalizing.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    @staticmethod
    def normalize_amount(amount: Any) -> float:
        """
        Normalize amount to float.

        Args:
            amount: Amount in various formats

        Returns:
            Amount as float
        """
        if amount is None or amount == "":
            return 0.0

        if isinstance(amount, (int, float)):
            return float(amount)

        # Convert to string and clean
        amount_str = str(amount)
        # Remove currency symbols, commas, spaces
        amount_str = re.sub(r'[฿,\s]', '', amount_str)

        try:
            return float(amount_str)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def detect_transaction_type(amount: float, description: str) -> str:
        """
        Detect transaction type (debit/credit) based on amount and description.

        Args:
            amount: Transaction amount
            description: Transaction description

        Returns:
            'debit' or 'credit'
        """
        # Check amount sign
        if amount < 0:
            return "debit"
        elif amount > 0:
            return "credit"

        # Check description keywords
        debit_keywords = ["ถอน", "จ่าย", "ซื้อ", "โอนออก", "ชำระ", "withdrawal", "payment", "purchase"]
        credit_keywords = ["ฝาก", "รับ", "โอนเข้า", "เงินเดือน", "deposit", "transfer in", "salary"]

        description_lower = description.lower()

        for keyword in debit_keywords:
            if keyword in description_lower:
                return "debit"

        for keyword in credit_keywords:
            if keyword in description_lower:
                return "credit"

        return "debit"  # Default to debit

    @staticmethod
    def auto_categorize(description: str, amount: float) -> str:
        """
        Automatically categorize transaction based on description.

        Args:
            description: Transaction description
            amount: Transaction amount

        Returns:
            Category name
        """
        description_lower = description.lower()

        # Check for income first
        if amount > 0:
            income_keywords = ["เงินเดือน", "salary", "รับโอน", "transfer in"]
            if any(keyword in description_lower for keyword in income_keywords):
                return "income"

        # Check each category
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in description_lower:
                    return category

        return "other"

    @staticmethod
    def detect_channel(description: str) -> str:
        """
        Detect transaction channel from description.

        Args:
            description: Transaction description

        Returns:
            Channel name
        """
        description_lower = description.lower()

        channel_patterns = {
            "mobile": ["mobile", "app", "application", "แอพ", "มือถือ"],
            "atm": ["atm", "ตู้", "เอทีเอ็ม"],
            "online": ["online", "internet", "web", "ออนไลน์"],
            "counter": ["counter", "สาขา", "branch", "เคาน์เตอร์"],
            "transfer": ["transfer", "โอน", "promptpay"],
            "card": ["card", "บัตร"],
        }

        for channel, keywords in channel_patterns.items():
            if any(keyword in description_lower for keyword in keywords):
                return channel

        return "unknown"

    @staticmethod
    def extract_merchant_info(description: str) -> Dict[str, Optional[str]]:
        """
        Extract merchant information from description.

        Args:
            description: Transaction description

        Returns:
            Dictionary with merchant name and location
        """
        # Try to extract branch/location info
        location_match = re.search(r'สาขา\s*(.+?)(?:\s|$)', description)
        location = location_match.group(1) if location_match else None

        # Try to extract merchant name (before branch info or first few words)
        if location:
            merchant = description.split('สาขา')[0].strip()
        else:
            # Take first 3-5 words as merchant name
            words = description.split()[:5]
            merchant = ' '.join(words)

        return {
            "name": DataCleaner.clean_text(merchant) if merchant else None,
            "location": DataCleaner.clean_text(location) if location else None
        }

    @staticmethod
    def remove_duplicates(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate transactions based on date, amount, and description.

        Args:
            transactions: List of transactions

        Returns:
            List of unique transactions
        """
        seen = set()
        unique = []

        for txn in transactions:
            # Create a signature for the transaction
            signature = (
                txn.get('date'),
                txn.get('amount'),
                txn.get('description', '')[:50]  # First 50 chars of description
            )

            if signature not in seen:
                seen.add(signature)
                unique.append(txn)

        return unique

    @classmethod
    def clean_transaction(cls, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean a single transaction record.

        Args:
            transaction: Raw transaction dictionary

        Returns:
            Cleaned transaction dictionary
        """
        cleaned = {}

        # Clean description
        if 'description' in transaction:
            cleaned['description'] = cls.clean_text(transaction['description'])
        else:
            cleaned['description'] = ""

        # Normalize amount
        if 'amount' in transaction:
            cleaned['amount'] = cls.normalize_amount(transaction['amount'])
        else:
            cleaned['amount'] = 0.0

        # Detect type if not present
        if 'type' not in transaction:
            cleaned['type'] = cls.detect_transaction_type(
                cleaned['amount'],
                cleaned['description']
            )
        else:
            cleaned['type'] = transaction['type']

        # Auto-categorize if not present
        if 'category' not in transaction:
            cleaned['category'] = cls.auto_categorize(
                cleaned['description'],
                cleaned['amount']
            )
        else:
            cleaned['category'] = transaction['category']

        # Detect channel if not present
        if 'channel' not in transaction:
            cleaned['channel'] = cls.detect_channel(cleaned['description'])
        else:
            cleaned['channel'] = transaction['channel']

        # Extract merchant info if not present
        if 'merchant' not in transaction:
            cleaned['merchant'] = cls.extract_merchant_info(cleaned['description'])
        else:
            cleaned['merchant'] = transaction['merchant']

        # Copy other fields
        for key in ['id', 'date', 'time', 'balance_after', 'reference', 'from_account']:
            if key in transaction:
                cleaned[key] = transaction[key]

        return cleaned

    @classmethod
    def clean_transactions(cls, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean a list of transactions.

        Args:
            transactions: List of raw transactions

        Returns:
            List of cleaned transactions
        """
        # Clean each transaction
        cleaned = [cls.clean_transaction(txn) for txn in transactions]

        # Remove duplicates
        cleaned = cls.remove_duplicates(cleaned)

        # Sort by date
        cleaned.sort(key=lambda x: (x.get('date', ''), x.get('time', '')))

        return cleaned

    @classmethod
    def clean_statement_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean entire statement data.

        Args:
            data: Raw statement data dictionary

        Returns:
            Cleaned statement data
        """
        cleaned = data.copy()

        # Clean transactions
        if 'transactions' in cleaned:
            cleaned['transactions'] = cls.clean_transactions(cleaned['transactions'])

        # Clean metadata strings
        if 'metadata' in cleaned:
            for key, value in cleaned['metadata'].items():
                if isinstance(value, str):
                    cleaned['metadata'][key] = cls.clean_text(value)

        return cleaned

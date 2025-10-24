"""
Parser for Bangkok Bank (BBL) statements
"""
import re
from typing import Dict, List, Any, Optional
from .base_parser import BaseParser
from utils import PDFExtractor, ThaiDateParser, DataCleaner, Validator


class BBLParser(BaseParser):
    """
    Parser for Bangkok Bank (ธนาคารกรุงเทพ) statements.
    """

    def __init__(self):
        super().__init__("bbl", "ธนาคารกรุงเทพ")

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Parse BBL PDF statement."""
        extractor = PDFExtractor(pdf_path)
        data = extractor.extract_text_and_tables()

        text = data['text']
        tables = data['tables']

        metadata = self.extract_metadata(text, tables)
        balance = self.extract_balance(text, tables)
        transactions = self.parse_transactions(tables)

        cleaner = DataCleaner()
        transactions = cleaner.clean_transactions(transactions)

        validator = Validator()
        validation = validator.validate_statement({
            'metadata': metadata,
            'balance': balance,
            'transactions': transactions
        })

        return self.standardize_output(metadata, balance, transactions, validation)

    def extract_metadata(self, text: str, tables: List) -> Dict[str, Any]:
        """Extract metadata from BBL statement."""
        metadata = {}

        # BBL account number format
        account_pattern = r'(\d{3}[-\s]?\d[-\s]?\d{5}[-\s]?\d)'
        account_match = re.search(account_pattern, text)
        if account_match:
            metadata['account_number'] = account_match.group(1)

        # Statement period
        period_pattern = r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})\s*(?:ถึง|to|-|ระหว่าง)\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})'
        period_match = re.search(period_pattern, text, re.IGNORECASE)

        if period_match:
            metadata['statement_period'] = {
                'start_date': ThaiDateParser.parse_date_flexible(period_match.group(1)),
                'end_date': ThaiDateParser.parse_date_flexible(period_match.group(2))
            }

        # Account type
        if 'ออมทรัพย์' in text or 'SAVINGS' in text.upper():
            metadata['account_type'] = 'savings'
        elif 'กระแสรายวัน' in text or 'CURRENT' in text.upper():
            metadata['account_type'] = 'current'
        else:
            metadata['account_type'] = 'unknown'

        metadata['currency'] = 'THB'
        return metadata

    def extract_balance(self, text: str, tables: List) -> Dict[str, float]:
        """Extract balance information from BBL statement."""
        balance = {}

        # Opening balance
        opening_patterns = [
            r'ยอดยกมา[:\s]+([\d,\.]+)',
            r'เงินคงเหลือยกมา[:\s]+([\d,\.]+)',
            r'Beginning Balance[:\s]+([\d,\.]+)',
        ]

        for pattern in opening_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balance['opening'] = self.clean_amount(match.group(1))
                break

        # Closing balance
        closing_patterns = [
            r'ยอดยกไป[:\s]+([\d,\.]+)',
            r'เงินคงเหลือยกไป[:\s]+([\d,\.]+)',
            r'Ending Balance[:\s]+([\d,\.]+)',
            r'ยอดคงเหลือปัจจุบัน[:\s]+([\d,\.]+)',
        ]

        for pattern in closing_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balance['closing'] = self.clean_amount(match.group(1))
                break

        if 'opening' in balance and 'closing' in balance:
            balance['average'] = (balance['opening'] + balance['closing']) / 2

        return balance

    def parse_transactions(self, tables: List) -> List[Dict[str, Any]]:
        """Parse transactions from BBL statement tables."""
        transactions = []
        transaction_id = 1

        for table in tables:
            if not table or len(table) < 2:
                continue

            header = ' '.join([str(cell or '') for cell in table[0]]).lower()
            if not any(keyword in header for keyword in ['date', 'วันที่', 'transaction', 'รายการ', 'รายละเอียด']):
                continue

            for row in table[1:]:
                if not row or len(row) < 3:
                    continue

                txn = self._parse_transaction_row(row, transaction_id)
                if txn:
                    transactions.append(txn)
                    transaction_id += 1

        return transactions

    def _parse_transaction_row(self, row: List, txn_id: int) -> Optional[Dict[str, Any]]:
        """Parse a single transaction row."""
        row = [str(cell).strip() if cell else '' for cell in row]

        if len(row) < 3:
            return None

        txn = {'id': f'txn_{txn_id:03d}'}

        # Parse date (first column)
        parsed_date = ThaiDateParser.parse_date_flexible(row[0])
        if not parsed_date:
            return None

        txn['date'] = parsed_date

        # BBL often has: Date | Description | Withdrawal | Deposit | Balance
        description = ''
        withdrawal = 0
        deposit = 0
        balance = 0

        for i, cell in enumerate(row[1:], 1):
            # Check if numeric
            if re.search(r'[\d,]+\.?\d*', cell):
                clean_val = self.clean_amount(cell)
                if clean_val > 0:
                    if withdrawal == 0:
                        withdrawal = clean_val
                    elif deposit == 0:
                        deposit = clean_val
                    else:
                        balance = clean_val
            elif cell:
                description += ' ' + cell

        txn['description'] = description.strip()

        # Determine amount
        if withdrawal > 0:
            txn['amount'] = -withdrawal
        elif deposit > 0:
            txn['amount'] = deposit

        if balance > 0:
            txn['balance_after'] = balance

        return txn if txn.get('amount', 0) != 0 else None

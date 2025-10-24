"""
Parser for Kasikorn Bank (KBANK) statements
"""
import re
from typing import Dict, List, Any, Optional
from .base_parser import BaseParser
from utils import PDFExtractor, ThaiDateParser, DataCleaner, Validator


class KBANKParser(BaseParser):
    """
    Parser for Kasikorn Bank (ธนาคารกสิกรไทย) statements.
    """

    def __init__(self):
        super().__init__("kbank", "ธนาคารกสิกรไทย")

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Parse KBANK PDF statement."""
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
        """Extract metadata from KBANK statement."""
        metadata = {}

        # KBANK account number format
        account_pattern = r'(\d{3}[-\s]?\d[-\s]?\d{5}[-\s]?\d)'
        account_match = re.search(account_pattern, text)
        if account_match:
            metadata['account_number'] = account_match.group(1)

        # Statement period
        period_pattern = r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})\s*(?:ถึง|to|-)\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})'
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
        """Extract balance information from KBANK statement."""
        balance = {}

        # Opening balance
        opening_patterns = [
            r'ยอดยกมา[:\s]+([\d,\.]+)',
            r'ยอดเงินคงเหลือยกมา[:\s]+([\d,\.]+)',
            r'Previous Balance[:\s]+([\d,\.]+)',
        ]

        for pattern in opening_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balance['opening'] = self.clean_amount(match.group(1))
                break

        # Closing balance
        closing_patterns = [
            r'ยอดยกไป[:\s]+([\d,\.]+)',
            r'ยอดเงินคงเหลือยกไป[:\s]+([\d,\.]+)',
            r'New Balance[:\s]+([\d,\.]+)',
            r'ยอดคงเหลือ[:\s]+([\d,\.]+)',
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
        """Parse transactions from KBANK statement tables."""
        transactions = []
        transaction_id = 1

        for table in tables:
            if not table or len(table) < 2:
                continue

            header = ' '.join([str(cell or '') for cell in table[0]]).lower()
            if not any(keyword in header for keyword in ['date', 'วันที่', 'transaction', 'รายการ']):
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

        # Parse date
        parsed_date = ThaiDateParser.parse_date_flexible(row[0])
        if not parsed_date:
            return None

        txn['date'] = parsed_date

        # KBANK format: Date | Time | Description | Debit | Credit | Balance
        time_pattern = r'\d{1,2}:\d{2}'
        if len(row) > 1 and re.match(time_pattern, row[1]):
            txn['time'] = row[1]
            start_idx = 2
        else:
            start_idx = 1

        description = ''
        amounts = []

        for i in range(start_idx, len(row)):
            cell = row[i]
            if re.search(r'[\d,]+\.?\d*', cell) and cell.replace(',', '').replace('.', '').replace('-', '').isdigit():
                amounts.append(self.clean_amount(cell))
            elif cell:
                description += ' ' + cell

        txn['description'] = description.strip()

        # Process amounts: typically [debit, credit, balance]
        if len(amounts) >= 2:
            if amounts[0] > 0:  # Debit
                txn['amount'] = -amounts[0]
            elif amounts[1] > 0:  # Credit
                txn['amount'] = amounts[1]

            if len(amounts) >= 3:
                txn['balance_after'] = amounts[2]
        elif len(amounts) == 1:
            txn['amount'] = amounts[0]

        return txn if txn.get('amount', 0) != 0 else None

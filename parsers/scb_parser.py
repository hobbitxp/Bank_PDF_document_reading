"""
Parser for Siam Commercial Bank (SCB) statements
"""
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_parser import BaseParser
from utils import PDFExtractor, ThaiDateParser, DataCleaner, Validator


class SCBParser(BaseParser):
    """
    Parser for SCB (ธนาคารไทยพาณิชย์) bank statements.
    """

    def __init__(self):
        super().__init__("scb", "ธนาคารไทยพาณิชย์")

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse SCB PDF statement.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Parsed statement data
        """
        # Extract PDF content
        extractor = PDFExtractor(pdf_path)
        data = extractor.extract_text_and_tables()

        text = data['text']
        tables = data['tables']

        # Extract components
        metadata = self.extract_metadata(text, tables)
        balance = self.extract_balance(text, tables)
        transactions = self.parse_transactions(tables)

        # Clean data
        cleaner = DataCleaner()
        transactions = cleaner.clean_transactions(transactions)

        # Validate
        validator = Validator()
        validation = validator.validate_statement({
            'metadata': metadata,
            'balance': balance,
            'transactions': transactions
        })

        # Standardize output
        return self.standardize_output(metadata, balance, transactions, validation)

    def extract_metadata(self, text: str, tables: List) -> Dict[str, Any]:
        """
        Extract metadata from SCB statement.

        Args:
            text: Extracted text
            tables: Extracted tables

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Extract account number (pattern: xxx-x-xxxxx-x)
        account_pattern = r'(\d{3}[-\s]?\d[-\s]?\d{5}[-\s]?\d)'
        account_match = re.search(account_pattern, text)
        if account_match:
            metadata['account_number'] = account_match.group(1)

        # Extract statement period
        # Look for date ranges
        period_pattern = r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})\s*(?:ถึง|to|-)\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})'
        period_match = re.search(period_pattern, text)

        if period_match:
            start_date = ThaiDateParser.parse_date_flexible(period_match.group(1))
            end_date = ThaiDateParser.parse_date_flexible(period_match.group(2))

            metadata['statement_period'] = {
                'start_date': start_date,
                'end_date': end_date
            }

        # Account type
        if 'ออมทรัพย์' in text or 'SAVINGS' in text.upper():
            metadata['account_type'] = 'savings'
        elif 'กระแสรายวัน' in text or 'CURRENT' in text.upper():
            metadata['account_type'] = 'current'
        else:
            metadata['account_type'] = 'unknown'

        # Currency
        metadata['currency'] = 'THB'

        return metadata

    def extract_balance(self, text: str, tables: List) -> Dict[str, float]:
        """
        Extract balance information from SCB statement.

        Args:
            text: Extracted text
            tables: Extracted tables

        Returns:
            Balance dictionary
        """
        balance = {}

        # Look for opening balance
        opening_patterns = [
            r'ยอดยกมา[:\s]+([\d,\.]+)',
            r'เงินคงเหลือยกมา[:\s]+([\d,\.]+)',
            r'Opening Balance[:\s]+([\d,\.]+)',
        ]

        for pattern in opening_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balance['opening'] = self.clean_amount(match.group(1))
                break

        # Look for closing balance
        closing_patterns = [
            r'ยอดยกไป[:\s]+([\d,\.]+)',
            r'เงินคงเหลือยกไป[:\s]+([\d,\.]+)',
            r'Closing Balance[:\s]+([\d,\.]+)',
            r'ยอดคงเหลือ[:\s]+([\d,\.]+)',
        ]

        for pattern in closing_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balance['closing'] = self.clean_amount(match.group(1))
                break

        # Calculate average if not found
        if 'opening' in balance and 'closing' in balance:
            balance['average'] = (balance['opening'] + balance['closing']) / 2

        return balance

    def parse_transactions(self, tables: List) -> List[Dict[str, Any]]:
        """
        Parse transactions from SCB statement tables.

        Args:
            tables: Extracted tables

        Returns:
            List of transactions
        """
        transactions = []
        transaction_id = 1

        for table in tables:
            if not table or len(table) < 2:
                continue

            # Skip if table doesn't look like transactions
            # Look for common headers
            header = ' '.join([str(cell or '') for cell in table[0]]).lower()
            if not any(keyword in header for keyword in ['date', 'วันที่', 'transaction', 'รายการ', 'amount', 'จำนวน']):
                continue

            # Process rows
            for row in table[1:]:  # Skip header
                if not row or len(row) < 3:
                    continue

                # Try to parse as transaction
                txn = self._parse_transaction_row(row, transaction_id)
                if txn:
                    transactions.append(txn)
                    transaction_id += 1

        return transactions

    def _parse_transaction_row(self, row: List, txn_id: int) -> Optional[Dict[str, Any]]:
        """
        Parse a single transaction row.

        Args:
            row: Table row
            txn_id: Transaction ID

        Returns:
            Transaction dictionary or None
        """
        # Clean row
        row = [str(cell).strip() if cell else '' for cell in row]

        # Common SCB table formats:
        # [Date, Description, Withdrawal, Deposit, Balance]
        # [Date, Time, Description, Amount, Balance]

        if len(row) < 3:
            return None

        txn = {'id': f'txn_{txn_id:03d}'}

        # Extract date (usually first column)
        date_str = row[0]
        parsed_date = ThaiDateParser.parse_date_flexible(date_str)
        if not parsed_date:
            return None  # Skip if no valid date

        txn['date'] = parsed_date

        # Extract time if present (check second column)
        time_pattern = r'(\d{1,2}:\d{2}(?::\d{2})?)'
        if len(row) > 1:
            time_match = re.search(time_pattern, row[1])
            if time_match:
                txn['time'] = time_match.group(1)
                description_start = 2
            else:
                description_start = 1
        else:
            description_start = 1

        # Find description (non-numeric column)
        description = ''
        amount_col = -1
        balance_col = -1

        for i in range(description_start, len(row)):
            cell = row[i]
            # Check if cell contains amount (numbers with commas/dots)
            if re.search(r'[\d,]+\.?\d*', cell) and len(cell.replace(',', '').replace('.', '').replace('-', '')) > 0:
                if amount_col == -1:
                    amount_col = i
                else:
                    balance_col = i
            else:
                description += ' ' + cell

        txn['description'] = description.strip()

        # Extract amount
        if amount_col >= 0:
            amount_str = row[amount_col]
            amount = self.clean_amount(amount_str)

            # Determine if debit or credit based on column or sign
            if balance_col > 0 and balance_col == amount_col + 1:
                # Two amount columns: withdrawal and deposit
                withdrawal = self.clean_amount(row[amount_col])
                deposit = self.clean_amount(row[amount_col + 1]) if amount_col + 1 < len(row) else 0

                if withdrawal > 0:
                    txn['amount'] = -withdrawal
                elif deposit > 0:
                    txn['amount'] = deposit
            else:
                # Single amount column
                if '-' in amount_str or 'ถอน' in description.lower() or 'จ่าย' in description.lower():
                    txn['amount'] = -abs(amount)
                else:
                    txn['amount'] = amount

        # Extract balance if present
        if balance_col >= 0:
            txn['balance_after'] = self.clean_amount(row[balance_col])

        return txn if txn.get('amount') != 0 else None

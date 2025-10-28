"""
Raw Text Parser for KBANK Statement
Parses raw PDF text into structured transaction table
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ParsedTransaction:
    """Structured transaction from raw text"""
    page: int
    date: str
    time: str
    channel: str
    description: str
    type: str  # PAYMENT, TRANSFER_OUT, CASH_WITHDRAWAL, TRANSFER_IN, CARRY_FORWARD, UNKNOWN
    amount: float
    signed_amount: Optional[float]  # negative for debit, positive for credit
    debit: Optional[float]  # positive value for money out
    credit: Optional[float]  # positive value for money in
    balance: float
    payer: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'page': self.page,
            'date': self.date,
            'time': self.time,
            'channel': self.channel,
            'description': self.description,
            'type': self.type,
            'amount': self.amount,
            'signed_amount': self.signed_amount,
            'debit': self.debit,
            'credit': self.credit,
            'balance': self.balance,
            'payer': self.payer
        }


class RawTextParser:
    """Parse KBANK raw text into structured transactions"""
    
    # Transaction type mapping from Thai keywords
    TYPE_MAPPING = {
        # เงินออก (Outgoing)
        "ชำระเงิน": "PAYMENT",
        "เพื่อชำระ": "PAYMENT",
        "โอนเงิน": "TRANSFER_OUT",
        "โอนไป": "TRANSFER_OUT",
        "ถอนเงินสด": "CASH_WITHDRAWAL",
        
        # เงินเข้า (Incoming)
        "รับโอนเงิน": "TRANSFER_IN",
        "รับเงินโอน": "TRANSFER_IN",
        "รับโอนเงินอัตโนมัติ": "TRANSFER_IN",
        "รับโอนเงินผ่าน QR": "TRANSFER_IN",
        
        # Special
        "ยอดยกมา": "CARRY_FORWARD",
        "ยอดยกไป": "CARRY_FORWARD"
    }
    
    OUT_TYPES = {"PAYMENT", "TRANSFER_OUT", "CASH_WITHDRAWAL"}
    IN_TYPES = {"TRANSFER_IN"}
    
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.lines = raw_text.split('\n')
        
    def parse(self) -> List[ParsedTransaction]:
        """Parse all transactions from raw text"""
        transactions = []
        current_page = 0
        
        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            
            # Track page number
            if line.startswith("PAGE "):
                page_match = re.search(r"PAGE (\d+)", line)
                if page_match:
                    current_page = int(page_match.group(1))
                i += 1
                continue
            
            # Skip empty lines and headers
            if not line.strip() or line.startswith("=") or "ยอดยกไป" in line:
                i += 1
                continue
            
            # Look for transaction pattern: date + time + channel
            # Example: "01-04-25\n05:27\nK PLUS\n32,062.15\n..."
            if re.match(r"\d{2}-\d{2}-\d{2}$", line.strip()):
                tx = self._parse_transaction_block(i, current_page)
                if tx:
                    transactions.append(tx)
                    # Skip lines that were part of this transaction
                    i += 10  # Typical transaction is ~6-10 lines
                else:
                    i += 1
            else:
                i += 1
        
        return transactions
    
    def _parse_transaction_block(self, start_idx: int, page: int) -> Optional[ParsedTransaction]:
        """Parse a single transaction block starting at start_idx"""
        
        # Get next 15 lines for context
        end_idx = min(start_idx + 15, len(self.lines))
        block = self.lines[start_idx:end_idx]
        block_text = '\n'.join(block)
        
        # Pattern: date, time, channel, amount (in various orders)
        date_line = block[0].strip() if len(block) > 0 else ""
        if not re.match(r"\d{2}-\d{2}-\d{2}$", date_line):
            return None
        
        # Extract components
        date = date_line
        time = ""
        channel = ""
        description_parts = []
        type_label = ""
        amount = None
        balance = None
        
        # Parse through block lines
        for i, line in enumerate(block[1:], 1):
            line_stripped = line.strip()
            
            # Time pattern
            if re.match(r"\d{2}:\d{2}$", line_stripped):
                time = line_stripped
                continue
            
            # Channel pattern
            if any(ch in line_stripped for ch in ["K PLUS", "ATM", "Internet/Mobile", "EDC/K SHOP"]):
                channel = line_stripped
                continue
            
            # Amount pattern (with comma)
            amount_match = re.match(r"^([\d,]+\.\d{2})$", line_stripped)
            if amount_match:
                if balance is None:
                    balance = float(amount_match.group(1).replace(',', ''))
                else:
                    # This is the transaction amount (2nd number)
                    amount = float(amount_match.group(1).replace(',', ''))
                continue
            
            # Type label
            if line_stripped in self.TYPE_MAPPING.keys():
                type_label = line_stripped
                continue
            
            # Description
            if line_stripped and line_stripped not in ["ยอดคงเหลือ", "(บาท)", "รายละเอียด"]:
                # Skip pure numbers, dates
                if not re.match(r'^[\d/:\s,\.-]+$', line_stripped):
                    description_parts.append(line_stripped)
        
        # If no amount found, skip (likely header or summary)
        if amount is None:
            return None
        
        # Determine transaction type
        tx_type = self.TYPE_MAPPING.get(type_label, "UNKNOWN")
        
        # Special case: if we see "จาก XXX" it's always incoming
        if re.search(r"จาก\s+[A-Z]", block_text):
            tx_type = "TRANSFER_IN"
        
        # Extract payer for incoming transfers
        payer = ""
        if tx_type == "TRANSFER_IN":
            payer_match = re.search(r"จาก\s+([A-Z]+)\s+X\d+\s+([^\+\n]+)", block_text)
            if payer_match:
                bank = payer_match.group(1)  # BBL, SCB, KTB
                name = payer_match.group(2).strip()
                payer = f"{bank} {name}"
        
        # Build description
        description = " | ".join(description_parts[:3])  # Max 3 parts
        
        # Calculate signed_amount based on type
        signed_amount = None
        if tx_type in self.OUT_TYPES:
            signed_amount = -amount
        elif tx_type in self.IN_TYPES:
            signed_amount = +amount
        elif tx_type == "CARRY_FORWARD":
            signed_amount = None  # No flow
        else:
            # Unknown - try to infer from keywords in description
            if "จาก" in block_text and re.search(r"จาก\s+[A-Z]", block_text):
                signed_amount = +amount
                tx_type = "TRANSFER_IN"
            elif any(kw in block_text for kw in ["โอนไป", "เพื่อชำระ", "ถอนเงินสด"]):
                signed_amount = -amount
                tx_type = "TRANSFER_OUT" if "โอนไป" in block_text else "PAYMENT"
            else:
                signed_amount = None
        
        # Calculate debit/credit columns
        debit = None
        credit = None
        if signed_amount is not None:
            if signed_amount < 0:
                debit = -signed_amount  # Positive value in debit column
            elif signed_amount > 0:
                credit = signed_amount  # Positive value in credit column
        
        return ParsedTransaction(
            page=page,
            date=date,
            time=time,
            channel=channel,
            description=description[:100],
            type=tx_type,
            amount=amount,
            signed_amount=signed_amount,
            debit=debit,
            credit=credit,
            balance=balance or 0.0,
            payer=payer[:50]
        )


def parse_raw_text_file(file_path: str) -> List[ParsedTransaction]:
    """Parse raw text file into transactions"""
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    parser = RawTextParser(raw_text)
    return parser.parse()


if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    if len(sys.argv) < 2:
        print("Usage: python raw_text_parser.py <raw_text_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    transactions = parse_raw_text_file(input_file)
    
    # Generate report
    output_file = input_file.replace("_raw_text_", "_parsed_table_")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 140 + "\n")
        f.write("KBANK PARSED TRANSACTION TABLE\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source: {input_file}\n")
        f.write("=" * 140 + "\n\n")
        
        # Summary
        total_debit = sum(t.debit for t in transactions if t.debit is not None)
        total_credit = sum(t.credit for t in transactions if t.credit is not None)
        debit_count = len([t for t in transactions if t.debit is not None])
        credit_count = len([t for t in transactions if t.credit is not None])
        
        f.write("SUMMARY\n")
        f.write("-" * 140 + "\n")
        f.write(f"Total transactions: {len(transactions)}\n")
        f.write(f"DEBIT  (เงินออก): {debit_count:4d} transactions = {total_debit:>15,.2f} THB\n")
        f.write(f"CREDIT (เงินเข้า): {credit_count:4d} transactions = {total_credit:>15,.2f} THB\n")
        f.write(f"Net Flow:                                   {total_credit - total_debit:>15,.2f} THB\n\n")
        
        # Type breakdown
        f.write("TYPE BREAKDOWN\n")
        f.write("-" * 140 + "\n")
        type_summary = {}
        for tx in transactions:
            if tx.type not in type_summary:
                type_summary[tx.type] = {'count': 0, 'total': 0.0}
            type_summary[tx.type]['count'] += 1
            if tx.signed_amount:
                type_summary[tx.type]['total'] += tx.signed_amount
        
        for tx_type in sorted(type_summary.keys()):
            stats = type_summary[tx_type]
            f.write(f"{tx_type:20s}: {stats['count']:4d} transactions, Net: {stats['total']:>15,.2f} THB\n")
        
        f.write("\n\n")
        
        # CSV Table
        f.write("TRANSACTION TABLE (CSV FORMAT)\n")
        f.write("=" * 140 + "\n")
        f.write("PAGE,DATE,TIME,CHANNEL,TYPE,AMOUNT,SIGNED,DEBIT,CREDIT,BALANCE,PAYER,DESCRIPTION\n")
        f.write("-" * 140 + "\n")
        
        for tx in transactions:
            signed_str = f"{tx.signed_amount:.2f}" if tx.signed_amount is not None else ""
            debit_str = f"{tx.debit:.2f}" if tx.debit is not None else ""
            credit_str = f"{tx.credit:.2f}" if tx.credit is not None else ""
            
            f.write(f"{tx.page},{tx.date},{tx.time},{tx.channel},{tx.type},{tx.amount:.2f},"
                   f"{signed_str},{debit_str},{credit_str},{tx.balance:.2f},{tx.payer},{tx.description}\n")
        
        f.write("\n" + "=" * 140 + "\n")
        f.write("END OF REPORT\n")
    
    print(f"✓ Parsed {len(transactions)} transactions")
    print(f"  DEBIT:  {debit_count} = {total_debit:,.2f} THB")
    print(f"  CREDIT: {credit_count} = {total_credit:,.2f} THB")
    print(f"  Saved to: {output_file}")

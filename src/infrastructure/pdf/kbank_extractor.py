"""
KBank (Kasikornbank) PDF Extractor
Implements IPDFExtractor for KBank Mobile/K PLUS statement format

โครงสร้างธุรกรรมจาก statement กสิกรไทย:

รูปแบบ block สำหรับแต่ละธุรกรรม:
    [วันที่ DD-MM-YY]
    [เวลา HH:MM]
    [ช่องทาง (อาจหลายบรรทัด)]
    [ยอดคงเหลือหลังรายการ]
    [รายละเอียดหลายบรรทัด]
    [ประเภทธุรกรรม เช่น "ชำระเงิน", "รับโอนเงิน", "ถอนเงินสด"]
    [จำนวนเงินของรายการ]

ใช้ state machine ในการ parse เพื่อความแม่นยำสูง
"""

import re
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import logging

try:
    import fitz  # PyMuPDF
except ImportError:
    pass  # Will be available in Docker container

from domain.entities.statement import Statement, Transaction
from application.ports.pdf_extractor import IPDFExtractor

logger = logging.getLogger(__name__)


class KBankPDFExtractor(IPDFExtractor):
    """Extract transactions from KBank (Kasikornbank) PDF statements"""

    # -----------------------
    # Regex patterns
    # -----------------------
    DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}$")              # e.g., "01-04-25"
    TIME_RE = re.compile(r"^\d{2}:\d{2}$")                     # e.g., "05:27"
    MONEY_RE = re.compile(r"^\d{1,3}(?:,\d{3})*\.\d{2}$")     # e.g., "12,278.00" or "875.50"

    # -----------------------
    # Transaction type keywords
    # -----------------------
    TX_TYPE_KEYWORDS_DEBIT = {
        "ชำระเงิน",        # จ่ายบิล / จ่ายร้าน
        "โอนเงิน",         # โอนไป ...
        "ถอนเงินสด",       # กดเงิน ATM
    }
    
    TX_TYPE_KEYWORDS_CREDIT = {
        "รับโอนเงิน",           # รับโอนเงิน
        "รับโอนเงินอัตโนมัติ",  # เงินเดือน/Payroll
        "รับโอนเงินผ่าน QR",    # รับผ่าน QR
    }
    
    TX_TYPE_KEYWORDS_ALL = TX_TYPE_KEYWORDS_DEBIT | TX_TYPE_KEYWORDS_CREDIT

    # -----------------------
    # Public API
    # -----------------------
    def extract(self, pdf_path: str, password: Optional[str] = None) -> Statement:
        """
        Extract statement from KBank PDF
        
        Steps:
        1. Open PDF document (with password if needed)
        2. Extract text from each page
        3. Parse transactions using state machine
        4. Return Statement entity with all transactions
        """
        import fitz
        
        doc = fitz.open(pdf_path)
        
        # Handle password-protected PDFs
        if doc.is_encrypted:
            if not password:
                doc.close()
                raise ValueError("PDF มีการป้องกันด้วยรหัสผ่าน กรุณาระบุรหัสผ่าน")
            
            if not doc.authenticate(password):
                doc.close()
                raise ValueError("รหัสผ่าน PDF ไม่ถูกต้อง")
        
        # Create Statement entity
        all_transactions: List[Transaction] = []
        page_count = doc.page_count  # Save before closing
        
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            
            # Extract transactions from this page
            page_transactions = self._extract_transactions_from_text(
                lines=lines,
                page_num=page_num + 1
            )
            
            all_transactions.extend(page_transactions)
        
        doc.close()
        
        print(f"[KBANK] Extracted {len(all_transactions)} transactions from {page_count} pages")
        
        return Statement(
            source_file=Path(pdf_path).name,
            total_pages=page_count,
            extracted_at=datetime.now(),
            transactions=all_transactions
        )
    
    # -----------------------
    # Page-level extraction
    # -----------------------
    def _extract_transactions_from_text(
        self,
        lines: List[str],
        page_num: int
    ) -> List[Transaction]:
        """
        Parse transactions from page text
        
        Auto-detects format:
        - Block format (state machine): K PLUS Mobile Banking
        - Table format: Table-based statement with columns
        """
        logger.debug(f"[KBANK extract_page] page={page_num} lines={len(lines)}")
        
        # Detect format by looking for table headers
        is_table_format = self._is_table_format(lines)
        
        if is_table_format:
            print(f"[KBANK] Detected table format on page {page_num}")
            txs = self._parse_kbank_table(lines, page_num)
        else:
            print(f"[KBANK] Detected block format on page {page_num}")
            txs = self._parse_kbank_page(lines, page_num)
        
        logger.debug(f"[KBANK extract_page] page={page_num} parsed_tx={len(txs)}")
        
        return txs
    
    # -----------------------
    # State machine parser
    # -----------------------
    def _parse_kbank_page(
        self,
        lines: List[str],
        page_num: int
    ) -> List[Transaction]:
        """
        State machine for parsing KBank statement page
        
        Transaction block format:
        1. Date (DD-MM-YY)
        2. Time (HH:MM)
        3. Channel (may span multiple lines)
        4. Balance after transaction
        5. Description (may span multiple lines)
        6. Transaction type keyword
        7. Transaction amount
        """
        
        txs: List[Transaction] = []
        i = 0
        n = len(lines)
        
        while i < n:
            line = lines[i].strip()
            
            # Look for date line (e.g., "01-04-25")
            if not self.DATE_RE.match(line):
                i += 1
                continue
            
            start_idx = i  # Save for Transaction.line_index
            date_str = line
            i += 1
            
            if i >= n:
                break
            
            # Check for "carry forward" block (ยอดยกมา/ยอดยกไป)
            # Format:
            #   05-04-25
            #   5,575.20
            #   ยอดยกมา
            if self._is_carry_forward_block(lines, start_idx):
                i = start_idx + 3  # Skip this block
                continue
            
            # ----- TIME -----
            time_str = None
            if i < n and self.TIME_RE.match(lines[i].strip()):
                time_str = lines[i].strip()
                i += 1
            
            if i >= n:
                break
            
            # ----- CHANNEL -----
            # Channel may span multiple lines (e.g., "ATM / Branch Name / Location")
            # Accumulate until we hit a money pattern (which is balance_after)
            channel_parts: List[str] = []
            while i < n and not self.MONEY_RE.match(lines[i].strip()):
                # If we hit another date, this block is malformed - abort
                if self.DATE_RE.match(lines[i].strip()):
                    logger.debug(
                        f"[KBANK page {page_num}] Encountered new date before balance; "
                        f"aborting current block at line {i}"
                    )
                    break
                
                channel_parts.append(lines[i].strip())
                i += 1
            
            if i >= n:
                break
            
            channel_str = " ".join(part for part in channel_parts if part)
            
            # ----- BALANCE AFTER -----
            balance_after = None
            if i < n and self.MONEY_RE.match(lines[i].strip()):
                balance_after = self._parse_money(lines[i].strip())
                i += 1
            else:
                # Missing balance - skip this block
                logger.debug(
                    f"[KBANK page {page_num}] Missing balance_after at line {i}; skip block"
                )
                continue
            
            # ----- DESCRIPTION LINES -----
            # Accumulate description lines until we hit a transaction type keyword
            desc_lines: List[str] = []
            tx_type: Optional[str] = None
            
            while i < n:
                candidate = lines[i].strip()
                
                # Check if this is a transaction type keyword
                if candidate in self.TX_TYPE_KEYWORDS_ALL:
                    tx_type = candidate
                    i += 1  # Move to amount line
                    break
                
                # If we hit a new date before tx_type, block is incomplete
                if self.DATE_RE.match(candidate):
                    logger.debug(
                        f"[KBANK page {page_num}] Hit next date before tx_type at line {i}; "
                        f"current block might be incomplete"
                    )
                    break
                
                desc_lines.append(candidate)
                i += 1
            
            description = " ".join(seg for seg in desc_lines if seg)
            
            # ----- AMOUNT (transaction amount) -----
            amount_val: Optional[float] = None
            if i < n and self.MONEY_RE.match(lines[i].strip()):
                amount_val = self._parse_money(lines[i].strip())
                i += 1
            
            # ----- DETERMINE CREDIT / DEBIT -----
            if tx_type in self.TX_TYPE_KEYWORDS_CREDIT:
                is_credit = True
            elif tx_type in self.TX_TYPE_KEYWORDS_DEBIT:
                is_credit = False
            else:
                # Fallback heuristic if tx_type not found
                blob = f"{tx_type or ''} {description}"
                is_credit = "รับโอนเงิน" in blob
            
            # ----- PAYER (for credits only) -----
            payer = None
            if is_credit:
                payer = self._extract_payer_from_desc(desc_lines)
            
            # ----- Create Transaction object -----
            tx_obj = Transaction(
                page=page_num,
                line_index=start_idx,
                date=date_str,
                time=time_str,
                channel=channel_str or None,
                description=description or None,
                amount=amount_val,
                is_credit=is_credit,
                payer=payer,
            )
            
            txs.append(tx_obj)
        
        return txs
    
    # -----------------------
    # Helper methods
    # -----------------------
    def _is_carry_forward_block(
        self,
        lines: List[str],
        i: int
    ) -> bool:
        """
        Check for 'carry forward' pattern (ยอดยกมา/ยอดยกไป)
        
        Format:
            [DD-MM-YY]
            [BALANCE_AFTER]
            ยอดยกมา
        """
        
        if i + 2 >= len(lines):
            return False
        
        date_line = lines[i].strip()
        bal_line = lines[i + 1].strip()
        next_line = lines[i + 2].strip()
        
        if not self.DATE_RE.match(date_line):
            return False
        if not self.MONEY_RE.match(bal_line):
            return False
        if "ยอดยกมา" in next_line or "ยอดยกไป" in next_line:
            return True
        
        return False
    
    def _extract_payer_from_desc(self, desc_lines: List[str]) -> Optional[str]:
        """
        Extract payer name from description for salary detection
        
        Examples:
            "จาก SCB X5247 นาย กฤษฎา รักเพื่++"           → "นาย กฤษฎา รักเพื่"
            "จาก KTB X4993 NUT SUBWIR++"                 → "NUT SUBWIR"
            "จาก SMART SCBT X1690 *BOOTS RETAIL (T) ++"  → "BOOTS RETAIL"
            "จาก X5027 MR. JAYARAJ  NIRMA++"              → "MR. JAYARAJ  NIRMA"
        """
        
        full_desc = " ".join(desc_lines)
        
        # Look for "จาก XXX" pattern
        if "จาก" not in full_desc:
            return None
        
        parts = full_desc.split("จาก", 1)
        if len(parts) < 2:
            return None
        
        after_jak = parts[1].strip()
        
        # Remove ++ and special characters at the end
        after_jak = re.sub(r"\+\+.*$", "", after_jak).strip()
        
        # Extract name after " X####" (account number) - this is usually the actual person/company name
        if " X" in after_jak:
            parts_by_x = after_jak.split(" X", 1)
            if len(parts_by_x) > 1:
                # Get text after "X####" pattern
                after_x = parts_by_x[1]
                # Skip the account number (first token after X)
                tokens = after_x.split()
                if len(tokens) > 1:
                    # Join remaining tokens as name (skip account number)
                    name = " ".join(tokens[1:]).strip()
                    if len(name) >= 3:
                        print(f"[KBANK PAYER_EXTRACT] desc='{full_desc[:60]}...' → payer='{name}'")
                        return name
            
            # If no name after X####, use bank name before X####
            before_x = parts_by_x[0].strip()
            if len(before_x) >= 2:
                print(f"[KBANK PAYER_EXTRACT_BANK] desc='{full_desc[:60]}...' → payer='{before_x}'")
                return before_x
        
        # Fallback: use first word after "จาก" (e.g., "SCB", "BBL", "KTB")
        first_word = after_jak.split()[0] if after_jak.split() else None
        if first_word:
            print(f"[KBANK PAYER_EXTRACT_FALLBACK] desc='{full_desc[:60]}...' → payer='{first_word}'")
        return first_word
    
    def _parse_money(self, money_str: str) -> float:
        """
        Convert Thai money format to float
        
        Examples:
            "12,278.00" → 12278.00
            "875.50"    → 875.50
        """
        return float(money_str.replace(",", ""))
    
    # -----------------------
    # Table format support
    # -----------------------
    def _is_table_format(self, lines: List[str]) -> bool:
        """
        Detect if this is table format by looking for column headers
        
        Table format has headers like:
        - "วันที่" / "เวลา" / "ช่องทาง" / "รายการ" / "ยอดคงเหลือ"
        """
        # Join first 30 lines to check for table headers
        header_text = " ".join(lines[:30])
        
        # Check for table header keywords
        has_date_header = "วันที่" in header_text
        has_channel_header = "ช่องทาง" in header_text or "รายการ" in header_text
        has_balance_header = "ยอดคงเหลือ" in header_text
        
        return has_date_header and has_channel_header and has_balance_header
    
    def _parse_kbank_table(
        self,
        lines: List[str],
        page_num: int
    ) -> List[Transaction]:
        """
        Parse KBank table format
        
        Transaction block structure:
        [วันที่ DD-MM-YY]
        [เวลา HH:MM]
        [ช่องทาง]
        [ยอดคงเหลือ]
        [รายละเอียด]
        [ประเภทธุรกรรม]
        [จำนวนเงิน]
        """
        
        txs: List[Transaction] = []
        i = 0
        n = len(lines)
        
        while i < n:
            line = lines[i].strip()
            
            # Look for date line (DD-MM-YY format)
            if not self.DATE_RE.match(line):
                i += 1
                continue
            
            start_idx = i
            date_str = line
            i += 1
            
            if i >= n:
                break
            
            # Check for carry forward (ยอดยกมา)
            if i < n and "ยอดยกมา" in lines[i]:
                i += 1
                continue
            
            # Parse time (HH:MM)
            time_str = None
            if i < n and self.TIME_RE.match(lines[i].strip()):
                time_str = lines[i].strip()
                i += 1
            
            if i >= n:
                break
            
            # Channel (e.g., "K PLUS", "EDC/K SHOP", "Internet/Mobile SCB")
            channel_str = None
            if i < n and not self.MONEY_RE.match(lines[i].strip()):
                channel_str = lines[i].strip()
                i += 1
            
            if i >= n:
                break
            
            # Balance after transaction
            balance_after = None
            if i < n and self.MONEY_RE.match(lines[i].strip()):
                balance_after = self._parse_money(lines[i].strip())
                i += 1
            else:
                # Missing balance - skip this block
                continue
            
            if i >= n:
                break
            
            # Description (may span multiple lines until we hit tx_type)
            desc_lines: List[str] = []
            tx_type: Optional[str] = None
            
            while i < n:
                candidate = lines[i].strip()
                
                # Check if this is transaction type keyword
                if candidate in self.TX_TYPE_KEYWORDS_ALL:
                    tx_type = candidate
                    i += 1
                    break
                
                # If we hit another date or money pattern, stop
                if self.DATE_RE.match(candidate):
                    break
                
                desc_lines.append(candidate)
                i += 1
            
            description = " ".join(seg for seg in desc_lines if seg)
            
            # Amount (last line of block)
            amount_val: Optional[float] = None
            if i < n and self.MONEY_RE.match(lines[i].strip()):
                amount_val = self._parse_money(lines[i].strip())
                i += 1
            
            if amount_val is None:
                # No amount found, skip
                continue
            
            # Determine credit/debit
            if tx_type in self.TX_TYPE_KEYWORDS_CREDIT:
                is_credit = True
            elif tx_type in self.TX_TYPE_KEYWORDS_DEBIT:
                is_credit = False
            else:
                # Heuristic: check description
                blob = f"{tx_type or ''} {description}"
                is_credit = "รับโอนเงิน" in blob or "รับดอกเบี้ย" in blob or "My QR" in description
            
            # Extract payer for credits
            payer = None
            if is_credit:
                payer = self._extract_payer_from_desc(desc_lines)
            
            # Create transaction
            tx_obj = Transaction(
                page=page_num,
                line_index=start_idx,
                date=date_str,
                time=time_str,
                channel=channel_str or None,
                description=description or None,
                amount=amount_val,
                is_credit=is_credit,
                payer=payer,
            )
            
            txs.append(tx_obj)
        
        return txs


"""
Infrastructure Adapter: PyMuPDF Extractor
Implements IPDFExtractor using PyMuPDF (fitz) library
"""

import re
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import logging

from application.ports.pdf_extractor import IPDFExtractor
from domain.entities.statement import Statement
from domain.entities.transaction import Transaction

logger = logging.getLogger(__name__)


class PyMuPDFExtractor(IPDFExtractor):
    """PDF extraction using PyMuPDF (fitz)"""
    
    def extract(self, pdf_path: str, password: Optional[str] = None) -> Statement:
        """Extract text and transactions from PDF"""
        
        doc = fitz.open(pdf_path)
        
        # Handle encrypted PDFs
        if doc.is_encrypted:
            if password:
                if not doc.authenticate(password):
                    doc.close()
                    raise ValueError("รหัสผ่าน PDF ไม่ถูกต้อง")
            else:
                doc.close()
                raise ValueError("PDF มีการป้องกันด้วยรหัสผ่าน กรุณาระบุรหัสผ่าน")
        
        # Create statement entity
        statement = Statement(
            source_file=Path(pdf_path).name,
            total_pages=len(doc),
            extracted_at=datetime.now(),
            pages=[]
        )
        
        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            lines = text.split('\n')
            
            statement.pages.append({
                "page_number": page_num + 1,
                "text": text,
                "lines": [line for line in lines if line.strip()]
            })
            
            # Extract transactions from this page
            transactions = self._extract_transactions_from_text(
                text, page_num + 1
            )
            for tx in transactions:
                statement.add_transaction(tx)
        
        doc.close()
        return statement
    
    def _extract_transactions_from_text(
        self, 
        text: str, 
        page_num: int
    ) -> list[Transaction]:
        """Extract transaction entities from page text"""
        
        transactions = []
        lines = text.split('\n')
        
        # Transaction patterns
        amount_pattern = r"(\d{1,3}(?:,\d{3})*\.\d{2})"
        credit_patterns = [
            # Thai patterns
            "รับโอนเงิน", "ฝากเงิน", "เงินโอนเข้า", 
            "เงินเดือน", "BSD02", "(BSD02)",
            "รับโอนเงินผ่าน QR", "โอนเข้า",
            "IORSDT", "(IORSDT)",  # KTB: เงินโอนเข้า
            "ฝากเงินสด", "ฝาก", "เงินเข้า",
            # English patterns
            "TRANSFER IN", "RECEIVE", "DEPOSIT",
            "SAL", "SALARY", "PAY", "PAYMENT RECEIVED",
            "INCOMING", "CREDIT"
        ]
        
        debit_patterns = [
            "จ่ายค่า", "โอนเงินออก", "ถอนเงิน",
            "NBSWP", "MORWSW", "CGSWP", "MORPSW",  # KTB transaction codes
            "MORISW", "NMIDSW"
        ]
        
        logger.debug(f"Processing page {page_num} with {len(lines)} lines")
        
        credit_count = 0
        debit_count = 0
        
        # Track transaction codes to avoid treating consecutive amounts as duplicates
        transaction_codes = ["BSD02", "IORSDT", "MORWSW", "MORPSW", "NBSWP", "NMIDSW", "CGSWP", "MORISW"]
        processed_lines = set()  # Track processed balance lines
        
        for idx, line in enumerate(lines):
            # Skip if already processed as balance
            if idx in processed_lines:
                continue
            
            # Find amounts in line
            amounts = re.findall(amount_pattern, line)
            if not amounts:
                continue
            
            # Check if this is a balance line (appears right after transaction amount)
            # Balance = transaction + small difference, appears on next line
            if idx > 0:
                prev_amounts = re.findall(amount_pattern, lines[idx-1])
                if prev_amounts and len(amounts) == 1 and len(prev_amounts) == 1:
                    try:
                        current_val = float(amounts[0].replace(',', ''))
                        prev_val = float(prev_amounts[0].replace(',', ''))
                        
                        # Balance is typically slightly higher than transaction (accumulated)
                        # and differs by less than 10%
                        if current_val > prev_val and (current_val - prev_val) / prev_val < 0.1:
                            processed_lines.add(idx)
                            continue
                    except:
                        pass
            
            # Check if credit transaction - ตรวจสอบ 2 บรรทัดก่อนหน้า และ 5 บรรทัดถัดไป
            context_start = max(0, idx-2)
            context_end = min(idx+6, len(lines))
            context_lines = '\n'.join(lines[context_start:context_end])
            
            # Check for specific transaction codes first (most reliable)
            specific_credit_codes = ["BSD02", "IORSDT"]
            specific_debit_codes = ["NBSWP", "MORWSW", "CGSWP", "MORPSW", "MORISW", "NMIDSW"]
            
            # Look in closer context (2 lines before, 1 line after) for transaction codes
            # Transaction code typically appears 1-2 lines before the amount
            close_context = '\n'.join(lines[max(0,idx-3):min(len(lines),idx+2)])
            
            has_credit_code = any(code in close_context for code in specific_credit_codes)
            has_debit_code = any(code in close_context for code in specific_debit_codes)
            
            if has_credit_code and not has_debit_code:
                is_credit = True
            elif has_debit_code and not has_credit_code:
                is_credit = False
            else:
                # Fallback to pattern matching
                is_debit = any(pattern in context_lines for pattern in debit_patterns)
                if is_debit:
                    is_credit = False
                else:
                    is_credit = any(pattern.lower() in context_lines.lower() for pattern in credit_patterns)
            
            if is_credit:
                credit_count += 1
            else:
                debit_count += 1
            
            # Extract time if present
            time_match = re.search(r"(\d{2}:\d{2})", context_lines)
            time_str = time_match.group(1) if time_match else None
            
            # Extract date if present (DD/MM/YY or DD/MM/YYYY)
            date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", context_lines)
            date_str = date_match.group(1) if date_match else None
            
            # Extract channel
            channel = None
            if "(BSD02)" in context_lines or "BSD02" in context_lines:
                channel = "BSD02"
            elif "K PLUS" in context_lines:
                channel = "K PLUS"
            elif "Internet/Mobile" in context_lines:
                channel = "Internet/Mobile"
            
            # Extract payer (simple heuristic) - หาในบรรทัดถัดไป
            payer = None
            for next_line in lines[idx+1:min(idx+4, len(lines))]:
                # หาคำว่า "จาก" หรือชื่อที่เป็นตัวพิมพ์ใหญ่
                if "จาก" in next_line or "KTB" in next_line or "SCB" in next_line:
                    payer = next_line.strip()
                    break
                for word in next_line.split():
                    if word.isupper() and len(word) > 3:
                        payer = word
                        break
                if payer:
                    break
            
            # รวมคำอธิบายจาก 2-3 บรรทัดก่อนหน้า (ที่มีชื่อ transaction type)
            desc_start = max(0, idx-3)
            desc_lines = []
            for i in range(desc_start, idx):
                line_text = lines[i].strip()
                # Skip lines that are only numbers, dates, or empty
                if line_text and not re.match(r'^[\d/:\s,\.]+$', line_text):
                    desc_lines.append(line_text)
            
            description = ' | '.join(desc_lines[-2:]) if desc_lines else f"Transaction at line {idx}"  # Last 2 descriptive lines
            
            # Create transaction for each amount found
            for amount_str in amounts:
                try:
                    amount = float(amount_str.replace(",", ""))
                    
                    transaction = Transaction(
                        page=page_num,
                        line_index=idx,
                        amount=amount,
                        description=description[:200],  # จำกัด 200 ตัวอักษร
                        is_credit=is_credit,
                        date=date_str,
                        time=time_str,
                        channel=channel,
                        payer=payer
                    )
                    transactions.append(transaction)
                    
                except ValueError:
                    continue
        
        return transactions

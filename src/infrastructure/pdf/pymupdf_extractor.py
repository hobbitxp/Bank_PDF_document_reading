"""
Infrastructure Adapter: PyMuPDF Extractor
Implements IPDFExtractor using PyMuPDF (fitz) library
"""

import re
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from application.ports.pdf_extractor import IPDFExtractor
from domain.entities.statement import Statement
from domain.entities.transaction import Transaction


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
            "รับโอนเงิน", "ฝากเงิน", "เงินโอนเข้า", 
            "เงินเดือน", "BSD02", "(BSD02)",
            "รับโอนเงินผ่าน QR", "โอนเข้า"
        ]
        
        for idx, line in enumerate(lines):
            # Find amounts in line
            amounts = re.findall(amount_pattern, line)
            if not amounts:
                continue
            
            # Check if credit transaction - ตรวจสอบทั้งบรรทัดปัจจุบันและ 3 บรรทัดถัดไป
            context_lines = '\n'.join(lines[idx:min(idx+4, len(lines))])
            # Check if credit transaction - ตรวจสอบทั้งบรรทัดปัจจุบันและ 3 บรรทัดถัดไป
            context_lines = '\n'.join(lines[idx:min(idx+4, len(lines))])
            is_credit = any(pattern in context_lines for pattern in credit_patterns)
            
            # Extract time if present
            time_match = re.search(r"(\d{2}:\d{2})", context_lines)
            time_str = time_match.group(1) if time_match else None
            
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
            
            # รวมคำอธิบายจาก 3 บรรทัด
            description = ' '.join([lines[i].strip() for i in range(idx, min(idx+3, len(lines))) if lines[i].strip()])
            
            # รวมคำอธิบายจาก 3 บรรทัด
            description = ' '.join([lines[i].strip() for i in range(idx, min(idx+3, len(lines))) if lines[i].strip()])
            
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
                        time=time_str,
                        channel=channel,
                        payer=payer
                    )
                    transactions.append(transaction)
                    
                except ValueError:
                    continue
        
        return transactions

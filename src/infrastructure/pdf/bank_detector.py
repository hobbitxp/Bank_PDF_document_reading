"""
Bank Statement Format Detector

Detects bank from PDF content to route to correct parser
"""

import re
from typing import Optional
import fitz


class BankDetector:
    """Detect bank from PDF statement content"""
    
    @staticmethod
    def detect_bank(pdf_path: str, password: Optional[str] = None) -> str:
        """
        Detect bank from PDF content
        
        Returns:
            "KBANK" | "KTB" | "SCB" | "BBL" | "UNKNOWN"
        """
        doc = fitz.open(pdf_path)
        
        if doc.is_encrypted:
            if password:
                doc.authenticate(password)
            else:
                doc.close()
                raise ValueError("PDF is encrypted, password required")
        
        # Extract first 2 pages for detection
        sample_text = ""
        for page_num in range(min(2, doc.page_count)):
            page = doc[page_num]
            sample_text += page.get_text()
        
        doc.close()
        
        # Detect by footer/header patterns
        sample_upper = sample_text.upper()
        
        # SCB (Siam Commercial Bank) - check first before KBANK
        # because SCB statements may contain "กสิกรไทย" in transaction descriptions
        if "ธนาคารไทยพาณิชย์" in sample_text or "SIAM COMMERCIAL" in sample_upper:
            return "SCB"
        
        # KTB (Krungthai Bank)
        if "ธนาคารกรุงไทย" in sample_text or "KRUNGTHAI" in sample_upper:
            return "KTB"
        
        # KBANK (Kasikorn Bank)
        if "ธนาคารกสิกรไทย" in sample_text or "KASIKORNBANK" in sample_upper:
            return "KBANK"
        if "K-MOBILE BANKING" in sample_upper or "K PLUS" in sample_upper or "K-PLUS" in sample_upper:
            return "KBANK"
        if "กสิกร" in sample_text or "KBANK" in sample_upper:
            return "KBANK"
        
        # BBL (Bangkok Bank)
        if "ธนาคารกรุงเทพ" in sample_text or "BANGKOK BANK" in sample_upper:
            return "BBL"
        
        # TMB/TTB (TMB Thanachart Bank)
        if "ธนาคารทหารไทยธนชาต" in sample_text or "TMB" in sample_upper or "THANACHART" in sample_upper:
            return "TMB"
        if "TTB" in sample_upper or "ทีทีบี" in sample_text or "ttbbank.com" in sample_text:
            return "TMB"
        
        print(f"[WARN] Could not detect bank from PDF. Sample text (first 200 chars):\n{sample_text[:200]}")
        return "UNKNOWN"

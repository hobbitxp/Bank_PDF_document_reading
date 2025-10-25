"""
Infrastructure Adapter: Regex Data Masker
Implements IDataMasker using regex patterns for PDPA compliance
"""

import re
from typing import Tuple, Dict

from application.ports.data_masker import IDataMasker
from domain.entities.statement import Statement


class RegexDataMasker(IDataMasker):
    """PDPA-compliant data masking using regex patterns"""
    
    # Masking patterns
    PATTERNS = {
        'thai_id': r'\b\d{13}\b',
        'account': r'\b\d{3,4}-\d+-\d{5,7}-?\d?\b',
        'thai_name': [
            r'นาย\s+[ก-๙]+\s+[ก-๙]+',
            r'นาง\s+[ก-๙]+\s+[ก-๙]+',
            r'นางสาว\s+[ก-๙]+\s+[ก-๙]+'
        ],
        'phone': [
            r'\b0\d{2}-\d{3}-\d{4}\b',
            r'\b0\d{9}\b'
        ],
        'address': r'เลขที่\s+\d+.*?(?=\s+\d{5}|\n|$)',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    }
    
    def mask(self, statement: Statement) -> Tuple[Statement, Dict[str, str]]:
        """Mask sensitive data in statement"""
        
        mapping = {}
        
        # Mask each page's text and lines
        for page in statement.pages:
            if "text" in page:
                page["text"], page_mapping = self._mask_text(page["text"], mapping)
                mapping.update(page_mapping)
            
            if "lines" in page:
                masked_lines = []
                for line in page["lines"]:
                    if isinstance(line, str):
                        masked_line, line_mapping = self._mask_text(line, mapping)
                        masked_lines.append(masked_line)
                        mapping.update(line_mapping)
                    else:
                        masked_lines.append(line)
                page["lines"] = masked_lines
        
        # Mask transaction descriptions
        for transaction in statement.transactions:
            transaction.description, tx_mapping = self._mask_text(
                transaction.description, mapping
            )
            mapping.update(tx_mapping)
            
            # Mask payer if present
            if transaction.payer:
                transaction.payer, payer_mapping = self._mask_text(
                    transaction.payer, mapping
                )
                mapping.update(payer_mapping)
        
        statement.masked = True
        statement.masked_items_count = len(mapping)
        
        return statement, mapping
    
    def _mask_text(self, text: str, existing_mapping: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
        """Mask sensitive data in text"""
        
        masked_text = text
        new_mapping = {}
        
        # 1. Mask Thai ID
        for match in re.finditer(self.PATTERNS['thai_id'], text):
            original = match.group(0)
            if original not in existing_mapping.values():
                masked_token = f"THAIID_{len(existing_mapping) + len(new_mapping) + 1:03d}"
                new_mapping[masked_token] = original
                masked_text = masked_text.replace(original, masked_token)
        
        # 2. Mask account numbers
        for match in re.finditer(self.PATTERNS['account'], masked_text):
            original = match.group(0)
            if original not in existing_mapping.values() and original not in new_mapping.values():
                masked_token = f"ACCOUNT_{len(existing_mapping) + len(new_mapping) + 1:03d}"
                new_mapping[masked_token] = original
                masked_text = masked_text.replace(original, masked_token)
        
        # 3. Mask Thai names
        for pattern in self.PATTERNS['thai_name']:
            for match in re.finditer(pattern, masked_text):
                original = match.group(0)
                if original not in existing_mapping.values() and original not in new_mapping.values():
                    masked_token = f"NAME_{len(existing_mapping) + len(new_mapping) + 1:03d}"
                    new_mapping[masked_token] = original
                    masked_text = masked_text.replace(original, masked_token)
        
        # 4. Mask phone numbers
        for pattern in self.PATTERNS['phone']:
            for match in re.finditer(pattern, masked_text):
                original = match.group(0)
                if original not in existing_mapping.values() and original not in new_mapping.values():
                    masked_token = f"PHONE_{len(existing_mapping) + len(new_mapping) + 1:03d}"
                    new_mapping[masked_token] = original
                    masked_text = masked_text.replace(original, masked_token)
        
        # 5. Mask emails
        for match in re.finditer(self.PATTERNS['email'], masked_text):
            original = match.group(0)
            if original not in existing_mapping.values() and original not in new_mapping.values():
                masked_token = f"EMAIL_{len(existing_mapping) + len(new_mapping) + 1:03d}"
                new_mapping[masked_token] = original
                masked_text = masked_text.replace(original, masked_token)
        
        return masked_text, new_mapping

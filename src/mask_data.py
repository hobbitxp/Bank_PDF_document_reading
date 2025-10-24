#!/usr/bin/env python3
"""
Mask sensitive data before sending to external API (GPT, Gemini, etc.)
To comply with PDPA (Personal Data Protection Act)
"""

import json
import re
import sys
from typing import Dict, Any


def mask_personal_data(text: str) -> tuple[str, Dict[str, str]]:
    """
    Mask sensitive personal information
    Returns: (masked_text, mapping_dict)
    """
    mapping = {}
    masked_text = text
    
    # 1. Mask Thai ID (13 digits)
    thai_id_pattern = r'\b\d{13}\b'
    for match in re.finditer(thai_id_pattern, masked_text):
        original = match.group(0)
        masked = f"THAIID_{len(mapping)+1:03d}"
        mapping[masked] = original
        masked_text = masked_text.replace(original, masked)
    
    # 2. Mask account numbers (xxx-x-xxxxx-x format)
    account_pattern = r'\b\d{3,4}-\d+-\d{5,7}-?\d?\b'
    for match in re.finditer(account_pattern, masked_text):
        original = match.group(0)
        masked = f"ACCOUNT_{len(mapping)+1:03d}"
        mapping[masked] = original
        masked_text = masked_text.replace(original, masked)
    
    # 3. Mask Thai names (นาย, นาง, นางสาว + Thai characters)
    name_patterns = [
        r'นาย\s+[ก-๙]+\s+[ก-๙]+',
        r'นาง\s+[ก-๙]+\s+[ก-๙]+',
        r'นางสาว\s+[ก-๙]+\s+[ก-๙]+'
    ]
    for pattern in name_patterns:
        for match in re.finditer(pattern, masked_text):
            original = match.group(0)
            if original not in mapping.values():
                masked = f"NAME_{len(mapping)+1:03d}"
                mapping[masked] = original
                masked_text = masked_text.replace(original, masked)
    
    # 4. Mask phone numbers (0xx-xxx-xxxx or 0xxxxxxxxx)
    phone_patterns = [
        r'\b0\d{2}-\d{3}-\d{4}\b',
        r'\b0\d{9}\b'
    ]
    for pattern in phone_patterns:
        for match in re.finditer(pattern, masked_text):
            original = match.group(0)
            masked = f"PHONE_{len(mapping)+1:03d}"
            mapping[masked] = original
            masked_text = masked_text.replace(original, masked)
    
    # 5. Mask addresses (keep general area only)
    address_pattern = r'\d+/\d+[^\n]+'
    for match in re.finditer(address_pattern, masked_text):
        original = match.group(0)
        masked = f"ADDRESS_{len(mapping)+1:03d}"
        mapping[masked] = original
        masked_text = masked_text.replace(original, masked)
    
    # 6. Mask email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    for match in re.finditer(email_pattern, masked_text):
        original = match.group(0)
        masked = f"EMAIL_{len(mapping)+1:03d}"
        mapping[masked] = original
        masked_text = masked_text.replace(original, masked)
    
    return masked_text, mapping


def mask_json_file(input_file: str, output_file: str = None):
    """Mask sensitive data in JSON file"""
    
    # Read original JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_mappings = {}
    
    # Mask each page
    for page in data['pages']:
        masked_text, mapping = mask_personal_data(page['text'])
        page['text'] = masked_text
        all_mappings.update(mapping)
    
    # Save masked JSON
    if output_file is None:
        output_file = input_file.replace('_extracted.json', '_masked.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Save mapping (for internal use only - DO NOT send to API)
    mapping_file = output_file.replace('.json', '_mapping.json')
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(all_mappings, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Masked data บันทึกที่: {output_file}")
    print(f"🔑 Mapping บันทึกที่: {mapping_file}")
    print(f"📊 จำนวนข้อมูลที่ mask: {len(all_mappings)} รายการ")
    print("\n⚠️  คำเตือน:")
    print("   - ส่งเฉพาะไฟล์ *_masked.json ไปยัง API เท่านั้น")
    print("   - ไฟล์ *_mapping.json เก็บไว้ที่เครื่องตัวเองเท่านั้น!")
    
    return output_file, mapping_file


def unmask_response(response_text: str, mapping_file: str) -> str:
    """Unmask the API response using mapping"""
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    unmasked_text = response_text
    for masked, original in mapping.items():
        unmasked_text = unmasked_text.replace(masked, original)
    
    return unmasked_text


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python mask_data.py <json_file>")
        print("\nExample:")
        print("  python mask_data.py data/json/statement_extracted.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    mask_json_file(input_file)

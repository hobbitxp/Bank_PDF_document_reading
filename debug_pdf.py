#!/usr/bin/env python3
import fitz

pdf_path = "/home/kisda/dev/temp_/Bank_PDF_document_reading/Test/Statement_24OCT2025_1af9f08a-bae8-424e-a7cb-f8b02275ec10.pdf"
password = "3409900091575"

doc = fitz.open(pdf_path)
doc.authenticate(password)

# Page 1
page = doc[0]
text = page.get_text()
lines = text.split('\n')

print("=== Lines 30-100 from Page 1 ===")
for i in range(30, min(100, len(lines))):
    print(f"{i:3d}: {lines[i]}")

print("\n=== Lines with amounts (first page) ===")
import re
amount_pattern = r"(\d{1,3}(?:,\d{3})*\.\d{2})"
for i, line in enumerate(lines[:200]):
    if re.search(amount_pattern, line):
        context_start = max(0, i-2)
        context_end = min(i+5, len(lines))
        print(f"\n--- Line {i} ---")
        for j in range(context_start, context_end):
            marker = ">>> " if j == i else "    "
            print(f"{marker}{j:3d}: {lines[j]}")

doc.close()

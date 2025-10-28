#!/usr/bin/env python3
"""Test extractor without Docker dependencies"""
import fitz
import re

pdf_path = "Test/kbank27051987.pdf"
password = "27051987"

# Type mapping
TYPE_MAPPING = {
    "ชำระเงิน": "PAYMENT",
    "เพื่อชำระ": "PAYMENT",
    "โอนเงิน": "TRANSFER_OUT",
    "โอนไป": "TRANSFER_OUT",
    "ถอนเงินสด": "CASH_WITHDRAWAL",
    "รับโอนเงิน": "TRANSFER_IN",
    "รับเงินโอน": "TRANSFER_IN",
    "รับโอนเงินอัตโนมัติ": "TRANSFER_IN",
    "รับโอนเงินผ่าน QR": "TRANSFER_IN",
    "ยอดยกมา": "CARRY_FORWARD",
    "ยอดยกไป": "CARRY_FORWARD"
}

IN_TYPES = {"TRANSFER_IN"}

doc = fitz.open(pdf_path)
doc.authenticate(password)

transactions = []

for page_num in range(doc.page_count):
    page = doc[page_num]
    text = page.get_text()
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for date pattern
        if not re.match(r"^\d{2}-\d{2}-\d{2}$", line):
            i += 1
            continue
        
        # Extract transaction block (next 20 lines)
        date = line
        block = lines[i:min(i+20, len(lines))]
        block_text = '\n'.join(block)
        
        # Find amounts
        amounts = []
        tx_type = "UNKNOWN"
        payer = None
        
        for bl in block[1:]:
            bl_s = bl.strip()
            # Amount
            if re.match(r"^[\d,]+\.\d{2}$", bl_s):
                try:
                    amounts.append(float(bl_s.replace(',', '')))
                except:
                    pass
            
            # Type
            for keyword, ttype in TYPE_MAPPING.items():
                if keyword in bl_s:
                    tx_type = ttype
        
        # Infer type from "จาก"
        if "จาก" in block_text and re.search(r"จาก\s+[A-Z]", block_text):
            tx_type = "TRANSFER_IN"
            # Extract payer - handle multiline format
            # Example: "จาก SMART SCBT X1690 *BOOTS RETAIL (T) ++"
            m = re.search(r"จาก\s+([A-Z][A-Z\s]+?)\s+X\d+", block_text, re.MULTILINE)
            if m:
                payer = m.group(1).strip()
                # Clean: "SMART SCBT" or "BBL" or "SCB"
                payer = re.sub(r'\s+', ' ', payer)  # Normalize spaces
            else:
                # Fallback: just get first word after "จาก"
                m2 = re.search(r"จาก\s+([A-Z]+)", block_text)
                if m2:
                    payer = m2.group(1)
        
        # Pick amount
        if len(amounts) > 1 and "รับโอนเงินอัตโนมัติ" in block_text:
            amount = amounts[-1]  # Salary: pick last (smaller) amount
        elif amounts:
            amount = min(amounts)  # Pick smaller amount
        else:
            i += 1
            continue
        
        # Skip carry forward
        if tx_type == "CARRY_FORWARD":
            i += 15
            continue
        
        is_credit = tx_type in IN_TYPES
        
        transactions.append({
            'date': date,
            'amount': amount,
            'is_credit': is_credit,
            'type': tx_type,
            'payer': payer or ''
        })
        
        i += 15

doc.close()

# Report
credits = [t for t in transactions if t['is_credit']]
debits = [t for t in transactions if not t['is_credit']]

print(f"Total: {len(transactions)}")
print(f"Credits: {len(credits)} = {sum(t['amount'] for t in credits):,.2f} THB")
print(f"Debits: {len(debits)} = {sum(t['amount'] for t in debits):,.2f} THB")

print(f"\nSalary (66,386.96):")
salary = [t for t in credits if 66380 < t['amount'] < 66400]
print(f"Found: {len(salary)}")
for s in salary:
    print(f"  {s['date']} | {s['amount']:,.2f} | Payer: '{s['payer']}'")

print(f"\nTop 10 Credits:")
top = sorted(credits, key=lambda x: x['amount'], reverse=True)[:10]
for i, t in enumerate(top, 1):
    print(f"{i:2d}. {t['date']} | {t['amount']:>12,.2f} | {t['payer'][:30]:30s}")

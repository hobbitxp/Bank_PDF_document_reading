#!/usr/bin/env python3
"""
Test script to check extractor output directly
"""
import sys
sys.path.insert(0, '/app')

from src.infrastructure.pdf.pymupdf_extractor import PyMuPDFExtractor

# Test extraction
extractor = PyMuPDFExtractor()
statement = extractor.extract("/app/Test/kbank27051987.pdf", password="27051987")

print(f"=== Extraction Results ===")
print(f"Total transactions: {len(statement.transactions)}")

# Classify
credits = [t for t in statement.transactions if t.is_credit]
debits = [t for t in statement.transactions if not t.is_credit]

print(f"Credits: {len(credits)} = {sum(t.amount for t in credits):,.2f} THB")
print(f"Debits:  {len(debits)} = {sum(t.amount for t in debits):,.2f} THB")

# Check salary
print(f"\n=== Salary Transactions (66,386.96 THB) ===")
salary_txs = [t for t in credits if 66380 < t.amount < 66400]
print(f"Found: {len(salary_txs)}")
for tx in salary_txs:
    print(f"  Date: {tx.date} | Amount: {tx.amount:,.2f} | Payer: '{tx.payer}' | Desc: {tx.description[:50]}")

# Top 10 credits
print(f"\n=== Top 10 Credits ===")
top_credits = sorted(credits, key=lambda x: x.amount, reverse=True)[:10]
for i, tx in enumerate(top_credits, 1):
    payer_str = (tx.payer or '(none)')[:30]
    print(f"{i:2d}. {tx.date} | {tx.amount:>12,.2f} | Payer: {payer_str:30s} | {tx.description[:40]}")

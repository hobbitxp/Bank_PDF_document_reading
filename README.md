# Bank Statement Analyzer

ระบบวิเคราะห์ Bank Statement ด้วย Claude AI + PDPA Compliance

## Features

- 📄 อ่าน PDF → JSON (รองรับภาษาไทย)
- 🔒 Mask ข้อมูลตาม PDPA
- 🤖 วิเคราะห์ด้วย Claude AI
- 💰 ตรวจจับเงินเดือนอัตโนมัติ (Thai tax model)

## Installation

```bash
pip install -r requirements-minimal.txt
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

## Usage

```bash
# One command - ทำทุกอย่างอัตโนมัติ
python src/process_statement.py "statement.pdf"
```

**Output:** 
- `data/json/*_masked.json` - ข้อมูลที่ปลอดภัย
- `*_salary_detection.xlsx` - วิเคราะห์เงินเดือน (3 sheets)
- `*_scored.csv` - รายการทั้งหมดพร้อมคะแนน
- `*_summary.json` - สรุปผล

## Manual Steps

```bash
# แยก step ทำเอง
python src/simple_pdf_to_json.py "statement.pdf"
python src/mask_data.py "data/json/statement_extracted.json"
python src/analyze_salary.py "data/json/statement_masked.json"
python src/ask_claude.py "data/json/statement_masked.json" "คำถาม"
```

## Project Structure

```
Bank_PDF_document_reading/
├── src/
│   ├── process_statement.py    # Main entry point
│   ├── simple_pdf_to_json.py   # PDF extraction
│   ├── mask_data.py             # PDPA masking
│   ├── analyze_salary.py        # Salary detection
│   └── ask_claude.py            # Claude AI
├── data/
│   ├── raw/                     # Original PDFs
│   └── json/                    # Output files
├── requirements-minimal.txt
└── README.md
```

## Security

⚠️ **สำคัญ:**
- เก็บ `*_mapping.json` ไว้ในเครื่องเท่านั้น
- แชร์ได้เฉพาะ `*_masked.json`
- ห้าม commit API keys

## Cost

~$0.40 per statement (~20k tokens)

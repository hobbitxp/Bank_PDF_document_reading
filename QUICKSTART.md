# Quick Start Guide

## Prerequisites

- Python 3.10 or higher
- Ollama (for AI features)

## Installation

### 1. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Ollama

**Linux/Mac:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

### 3. Download AI Model

```bash
# Recommended: LLaMA 3.2 (3B - fast and good)
ollama pull llama3.2

# Alternative: Qwen 2.5 (better for Thai)
ollama pull qwen2.5:3b
```

### 4. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env if needed (optional)
nano .env
```

## Usage

### Check System Status

```bash
python main.py info
```

This will show:
- Supported banks
- Ollama status
- Available AI models

### Parse a Bank Statement

```bash
# Parse a single PDF
python main.py parse --bank scb --input data/raw/statement.pdf

# Output will be saved to data/json/
```

**Supported banks:**
- `scb` - ธนาคารไทยพาณิชย์
- `tmb` - ธนาคารทหารไทยธนชาต
- `bbl` - ธนาคารกรุงเทพ
- `kbank` - ธนาคารกสิกรไทย
- `ktb` - ธนาคารกรุงไทย

### Analyze with AI

**Quick Summary:**
```bash
python main.py analyze --input data/json/statement_scb.json --template summary
```

**Interactive Mode:**
```bash
python main.py analyze --input data/json/statement_scb.json --interactive
```

In interactive mode, you can ask questions like:
- รายจ่ายทั้งหมดเท่าไหร่
- ร้านไหนจ่ายบ่อยสุด
- แนะนำการลดค่าใช้จ่าย
- สุขภาพการเงินเป็นยังไง

**Available Templates:**
- `summary` - สรุปภาพรวม
- `spending_analysis` - วิเคราะห์รายจ่าย
- `savings_advice` - คำแนะนำการออม
- `anomaly_detection` - ตรวจหารายการผิดปกติ
- `budget_recommendation` - แนะนำงบประมาณ
- `category_breakdown` - แยกตามหมวด
- `merchant_analysis` - วิเคราะห์ร้านค้า
- `financial_health` - ประเมินสุขภาพการเงิน

### Batch Processing

Process multiple PDFs at once:

```bash
python main.py batch --bank scb --input-dir data/raw/ --output-dir data/json/
```

## Example Workflow

```bash
# 1. Start Ollama (if not running)
ollama serve &

# 2. Parse your statement
python main.py parse --bank scb --input my_statement.pdf

# 3. Get a quick summary
python main.py analyze --input data/json/my_statement_scb.json --template summary

# 4. Ask specific questions
python main.py analyze --input data/json/my_statement_scb.json --interactive
```

## Common Issues

### "Cannot connect to Ollama"

**Solution:**
```bash
# Check if Ollama is running
ollama list

# If not, start it
ollama serve
```

### "No module named 'pdfplumber'"

**Solution:**
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Invalid PDF format"

**Solution:**
- Make sure the PDF is text-based (not scanned image)
- Try opening the PDF in a viewer to verify it's not corrupted
- Check that it's actually a bank statement PDF

### Parser returns empty transactions

**Solution:**
- The PDF format might be different from expected
- Check `data/json/` output to see what was extracted
- You may need to adjust the parser for your specific PDF format

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov
```

## Getting Help

```bash
# CLI help
python main.py --help

# Command-specific help
python main.py parse --help
python main.py analyze --help
```

## Next Steps

1. **Test with Your PDFs:** Try parsing your actual bank statements
2. **Refine Parsers:** Adjust parsers based on your PDF formats
3. **Explore AI Features:** Try different analysis templates
4. **Customize Categories:** Edit `config.py` to customize auto-categorization

## Tips

1. **Start with one bank:** Get one parser working well before trying others
2. **Use interactive mode:** Great for exploring your financial data
3. **Save AI responses:** Redirect output to file for later reference
4. **Batch process:** Process multiple months at once for trends

## Resources

- **Ollama Docs:** https://ollama.com/docs
- **pdfplumber Docs:** https://github.com/jsvine/pdfplumber
- **Implementation Details:** See `IMPLEMENTATION.md`

## Quick Reference

```bash
# Parse
python main.py parse -b <bank> -i <pdf>

# Analyze with template
python main.py analyze -i <json> -t <template>

# Interactive
python main.py analyze -i <json> -I

# Batch
python main.py batch -b <bank> -i <dir>

# Info
python main.py info
```

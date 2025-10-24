# Implementation Notes

## Overview

This document describes the implementation of the Bank Statement Analyzer MVP (Phase 1).

## Architecture

The project follows a modular architecture with clear separation of concerns:

```
bank-statement-analyzer/
├── parsers/        # Bank-specific PDF parsers
├── utils/          # Utility functions (PDF, dates, cleaning, validation)
├── ai/             # AI integration (Ollama client, analyzer, prompts)
├── tests/          # Unit tests
├── data/           # Data storage (raw PDFs, JSON, validated)
├── config.py       # Configuration
└── main.py         # CLI interface
```

## Components

### 1. PDF Extraction (`utils/pdf_extractor.py`)

**Purpose:** Extract text and tables from PDF files using pdfplumber.

**Key Features:**
- Extract text from all or specific pages
- Extract tables with customizable settings
- Search functionality
- PDF validation

**Usage:**
```python
from utils import PDFExtractor

extractor = PDFExtractor("statement.pdf")
data = extractor.extract_text_and_tables()
```

### 2. Date Parsing (`utils/date_parser.py`)

**Purpose:** Handle Thai dates with Buddhist calendar conversion.

**Key Features:**
- Buddhist to Gregorian year conversion
- Support for multiple date formats (DD/MM/YYYY, Thai month names)
- Flexible date parsing with fallback

**Challenges Solved:**
- Thai banks use Buddhist calendar (พ.ศ.) which is 543 years ahead of Gregorian
- Multiple date formats across different banks
- Thai month names (full and abbreviated)

**Usage:**
```python
from utils import ThaiDateParser

date = ThaiDateParser.parse_thai_date('15 มกราคม 2567')
# Returns: datetime(2024, 1, 15)
```

### 3. Data Cleaning (`utils/data_cleaner.py`)

**Purpose:** Clean and normalize extracted data.

**Key Features:**
- Text normalization
- Amount parsing (handles commas, currency symbols)
- Auto-categorization based on description
- Transaction type detection (debit/credit)
- Channel detection (mobile, ATM, online, etc.)
- Merchant information extraction
- Duplicate removal

**Auto-Categorization:**
Uses keyword matching to categorize transactions:
- Food: ร้านอาหาร, cafe, starbucks
- Shopping: 7-eleven, shopee, lazada
- Transport: BTS, grab, fuel
- Utilities: ไฟฟ้า, internet, AIS
- And more...

### 4. Data Validation (`utils/validator.py`)

**Purpose:** Validate parsed data for correctness and completeness.

**Key Features:**
- Required field checking
- Data type validation
- Range validation (amounts, dates)
- Balance verification
- Comprehensive error and warning reporting

**Validation Levels:**
- Transaction-level validation
- Balance validation
- Metadata validation
- Full statement validation

### 5. Base Parser (`parsers/base_parser.py`)

**Purpose:** Abstract base class for all bank parsers.

**Key Methods:**
- `parse_pdf()` - Main parsing method
- `extract_metadata()` - Extract account info, period
- `extract_balance()` - Extract opening/closing balance
- `parse_transactions()` - Parse transaction tables
- `generate_summary()` - Generate statistics

**Helper Methods:**
- `clean_amount()` - Clean amount strings
- `extract_account_number()` - Regex-based extraction
- `standardize_output()` - Consistent JSON format

### 6. Bank-Specific Parsers

**Implemented Parsers:**
- SCB (ธนาคารไทยพาณิชย์)
- TMB (ธนาคารทหารไทยธนชาต)
- BBL (ธนาคารกรุงเทพ)
- KBANK (ธนาคารกสิกรไทย)
- KTB (ธนาคารกรุงไทย)

**Design Pattern:**
Each parser inherits from `BaseParser` and implements:
- Custom regex patterns for account numbers, dates
- Bank-specific table layouts
- Custom transaction parsing logic

**Note:** Parsers are implemented with flexible patterns to handle variations. They should be tested with actual PDFs and refined as needed.

### 7. Ollama Client (`ai/ollama_client.py`)

**Purpose:** Interface with Ollama local AI.

**Key Features:**
- Text generation with custom prompts
- Chat interface with message history
- Model availability checking
- Statement analysis with context

**Configuration:**
- Host: Default `http://localhost:11434`
- Model: Default `llama3.2` (configurable)
- Temperature: Default 0.7
- Max tokens: Default 2048

**Usage:**
```python
from ai import OllamaClient

client = OllamaClient()
response = client.generate("Your prompt here")
```

### 8. AI Prompts (`ai/prompts.py`)

**Purpose:** Template system for AI queries.

**Features:**
- Predefined system prompts (advisor, analyzer, planner)
- Query templates for common analyses
- Statement context formatting
- Example queries

**Available Templates:**
- Summary - Overall financial summary
- Spending Analysis - Analyze spending patterns
- Savings Advice - Get savings recommendations
- Anomaly Detection - Find unusual transactions
- Budget Recommendation - Get budget suggestions
- Category Breakdown - Detailed category analysis
- Merchant Analysis - Analyze merchants/vendors
- Financial Health - Calculate health score

### 9. Financial Analyzer (`ai/analyzer.py`)

**Purpose:** High-level AI analysis interface.

**Key Methods:**
- `analyze()` - General analysis with custom query
- `quick_summary()` - Quick financial summary
- `spending_analysis()` - Spending pattern analysis
- `savings_advice()` - Savings recommendations
- `detect_anomalies()` - Find unusual transactions
- `budget_recommendation()` - Budget planning
- `financial_health_score()` - Health scoring
- `interactive_query()` - Interactive Q&A mode

### 10. CLI Interface (`main.py`)

**Purpose:** Command-line interface using Click and Rich.

**Commands:**
- `parse` - Parse a PDF statement
- `analyze` - Analyze with AI
- `batch` - Batch process multiple PDFs
- `info` - Show system information

**Examples:**
```bash
# Parse a statement
python main.py parse --bank scb --input statement.pdf

# Analyze with template
python main.py analyze --input output.json --template summary

# Interactive mode
python main.py analyze --input output.json --interactive

# Batch processing
python main.py batch --bank scb --input-dir ./pdfs/
```

## JSON Output Format

All parsers generate standardized JSON with this structure:

```json
{
  "metadata": {
    "bank": "SCB",
    "account_number": "xxx-x-xxxxx-x",
    "account_type": "savings",
    "currency": "THB",
    "statement_period": {
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    },
    "generated_at": "2025-01-15T10:30:00Z"
  },
  "balance": {
    "opening": 50000.00,
    "closing": 45000.00,
    "average": 47500.00
  },
  "transactions": [...],
  "summary": {
    "total_transactions": 161,
    "total_debit": 29386.08,
    "total_credit": 25565.77,
    "net_change": -3820.31,
    "by_type": {...},
    "by_channel": {...},
    "by_category": {...}
  },
  "validation": {
    "status": "valid",
    "errors": [],
    "warnings": []
  }
}
```

## Testing

Basic unit tests are provided in the `tests/` directory:

- `test_parsers.py` - Parser tests
- `test_utils.py` - Utility function tests
- `test_ai.py` - AI component tests

**Run tests:**
```bash
pytest tests/ -v
pytest tests/ --cov  # With coverage
```

## Configuration

Configuration is managed through:
1. `.env` file (copy from `.env.example`)
2. `config.py` constants

**Key Settings:**
- `OLLAMA_HOST` - Ollama API endpoint
- `OLLAMA_MODEL` - AI model to use
- `AI_TEMPERATURE` - Sampling temperature
- `SUPPORTED_BANKS` - Bank code mapping
- `CATEGORY_KEYWORDS` - Auto-categorization rules

## Known Limitations

1. **PDF Format Variations:** Each bank may have multiple statement formats. Parsers need testing with actual PDFs and refinement.

2. **OCR Not Supported:** Currently only works with text-based PDFs. Scanned images require OCR preprocessing.

3. **Single Statement:** Multi-month analysis not yet implemented.

4. **Thai Language Only:** AI prompts are primarily in Thai. English support can be added.

5. **Ollama Required:** AI features require Ollama to be running locally.

## Future Enhancements

**Phase 2: Core Features**
- [ ] Enhanced error handling
- [ ] More robust table detection
- [ ] Support for credit card statements
- [ ] CSV/Excel export

**Phase 3: AI Enhancement**
- [ ] Multi-statement comparison
- [ ] Predictive budgeting
- [ ] Anomaly detection with ML
- [ ] Custom categorization rules

**Phase 4: UI/UX**
- [ ] Web interface (Streamlit)
- [ ] Visualization dashboard
- [ ] PDF report generation
- [ ] Mobile app

## Performance

**Benchmarks (estimated):**
- PDF Parsing: ~3-5 seconds per 10-page statement
- Data Cleaning: ~1 second
- Validation: ~0.5 seconds
- AI Analysis: ~5-10 seconds (depends on model)

**Optimization Tips:**
- Use smaller AI models (3B-8B parameters)
- Batch process multiple PDFs
- Cache common AI queries
- Use GPU acceleration for AI if available

## Development Setup

```bash
# Clone repository
git clone <repo-url>
cd Bank_PDF_document_reading

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull AI model
ollama pull llama3.2

# Copy environment file
cp .env.example .env

# Run tests
pytest tests/

# Try the CLI
python main.py info
```

## Contributing

When adding new features:

1. Follow existing code structure
2. Add type hints
3. Write docstrings
4. Add unit tests
5. Update documentation

## Support

For issues or questions:
- Check existing issues on GitHub
- Review documentation
- Test with sample PDFs first

## License

MIT License - See LICENSE file for details.

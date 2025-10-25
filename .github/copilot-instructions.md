# Bank Statement Analyzer - AI Agent Instructions

## Documentation Standards

**NO ICONS/EMOJIS POLICY:**
- NEVER use emoji icons in any documentation (README.md, comments, commit messages)
- Use plain text headings only: `## Features` not `## 🌟 Features`
- Use plain bullet points: `- **PDF Extraction**` not `- 📄 **PDF Extraction**`
- Use plain text warnings: `WARNING:` or `SECRET:` not `⚠️` or `🔒`
- Rationale: Professional documentation, better accessibility, universal compatibility

**Markdown Guidelines:**
- Use `**bold**` and `*italic*` for emphasis
- Use `>` for blockquotes when needed
- Use code blocks with language tags: ```python, ```bash, ```json
- Use tables for structured data when appropriate

## Architecture Overview

**Hexagonal Architecture (Ports & Adapters) - Completed**
- **Domain Layer**: Core business logic (entities, value objects) - framework-independent
- **Application Layer**: Use cases and ports (interfaces)
- **Infrastructure Layer**: Adapters (PyMuPDF, S3, Thai tax analyzer)
- **API Layer**: FastAPI endpoints with dependency injection

**Project Structure:**
```
src/
├── domain/                     # Pure business logic
│   └── entities/              # Transaction, Statement, SalaryAnalysis
├── application/               # Use cases & interfaces
│   ├── ports/                 # IPDFExtractor, IDataMasker, ISalaryAnalyzer, IStorage
│   └── use_cases/            # AnalyzeStatementUseCase
├── infrastructure/            # External system adapters
│   ├── pdf/                  # PyMuPDFExtractor
│   ├── masking/              # RegexDataMasker (PDPA)
│   ├── analysis/             # ThaiSalaryAnalyzer
│   └── storage/              # S3Storage, LocalStorage
├── api/v1/                   # FastAPI endpoints
│   ├── routes/               # health.py, analyze.py
│   ├── schemas.py            # Pydantic models
│   └── dependencies.py       # DI container
├── config.py                 # Settings
└── main.py                   # FastAPI app entry point
```

**Data Flow:**
```
Mobile App → POST /api/v1/analyze-upload
  → PDFExtractor (PyMuPDF) → Statement entity
  → DataMasker (Regex) → Masked Statement + Mapping
  → SalaryAnalyzer (Thai Tax) → SalaryAnalysis entity
  → Storage (S3/Local) → Pre-signed URLs or file:// paths
  → Response JSON
```

## Critical Patterns

### Hexagonal Architecture Principles

**Dependency Rule:** Dependencies point inward only
- Domain knows nothing about application/infrastructure
- Application defines ports (interfaces), infrastructure implements adapters
- API depends on application layer, not infrastructure directly

**Example:**
```python
# ✅ CORRECT: Application uses port interface
class AnalyzeStatementUseCase:
    def __init__(self, pdf_extractor: IPDFExtractor):
        self.extractor = pdf_extractor

# ❌ WRONG: Application depends on concrete implementation
class AnalyzeStatementUseCase:
    def __init__(self):
        self.extractor = PyMuPDFExtractor()  # Tight coupling!
```

**Dependency Injection:** Use DI container in `api/v1/dependencies.py`
```python
def get_pdf_extractor() -> IPDFExtractor:
    return PyMuPDFExtractor()

@router.post("/analyze")
async def analyze(extractor: IPDFExtractor = Depends(get_pdf_extractor)):
    ...
```

### Domain Entity Design

**Transaction Entity:**
- Immutable value object pattern (dataclass with frozen=False for scoring)
- Business logic methods: `is_excluded()`, `has_keyword()`, `is_early_morning()`
- No framework dependencies (no FastAPI, boto3, pandas imports)

**Statement Entity:**
- Aggregate root containing transactions
- Factory methods: `get_credit_transactions()`, `get_debit_transactions()`
- Rich domain model (not anemic)

### Thai Banking Context
- **Language:** All comments/strings support Thai characters (UTF-8 encoded)
- **Number Format:** Thai uses commas: `84,456.01` parsed via `r"(\d{1,3}(?:,\d{3})*\.\d{2})"`
- **Name Patterns:** `นาย/นาง/นางสาว` + Thai name (masked as `NAME_001`)
- **Account Format:** `xxx-x-xxxxx-x` (masked as `ACCOUNT_001`)

### PDPA Compliance (mask_data.py)
**6 Pattern Types:** Thai ID (13 digits), account numbers, Thai names, phone (0xx-xxx-xxxx), addresses, emails
- **Output:** 2 files - `*_masked.json` (shareable) + `*_mapping.json` (SECRET, local only)
- **Rule:** NEVER send `*_mapping.json` to APIs or commit to git

### Salary Detection Algorithm (analyze_salary.py)
**Multi-Factor Scoring System:**
- Keyword match (`เงินเดือน`, `BSD02`, `Payroll`): +5 points
- Employer payer match: +3 points  
- Time heuristic (01:00-06:00 AM payroll window): +2 points
- Amount clustering (±3% threshold): +3 points
- Not excluded (e-wallet, cash, check): +2 points

**Thai Tax Model:**
- Progressive brackets: 0% (0-150k), 5% (150-300k), 10% (300-500k), 15% (500-750k), 20% (750k-1M), 25% (1M-2M), 30% (2M-5M), 35% (>5M)
- SSO: 5% capped at 750 THB/month
- Deductions: 60k personal allowance + 100k employment expense cap
- Function: `thai_monthly_net_from_gross(gross, pvd_rate, extra_deductions_yearly)`

### Excel Output Structure
3 sheets in `*_salary_detection.xlsx`:
1. **Summary:** Gross estimate, net salary, tax, SSO, top candidates
2. **Top Candidates:** High-scoring transactions (score ≥ median)
3. **All Scored:** Every credit transaction with scoring breakdown

## Development Workflow

### Running the API (Production)

```bash
# Development
cd src
python main.py

# Production with uvicorn
cd src
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4

# With gunicorn (production)
cd src
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

**API Endpoints:**
- `GET /api/v1/health` - Health check (returns version 3.0.0-hexagonal)
- `POST /api/v1/analyze-upload` - Upload PDF and analyze
- `POST /api/v1/analyze-s3` - Analyze from S3 key
- `GET /docs` - Swagger UI

**Testing:**
```bash
# Health
curl http://localhost:8001/api/v1/health

# Analyze
curl -X POST "http://localhost:8001/api/v1/analyze-upload" \
  -F "pdf_file=@statement.pdf" \
  -F "user_id=test_user" \
  -F "pdf_password=1234" \
  -F "expected_gross=65000" \
  -F "employer=ACME" \
  -F "pvd_rate=0.03"
```

### Testing Strategy

**Unit Tests (Domain Layer):**
```bash
pytest tests/unit/domain/  # No I/O, pure logic
```

**Integration Tests (Infrastructure):**
```bash
pytest tests/integration/infrastructure/  # Test adapters
```

**E2E Tests (API):**
```bash
pytest tests/e2e/api/  # Full workflow
```

### Adding New Adapter

1. Define port in `application/ports/`
2. Implement adapter in `infrastructure/`
3. Register in DI container `api/v1/dependencies.py`
4. Inject via FastAPI `Depends()`

Example:
```python
# 1. Port
class IEmailNotifier(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str): pass

# 2. Adapter
class SendGridNotifier(IEmailNotifier):
    def send(self, to: str, subject: str, body: str):
        # SendGrid implementation

# 3. DI Container
def get_email_notifier() -> IEmailNotifier:
    return SendGridNotifier(api_key=settings.SENDGRID_KEY)

# 4. Inject
@router.post("/analyze")
async def analyze(notifier: IEmailNotifier = Depends(get_email_notifier)):
    ...
```

### Common Issues
- Place test PDFs in `Test/` directory
- Run with real bank statements from: KTB, SCB, BBL, KBANK, TMB
- Verify outputs: check `data/json/` for all 4 file types (extracted, masked, mapping, analysis)

### Common Issues

**Circular Import:**
- Domain should never import from application/infrastructure
- Use dependency injection instead of direct imports

**Port not found:**
- Ensure port is defined in `application/ports/`
- Check DI container registration

**S3 Connection Failed:**
- Verify AWS credentials in environment variables
- Check bucket permissions and region

## Project Structure Rules

- **All Python in src/:** Never place `.py` files in root
- **Single README:** Only 1 markdown file allowed (README.md)
- **Clean structure:** Removed legacy folders: `ai/`, `parsers/`, `tests/`, `utils/` and legacy scripts
- **Dependencies:** Use `requirements.txt` (10 packages: PyMuPDF, anthropic, pandas, openpyxl, fastapi, uvicorn, python-multipart, boto3)
- **Pure Hexagonal:** 31 Python files across 4 layers (Domain, Application, Infrastructure, API)

## Integration Points

### Claude AI (Optional)
- `src/ask_claude.py` - Question answering on masked statements
- Requires: `ANTHROPIC_API_KEY` environment variable
- Cost: ~$0.40 per statement (~20k tokens)
- Input: Always use `*_masked.json`, never raw extracted JSON

### PDF Processing
- Library: PyMuPDF (fitz) - handles Thai text correctly
- Password support: `doc.authenticate(password)` before extraction
- Output: JSON with `pages[]` array, each containing `page_number`, `text`, `lines[]`

## Code Conventions

- **Dataclass for transactions:** `@dataclass Tx` with `page`, `amount`, `desc_raw`, `is_credit`, `score`, `cluster_id`
- **Type hints:** Use Python 3.10+ syntax - `tuple[str, Dict]`, not `Tuple[str, Dict]`
- **Error handling:** Print error messages in Thai when user-facing
- **CLI:** Use argparse with Thai help text: `parser.add_argument("--password", help="รหัสผ่าน PDF")`

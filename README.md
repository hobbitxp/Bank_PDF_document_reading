# Bank Statement Analyzer API

ระบบวิเคราะห์ Bank Statement สำหรับ Mobile App  
**Hexagonal Architecture | PDPA Compliance | Thai Tax Calculation**

[![Version](https://img.shields.io/badge/version-3.0.0--hexagonal-blue.svg)](https://github.com/hobbitxp/Bank_PDF_document_reading)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal.svg)](https://fastapi.tiangolo.com/)

## Features

- **PDF Extraction** - PyMuPDF รองรับภาษาไทย, encrypted PDFs
- **PDPA Compliance** - Regex masking 6 patterns (Thai ID, accounts, names, phones, emails, addresses)
- **Salary Detection** - Multi-factor scoring + Thai progressive tax calculation + clustering
- **Storage** - S3 with pre-signed URLs (fallback to local storage)
- **FastAPI API** - RESTful endpoints for mobile apps
- **Hexagonal Architecture** - Ports & Adapters pattern for maintainability

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       API Layer (FastAPI)                     │
│  /api/v1/health  |  /api/v1/analyze-upload  |  /api/v1/analyze-s3  │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              Application Layer (Use Cases)                    │
│        AnalyzeStatementUseCase (Orchestrator)                │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│          Application Ports (Interfaces)                       │
│  IPDFExtractor | IDataMasker | ISalaryAnalyzer | IStorage   │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│         Infrastructure Layer (Adapters)                       │
│  PyMuPDFExtractor | RegexMasker | ThaiAnalyzer | S3Storage  │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                   Domain Layer (Entities)                     │
│        Transaction | Statement | SalaryAnalysis              │
└──────────────────────────────────────────────────────────────┘
```

**Dependency Rule:** Dependencies point inward only  
**Principle:** Infrastructure depends on Application, Application defines Ports, Domain knows nothing

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/hobbitxp/Bank_PDF_document_reading.git
cd Bank_PDF_document_reading

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration (Optional)

```bash
# For S3 storage (optional - will use local storage if not configured)
cp .env.example .env
nano .env
```

**Environment Variables:**
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=bank-statements
S3_PRESIGNED_URL_EXPIRATION=3600
LOCAL_STORAGE_PATH=data/storage
```

### 3. Start API Server

```bash
# Start Hexagonal API (Port 8001)
cd src
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Test API

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Analyze statement
curl -X POST "http://localhost:8001/api/v1/analyze-upload" \
  -F "pdf_file=@statement.pdf" \
  -F "user_id=user001" \
  -F "pdf_password=1234" \
  -F "expected_gross=50000" \
  -F "employer=ACME Corp" \
  -F "pvd_rate=0.03"
```

### 5. API Documentation

Open browser: `http://localhost:8001/docs`

## API Endpoints

### Health Check
```bash
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "bank-statement-analyzer",
  "version": "3.0.0-hexagonal",
  "architecture": "hexagonal",
  "storage_type": "local"  // or "s3"
}
```

### Analyze Statement (Upload)
```bash
POST /api/v1/analyze-upload
```

**Parameters:**
- `pdf_file` (file, required) - Bank statement PDF
- `user_id` (string, required) - User identifier
- `pdf_password` (string, optional) - PDF password if encrypted
- `expected_gross` (float, optional) - Expected gross salary for validation
- `employer` (string, optional) - Employer name for matching
- `pvd_rate` (float, optional) - Provident fund rate (0.0-0.15, default: 0.0)
- `extra_deductions` (float, optional) - Extra annual deductions in THB
- `upload_to_storage` (boolean, optional) - Upload to S3/local (default: true)

**Response:**
```json
{
  "success": true,
  "statement_id": "20251025_180653_tmpgbv0xlms",
  "user_id": "test_user",
  "timestamp": "20251025_180653",
  "statistics": {
    "total_transactions": 1278,
    "credit_transactions": 72,
    "debit_transactions": 1206,
    "masked_items": 33,
    "pages_processed": 17
  },
  "analysis": {
    "detected_amount": 65000.0,
    "confidence": "medium",
    "transactions_analyzed": 72,
    "clusters_found": 3,
    "top_candidates_count": 10,
    "matches_expected": true,
    "difference": 0.0,
    "difference_percentage": 0.0
  },
  "storage_urls": {
    "masked": "file:///.../masked.json",
    "mapping": "file:///.../mapping.json",
    "analysis": "file:///.../analysis.json"
  },
  "local_files": {
    "masked": "data/json/xxx_masked.json",
    "mapping": "data/json/xxx_mapping.json",
    "analysis": "data/json/xxx_analysis.json"
  }
}
```

### Analyze Statement (S3)
```bash
POST /api/v1/analyze-s3
```

Same parameters as `/analyze-upload` but use `s3_key` instead of `pdf_file`

## Project Structure

```
Bank_PDF_document_reading/
├── src/
│   ├── domain/                    # Domain Layer (Pure Business Logic)
│   │   └── entities/
│   │       ├── transaction.py     # Transaction entity
│   │       ├── statement.py       # Statement aggregate
│   │       └── salary_analysis.py # Analysis result
│   │
│   ├── application/               # Application Layer (Use Cases + Ports)
│   │   ├── ports/                 # Interface definitions
│   │   │   ├── pdf_extractor.py
│   │   │   ├── data_masker.py
│   │   │   ├── salary_analyzer.py
│   │   │   └── storage.py
│   │   └── use_cases/
│   │       └── analyze_statement.py
│   │
│   ├── infrastructure/            # Infrastructure Layer (Adapters)
│   │   ├── pdf/
│   │   │   └── pymupdf_extractor.py
│   │   ├── masking/
│   │   │   └── regex_masker.py
│   │   ├── analysis/
│   │   │   └── thai_analyzer.py
│   │   └── storage/
│   │       └── s3_storage.py      # S3Storage + LocalStorage
│   │
│   ├── api/                       # API Layer
│   │   └── v1/
│   │       ├── routes/
│   │       │   ├── health.py
│   │       │   └── analyze.py
│   │       ├── schemas.py         # Pydantic models
│   │       └── dependencies.py    # DI container
│   │
│   ├── config.py                  # Settings
│   └── main.py                    # FastAPI app entry point
│
├── data/
│   ├── json/                     # Working files
│   ├── storage/                  # Local storage
│   └── raw/                      # Input PDFs
│
├── Test/                         # Test PDFs
├── requirements.txt              # Dependencies
├── .env.example                  # Environment template
└── README.md
```

**Total Files:** 31 Python files across 4 layers (Domain, Application, Infrastructure, API)

**Response:**
```json
{
  "success": true,
  "request_id": "req_xxx_user123",
  "analysis": {
    "salary_detected": 84456.01,
    "confidence": "high",
    "transactions_analyzed": 262,
    "best_candidates": [...],
    "validation": {
      "matches_expected": true,
      "difference": -543.99
    }
  },
  "s3_urls": {
    "original_pdf": "https://...",
    "masked_json_url": "https://...",
    "excel_url": "https://..."
  },
  "metadata": {
    "processing_time_ms": 364
  }
}
```

## Project Structure

```bash
## CLI Usage (Legacy Scripts)

สำหรับการใช้งานแบบ command-line (backwards compatibility):

```bash
# One command - ทำทุกอย่างอัตโนมัติ
python src/process_statement.py "statement.pdf" --password "1234"

# Manual steps
python src/simple_pdf_to_json.py "statement.pdf"
python src/mask_data.py "data/json/statement_extracted.json"
python src/analyze_salary.py "data/json/statement_masked.json" --gross 85000
python src/ask_claude.py "data/json/statement_masked.json" "คำถาม"
```

**Output Files:**
- `*_extracted.json` - Raw data from PDF
- `*_masked.json` - PDPA-compliant (shareable)
- `*_mapping.json` - Decryption key (SECRET - never share!)
- `*_salary_detection.xlsx` - Analysis report (3 sheets)
- `*_scored.csv` - All transactions with scores
- `*_summary.json` - Summary statistics

## API Endpoints

### POST /api/v1/analyze-upload
Upload PDF and analyze salary

**Request:**
- `file`: PDF file (multipart/form-data)
- `expected_salary`: Expected gross salary (optional)
- `password`: PDF password (optional)
- `employer`: Employer name (optional)
- `user_id`: User identifier (required)
- Header: `X-API-Key: your-api-key`

**Response:** Analysis result + S3 URLs

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "service": "bank-statement-analyzer",
  "s3_status": "connected",
  "version": "2.1.0"
}
```

## Configuration

### Environment Variables (.env)

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-southeast-1

# S3 Buckets
S3_BUCKET_INPUT=bank-statements-input
S3_BUCKET_OUTPUT=bank-statements-output

# API
API_KEY=your-secret-api-key
MAX_FILE_SIZE_MB=50

# Optional
ANTHROPIC_API_KEY=sk-ant-...
```

## Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY src/ ./src/
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bank-analyzer
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: bank-analyzer:latest
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: api-key
```

### Production Checklist

- [ ] Set strong `API_KEY` in environment
- [ ] Configure AWS IAM with least-privilege S3 permissions
- [ ] Enable HTTPS (TLS/SSL)
- [ ] Setup rate limiting (10 requests/minute per user)
- [ ] Configure logging and monitoring
- [ ] Setup S3 bucket lifecycle policies (auto-delete after 30 days)
- [ ] Enable S3 encryption at rest
- [ ] Configure CORS for mobile app domain
- [ ] Setup health check monitoring
- [ ] Configure auto-scaling (HPA in Kubernetes)

## Security

### PDPA Compliance

**Data Masking:** 6 pattern types
- Thai ID (13 digits) → `THAIID_001`
- Account numbers → `ACCOUNT_001`
- Thai names → `NAME_001`
- Phone numbers → `PHONE_001`
- Addresses → `ADDRESS_001`
- Emails → `EMAIL_001`

**File Security:**
- `*_masked.json` - Safe to share/store
- `*_mapping.json` - SECRET - store securely, never commit to git
- Original PDFs - Auto-delete after processing (temp directory)

### API Security

- **Authentication**: API Key via `X-API-Key` header
- **Authorization**: User-based access control
- **File Validation**: PDF only, max 50MB
- **Rate Limiting**: Recommended 10 req/min per user
- **S3 Pre-signed URLs**: 7-day expiry

## Performance

**Benchmarks (tested):**
- PDF Upload: ~100ms
- PDF Extraction (10 pages): ~200ms
- Data Masking: ~50ms
- Salary Analysis (262 transactions): ~100ms
- **Total Processing Time: ~364ms**

**Scalability:**
- 5k users/day: Single instance sufficient
- 50k+ users/day: Horizontal scaling (Kubernetes HPA)
- Async processing: Use Celery + Redis for queue

## Cost Estimate

**AWS S3:**
- Storage: $0.023/GB/month
- Upload: Free
- Download (pre-signed URLs): $0.09/GB
- Estimated: ~$5-10/month for 5k users

**Optional Claude AI:**
- ~$0.40 per statement analysis
- 5k requests = ~$2000/month

## Troubleshooting
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
│   ├── domain/                      # Core Business Logic
│   │   ├── entities/
│   │   │   ├── transaction.py      # Transaction entity
│   │   │   ├── statement.py        # Statement aggregate
│   │   │   └── salary_analysis.py  # Analysis result
│   │   └── value_objects/          # Money, Confidence, etc.
│   │
│   ├── application/                 # Use Cases & Interfaces
│   │   ├── ports/                  # Abstract interfaces
│   │   │   ├── pdf_extractor.py   # IPDFExtractor
│   │   │   ├── data_masker.py     # IDataMasker
│   │   │   ├── salary_analyzer.py # ISalaryAnalyzer
│   │   │   └── storage.py         # IStorage
│   │   └── use_cases/
│   │       └── analyze_statement.py # Main business flow
│   │
│   ├── infrastructure/              # External Adapters
│   │   ├── pdf/
│   │   │   └── pymupdf_extractor.py # PyMuPDF implementation
│   │   ├── masking/
│   │   │   └── regex_masker.py     # PDPA regex masker
│   │   ├── analysis/
│   │   │   └── thai_analyzer.py    # Thai tax calculator
│   │   └── storage/
│   │       ├── s3_storage.py       # AWS S3 adapter
│   │       └── local_storage.py    # Local filesystem
│   │
│   ├── api/                         # HTTP API Layer
│   │   └── v1/
│   │       ├── routes/
│   │       │   ├── health.py       # Health check
│   │       │   └── analyze.py      # Analysis endpoints
│   │       ├── schemas/
│   │       │   ├── requests.py     # Request models
│   │       │   └── responses.py    # Response models
│   │       └── dependencies.py     # DI container
│   │
│   ├── config/
│   │   └── settings.py             # Environment config
│   │
│   ├── main.py                     # FastAPI app entry
│   │
│   └── [legacy scripts]            # Backwards compatibility
│       ├── simple_pdf_to_json.py
│       ├── mask_data.py
│       ├── analyze_salary.py
│       ├── process_statement.py
│       └── api_mobile.py
│
├── tests/                          # Test Suite
│   ├── unit/                       # Domain & use case tests
│   ├── integration/                # Adapter tests
│   └── e2e/                        # API tests
│
├── data/
│   ├── json/                       # Output files
│   └── uploads/                    # Temp uploads
│
├── Test/                           # Sample PDFs
├── requirements-api.txt
├── .env.s3
└── README.md
```

## Development Guide

### Adding New Features

**1. Add Business Logic (Domain)**
```python
# src/domain/entities/transaction.py
def is_bonus_payment(self) -> bool:
    return "โบนัส" in self.description
```

**2. Define Interface (Port)**
```python
# src/application/ports/bonus_detector.py
class IBonusDetector(ABC):
    @abstractmethod
    def detect(self, transactions: list[Transaction]) -> list[Transaction]:
        pass
```

**3. Implement Adapter**
```python
# src/infrastructure/analysis/bonus_detector.py
class ThaiB onusDetector(IBonusDetector):
    def detect(self, transactions: list[Transaction]) -> list[Transaction]:
        return [t for t in transactions if t.is_bonus_payment()]
```

**4. Register in DI Container**
```python
# src/api/v1/dependencies.py
def get_bonus_detector() -> IBonusDetector:
    return ThaiBonusDetector()
```

**5. Use in Endpoint**
```python
@router.post("/detect-bonus")
async def detect_bonus(detector: IBonusDetector = Depends(get_bonus_detector)):
    ...
```

### Testing

```bash
# Unit tests (fast, no I/O)
pytest tests/unit/

# Integration tests (with real adapters)
pytest tests/integration/

# E2E tests (full API)
pytest tests/e2e/

# With coverage
pytest --cov=src tests/
```

## CLI Usage (Legacy Scripts)

## Security

## Troubleshooting

**PDF Password Error:**
```
Error: PDF มีการป้องกันด้วยรหัสผ่าน
Solution: Include password in request
```

**S3 Connection Failed:**
```
Error: s3_status: "disconnected"
Solution: Check AWS credentials in .env file
```

**Import Error:**
```
Error: ModuleNotFoundError: No module named 'boto3'
Solution: pip install -r requirements-api.txt
```

**Port Already in Use:**
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9
```

## Contributing

1. Follow Hexagonal Architecture principles
2. Add tests for new features (TDD)
3. Update both API and CLI (backwards compatibility)
4. Document changes in README and copilot-instructions.md

## License

MIT License

## Support

- Email: support@example.com
- Issues: GitHub Issues
- Docs: `/docs` endpoint (Swagger UI)

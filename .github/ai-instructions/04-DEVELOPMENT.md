# Development Guide

**Read this for: Running the API, testing, development commands**

## Running the API

### Development Mode

**Start FastAPI with auto-reload:**
```bash
cd src
python main.py
```

**Or with uvicorn directly:**
```bash
cd src
uvicorn main:app --host 0.0.0.0 --port 8001 --reload --log-level info
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
Database connected: {'status': 'connected'}
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Production Mode

**With uvicorn (single worker):**
```bash
cd src
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

**With gunicorn (multiple workers):**
```bash
cd src
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### Docker Mode

**Build and run:**
```bash
docker-compose up --build
```

**Run without build:**
```bash
docker-compose up
```

**Stop services:**
```bash
docker-compose down
```

## API Endpoints

### Health Check
```bash
# Health check
curl http://localhost:8001/api/v1/health

# Expected response
{
  "status": "healthy",
  "service": "bank-statement-analyzer",
  "version": "3.0.0-hexagonal",
  "architecture": "hexagonal",
  "storage_type": "s3",
  "database_status": "connected"
}
```

### Analyze PDF (Upload)
```bash
curl -X POST "http://localhost:8001/api/v1/analyze-upload" \
  -F "pdf_file=@statement.pdf" \
  -F "user_id=test_user_001" \
  -F "pdf_password=1234" \
  -F "expected_gross=65000" \
  -F "employer=ACME Corp" \
  -F "pvd_rate=0.03" \
  -F "extra_deductions=0" \
  -F "upload_to_storage=true"
```

### Analyze PDF (S3 Key)
```bash
curl -X POST "http://localhost:8001/api/v1/analyze-s3" \
  -H "Content-Type: application/json" \
  -d '{
    "s3_key": "uploads/user_001/statement.pdf",
    "user_id": "test_user_001",
    "pdf_password": "1234",
    "expected_gross": 65000,
    "employer": "ACME Corp",
    "pvd_rate": 0.03
  }'
```

### API Documentation
```bash
# Swagger UI (interactive)
open http://localhost:8001/docs

# ReDoc (alternative)
open http://localhost:8001/redoc
```

## Testing Strategy

**CRITICAL: Follow TDD (Test-Driven Development) for ALL features**

### TDD Workflow (MANDATORY)

**Red-Green-Refactor Cycle:**

```
┌─────────────────────────────────────────────┐
│ 1. RED: Write failing test                 │
│    - Based on requirements                  │
│    - Define expected behavior               │
│    - Run test → MUST FAIL                   │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 2. GREEN: Write minimal code               │
│    - Just enough to pass test               │
│    - Don't worry about perfection           │
│    - Run test → MUST PASS                   │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 3. REFACTOR: Improve code                  │
│    - Clean up implementation                │
│    - Apply design patterns                  │
│    - Run test → MUST STILL PASS             │
└─────────────────┬───────────────────────────┘
                  ↓
                REPEAT
```

### Test Types (Both Required)

**1. Unit Tests (Fast, No I/O, Use Mocks)**

**Purpose:** Test business logic in isolation
**Location:** `tests/test_*.py` (without `_integration` suffix)
**Speed:** <0.5s for entire suite
**Dependencies:** None (use mocks)

**When to write:**
- Domain entities and value objects
- Application use cases (mock all ports)
- Pure functions and algorithms
- Business rules and calculations

**Example structure:**
```python
# tests/test_salary_analyzer.py
import pytest
from unittest.mock import MagicMock
from application.services.salary_analyzer import SalaryAnalyzer

class TestSalaryAnalyzer:
    """Unit tests for SalaryAnalyzer (mocked dependencies)"""
    
    @pytest.fixture
    def mock_transactions(self):
        """Mock transaction data"""
        return [
            {"amount": 50000, "description": "เงินเดือน"},
            {"amount": 100, "description": "ค่าอาหาร"}
        ]
    
    def test_detect_salary_with_keyword(self, mock_transactions):
        """Test salary detection with keyword"""
        analyzer = SalaryAnalyzer()
        result = analyzer.detect(mock_transactions)
        
        assert result.amount == 50000.0
        assert result.confidence == "high"
    
    def test_detect_salary_no_keyword(self):
        """Test salary detection without keyword"""
        analyzer = SalaryAnalyzer()
        transactions = [
            {"amount": 45000, "description": "โอนเงิน", "time": "03:30"}
        ]
        result = analyzer.detect(transactions)
        
        assert result.amount == 45000.0
        assert result.confidence == "medium"
```

**Run unit tests:**
```bash
# All unit tests (excludes integration)
pytest tests/ -v -m "not integration"

# Specific test file
pytest tests/test_salary_analyzer.py -v

# With coverage
pytest tests/ -v -m "not integration" --cov=src --cov-report=term-missing
```

**2. Integration Tests (Slower, Real Dependencies)**

**Purpose:** Test adapters with real external services
**Location:** `tests/test_*_integration.py`
**Speed:** 1-10s depending on service
**Dependencies:** Docker services (PostgreSQL, S3/LocalStack)

**When to write:**
- Database adapters (PostgreSQL operations)
- Storage adapters (S3 upload/download)
- PDF extractors (real PDF files)
- External API integrations

**Marker:** `@pytest.mark.integration`

**Example structure:**
```python
# tests/test_database_integration.py
import pytest
import os
from uuid import UUID
from infrastructure.database.postgres_adapter import PostgresDatabase

pytestmark = pytest.mark.integration  # Mark all tests in file

@pytest.fixture
async def db_connection():
    """Real database connection fixture"""
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not set")
    
    db = PostgresDatabase(connection_string=db_url)
    await db.connect()
    
    yield db
    
    # Cleanup
    if db.pool:
        await db.pool.close()

@pytest.mark.asyncio
async def test_save_analysis_real(db_connection):
    """Test saving analysis to real PostgreSQL"""
    db = db_connection
    
    analysis_id = await db.save_analysis(
        user_id="test-integration",
        detected_salary=50000.0,
        confidence="high",
        # ... other parameters
    )
    
    assert isinstance(analysis_id, UUID)
    
    # Verify data was saved
    result = await db.get_analysis(str(analysis_id))
    assert result["user_id"] == "test-integration"
    
    # Cleanup
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM analyses WHERE id = $1", analysis_id)
```

**Run integration tests:**
```bash
# Start dependencies first
docker compose up -d db

# Set environment variable
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_bank_statements"

# Run integration tests only
pytest tests/ -v -m integration

# Run all tests (unit + integration)
pytest tests/ -v
```

### Test Coverage Requirements

**Minimum coverage by layer:**

| Layer           | Coverage | Test Type   | Why                              |
|-----------------|----------|-------------|----------------------------------|
| Domain          | 100%     | Unit        | Pure business logic, no I/O      |
| Application     | 90%      | Unit        | Use cases with mocked ports      |
| Infrastructure  | 70%      | Integration | Real adapters (DB, S3, PDF)      |
| API             | 80%      | E2E/Unit    | Endpoint logic + error handling  |

**Check coverage:**
```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Open HTML report
open htmlcov/index.html

# Coverage by layer
pytest tests/ --cov=src/domain --cov-report=term        # Domain: 100%
pytest tests/ --cov=src/application --cov-report=term   # Application: 90%
pytest tests/ --cov=src/infrastructure --cov-report=term # Infrastructure: 70%
```

### Test Structure
```
tests/
├── __init__.py
├── conftest.py                      # Shared fixtures
├── test_transaction.py              # Unit: Domain entity
├── test_salary_analyzer.py          # Unit: Domain service
├── test_analyze_use_case.py         # Unit: Use case (mocked)
├── test_database.py                 # Unit: Database adapter (mocked)
├── test_database_integration.py     # Integration: Real PostgreSQL
├── test_s3_integration.py           # Integration: Real S3/LocalStack
├── test_pdf_integration.py          # Integration: Real PDF files
└── test_api_e2e.py                  # E2E: Full workflow
```

### Unit Tests (Domain Layer)

**Run domain tests:**
```bash
pytest tests/test_transaction.py tests/test_salary_analyzer.py -v
```

**Example test:**
```python
# tests/test_transaction.py
import pytest
from domain.entities.transaction import Transaction

def test_is_excluded():
    """Test exclusion logic"""
    tx = Transaction(
        page=1,
        amount=100.0,
        description="ทรูมันนี่ โอนเงิน",
        is_credit=True
    )
    assert tx.is_excluded() == True

def test_has_keyword():
    """Test keyword matching"""
    tx = Transaction(
        page=1,
        amount=50000.0,
        description="เงินเดือน มกราคม",
        is_credit=True
    )
    assert tx.has_keyword(["เงินเดือน"]) == True

def test_is_early_morning():
    """Test payroll time window"""
    tx = Transaction(
        page=1,
        amount=50000.0,
        description="โอนเงิน",
        is_credit=True,
        time="03:45"
    )
    assert tx.is_early_morning() == True
```

### Integration Tests (Adapters)

**Run integration tests:**
```bash
pytest tests/test_*_integration.py -v -m integration
```

**Example test:**
```python
# tests/test_pdf_integration.py
import pytest
from infrastructure.pdf.pymupdf_extractor import PyMuPDFExtractor

pytestmark = pytest.mark.integration

def test_extract_pdf():
    """Test PDF extraction with real file"""
    extractor = PyMuPDFExtractor()
    result = extractor.extract("tests/fixtures/sample.pdf")
    
    assert result is not None
    assert "pages" in result
    assert len(result["pages"]) > 0
````

### Integration Tests (Adapters)

**Run integration tests:**
```bash
pytest tests/integration/infrastructure/ -v
```

**Example test:**
```python
# tests/integration/infrastructure/test_pymupdf_extractor.py
import pytest
from infrastructure.pdf.pymupdf_extractor import PyMuPDFExtractor

def test_extract_pdf():
    """Test PDF extraction with real file"""
    extractor = PyMuPDFExtractor()
    result = extractor.extract("tests/fixtures/sample.pdf")
    
    assert result is not None
    assert "pages" in result
    assert len(result["pages"]) > 0
    assert "text" in result["pages"][0]

def test_extract_encrypted_pdf():
    """Test encrypted PDF"""
    extractor = PyMuPDFExtractor()
    result = extractor.extract(
        "tests/fixtures/encrypted.pdf",
        password="1234"
    )
    
    assert result is not None
    assert len(result["pages"]) > 0
```

**S3 integration test:**
```python
# tests/integration/infrastructure/test_s3_storage.py
import pytest
from infrastructure.storage.s3_storage import S3Storage

@pytest.mark.asyncio
async def test_s3_upload():
    """Test S3 upload"""
    storage = S3Storage(
        bucket_name="test-bucket",
        aws_access_key="test_key",
        aws_secret_key="test_secret",
        region="ap-southeast-1"
    )
    
    url = await storage.upload(
        file_path="test/file.json",
        content=b'{"test": "data"}'
    )
    
    assert url.startswith("https://")
    assert "test-bucket" in url
```

**Database integration test:**
```python
# tests/integration/infrastructure/test_postgres_adapter.py
import pytest
from infrastructure.database.postgres_adapter import PostgresDatabase

@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection"""
    db = PostgresDatabase(
        database_url="postgresql://user:pass@localhost:5432/test",
        min_size=1,
        max_size=2
    )
    
    await db.connect()
    health = await db.health_check()
    
    assert health["status"] == "connected"
    
    await db.close()
```

### E2E Tests (API Layer)

**Run E2E tests:**
```bash
pytest tests/e2e/api/ -v
```

**Example test:**
```python
# tests/e2e/api/test_analyze.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check"""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["version"] == "3.0.0-hexagonal"

def test_analyze_upload():
    """Test PDF upload and analysis"""
    with open("tests/fixtures/sample.pdf", "rb") as pdf:
        response = client.post(
            "/api/v1/analyze-upload",
            files={"pdf_file": pdf},
            data={
                "user_id": "test_user",
                "expected_gross": "50000",
                "pvd_rate": "0.03"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "statement_id" in data
    assert "analysis" in data
```

### Run All Tests

**Run everything:**
```bash
pytest tests/ -v
```

**Run with coverage:**
```bash
pytest tests/ --cov=src --cov-report=html
```

**Run specific test:**
```bash
pytest tests/unit/domain/test_transaction.py::test_is_excluded -v
```

**Run with markers:**
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Run only e2e tests
pytest -m e2e
```

## Project Structure

### Complete Directory Tree
```
Bank_PDF_document_reading/
├── .github/                        # Project management
│   ├── copilot-instructions.md    # Master instructions
│   ├── REQUIREMENTS.md             # Business requirements
│   ├── DESIGN.md                   # Technical design
│   ├── tasks.json                  # Task tracking
│   └── ai-instructions/            # Detailed guidelines
│       ├── 00-START-HERE.md
│       ├── 01-WORKFLOW.md
│       ├── 02-ARCHITECTURE.md
│       ├── 03-DOMAIN-RULES.md
│       ├── 04-DEVELOPMENT.md
│       ├── 05-COMMON-ISSUES.md
│       └── 06-CODE-STANDARDS.md
│
├── database/                       # Database files
│   ├── schema.sql                 # Table definitions
│   ├── queries.sql                # Sample queries
│   └── README.md                  # Setup guide
│
├── src/                           # Application code
│   ├── domain/                    # Pure business logic
│   │   └── entities/
│   │       ├── transaction.py
│   │       ├── statement.py
│   │       └── salary_analysis.py
│   │
│   ├── application/               # Use cases & ports
│   │   ├── ports/
│   │   │   ├── pdf_extractor.py
│   │   │   ├── data_masker.py
│   │   │   ├── salary_analyzer.py
│   │   │   ├── storage.py
│   │   │   └── database.py
│   │   └── use_cases/
│   │       └── analyze_statement.py
│   │
│   ├── infrastructure/            # Adapters
│   │   ├── pdf/
│   │   │   └── pymupdf_extractor.py
│   │   ├── masking/
│   │   │   └── regex_masker.py
│   │   ├── analysis/
│   │   │   └── thai_analyzer.py
│   │   ├── storage/
│   │   │   └── s3_storage.py
│   │   └── database/
│   │       └── postgres_adapter.py
│   │
│   ├── api/v1/                    # FastAPI layer
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   └── analyze.py
│   │   ├── schemas.py
│   │   └── dependencies.py
│   │
│   ├── config.py                  # Settings
│   └── main.py                    # App entry point
│
├── tests/                         # Test suite
│   ├── unit/
│   │   ├── domain/
│   │   └── application/
│   ├── integration/
│   │   └── infrastructure/
│   └── e2e/
│       └── api/
│
├── data/                          # Local data storage
│   ├── json/                      # Extracted JSONs
│   ├── raw/                       # Raw PDFs
│   └── validated/                 # Validated results
│
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker image
├── docker-compose.yml             # Multi-container setup
├── .gitignore                     # Git ignore rules
├── .env.example                   # Environment template
└── README.md                      # Project overview
```

### File Counts

**Total: 31 Python files**
- Domain: 3 files
- Application: 6 files (5 ports + 1 use case)
- Infrastructure: 5 files (5 adapters)
- API: 7 files (2 routes + schemas + dependencies + config + main + __init__)

## Common Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Database Setup
```bash
# Create database
createdb bank_statements

# Run schema
psql bank_statements < database/schema.sql

# Test connection
psql bank_statements -c "SELECT version();"
```

### Docker Commands
```bash
# Build image
docker build -t bank-statement-api .

# Run container
docker run -p 8001:8001 bank-statement-api

# View logs
docker logs -f <container_id>

# Enter container
docker exec -it <container_id> bash
```

### S3 Commands
```bash
# List bucket
aws s3 ls s3://bank-statements-1761407671/

# Upload file
aws s3 cp local.pdf s3://bank-statements-1761407671/uploads/

# Download file
aws s3 cp s3://bank-statements-1761407671/file.pdf ./

# Check bucket settings
aws s3api get-public-access-block --bucket bank-statements-1761407671
```

### Environment Variables

**Required:**
```bash
# AWS
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-southeast-1
export S3_BUCKET_NAME=bank-statements-1761407671

# Database
export DATABASE_URL=postgresql://user:pass@localhost:5432/bank_statements

# API
export API_PORT=8001
```

**Optional:**
```bash
# Anthropic (for Claude AI)
export ANTHROPIC_API_KEY=your_key

# Logging
export LOG_LEVEL=INFO

# Storage
export LOCAL_STORAGE_PATH=data/storage
```

### Create .env File
```bash
# .env.example
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=bank-statements-1761407671
S3_PRESIGNED_URL_EXPIRATION=3600

DATABASE_URL=postgresql://bank_user:bank_password@localhost:5432/bank_statements
DATABASE_MIN_SIZE=5
DATABASE_MAX_SIZE=20

API_HOST=0.0.0.0
API_PORT=8001

LOG_LEVEL=INFO
LOCAL_STORAGE_PATH=data/storage
```

## Troubleshooting

### Issue: Import Errors
```bash
# Solution: Ensure src/ is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or run from src/ directory
cd src
python main.py
```

### Issue: Database Connection Failed
```bash
# Check PostgreSQL is running
pg_isready

# Check connection details
psql postgresql://user:pass@localhost:5432/bank_statements

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Issue: S3 Connection Failed
```bash
# Check AWS credentials
aws sts get-caller-identity

# Test bucket access
aws s3 ls s3://bank-statements-1761407671/

# Check region
aws configure get region
```

### Issue: Port Already in Use
```bash
# Find process using port 8001
lsof -i :8001

# Kill process
kill -9 <PID>

# Or use different port
export API_PORT=8002
```

## Next Steps

**For architecture patterns:**
→ Read 02-ARCHITECTURE.md

**For domain logic:**
→ Read 03-DOMAIN-RULES.md

**For debugging:**
→ Read 05-COMMON-ISSUES.md

**For code standards:**
→ Read 06-CODE-STANDARDS.md

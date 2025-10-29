# Common Issues & Solutions

**Read this for: Debugging, troubleshooting, known problems**

## Circular Import Errors

### Problem
```python
# Error message
ImportError: cannot import name 'Transaction' from partially initialized module 'domain.entities.transaction'
```

### Root Cause
- Domain imports from infrastructure
- Circular dependency between modules

### Solution

**❌ WRONG:**
```python
# domain/entities/statement.py
from infrastructure.analysis.thai_analyzer import ThaiSalaryAnalyzer  # BAD

class Statement:
    def analyze_salary(self):
        analyzer = ThaiSalaryAnalyzer()  # Tight coupling
        return analyzer.analyze(self)
```

**✅ CORRECT:**
```python
# Domain should never import infrastructure
# Use dependency injection from use case instead

# application/use_cases/analyze_statement.py
class AnalyzeStatementUseCase:
    def __init__(
        self,
        salary_analyzer: ISalaryAnalyzer  # Port, not adapter
    ):
        self.analyzer = salary_analyzer
    
    def execute(self, statement: Statement):
        return self.analyzer.analyze(statement)
```

### Verification
```bash
# Check for forbidden imports
grep -r "from infrastructure" src/domain/
grep -r "from infrastructure" src/application/

# Should return no results
```

## Port Not Found Errors

### Problem
```python
# Error message
ModuleNotFoundError: No module named 'application.ports.email_notifier'
```

### Root Cause
- Port interface not defined before adapter
- Incorrect import path
- Missing __init__.py

### Solution

**Step 1: Create Port**
```python
# application/ports/email_notifier.py
from abc import ABC, abstractmethod

class IEmailNotifier(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> bool:
        pass
```

**Step 2: Create __init__.py**
```python
# application/ports/__init__.py
from .email_notifier import IEmailNotifier

__all__ = ["IEmailNotifier"]
```

**Step 3: Import Correctly**
```python
# infrastructure/email/sendgrid_notifier.py
from application.ports.email_notifier import IEmailNotifier  # Correct path

class SendGridNotifier(IEmailNotifier):
    pass
```

### Verification
```bash
# Check port exists
ls -la src/application/ports/email_notifier.py

# Check __init__.py exists
ls -la src/application/ports/__init__.py

# Test import
cd src
python -c "from application.ports.email_notifier import IEmailNotifier; print('OK')"
```

## S3 Connection Failed

### Problem
```python
# Error message
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

### Root Cause
- AWS credentials not configured
- Environment variables not set
- Incorrect region

### Solution

**Step 1: Configure AWS CLI**
```bash
aws configure
# AWS Access Key ID: your_key
# AWS Secret Access Key: your_secret
# Default region name: ap-southeast-1
# Default output format: json
```

**Step 2: Set Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-southeast-1
export S3_BUCKET_NAME=bank-statements-1761407671
```

**Step 3: Verify Credentials**
```bash
# Test credentials
aws sts get-caller-identity

# Test bucket access
aws s3 ls s3://bank-statements-1761407671/
```

**Step 4: Check Code**
```python
# config.py
AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "bank-statements-1761407671")
```

### Alternative: Local Storage Fallback
```python
# api/v1/dependencies.py
def get_storage() -> IStorage:
    """Get storage implementation (S3 or Local fallback)"""
    
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        try:
            return S3Storage(...)
        except Exception as e:
            print(f"S3 failed, using local: {e}")
    
    return LocalStorage(base_path=settings.LOCAL_STORAGE_PATH)
```

## Database Connection Failed

### Problem
```python
# Error message
asyncpg.exceptions.InvalidCatalogNameError: database "bank_statements" does not exist
```

### Root Cause
- Database not created
- Connection string incorrect
- PostgreSQL not running
- Asyncpg not installed

### Solution

**Step 1: Install Asyncpg**
```bash
pip install asyncpg>=0.29.0
```

**Step 2: Create Database**
```bash
# Create database
createdb bank_statements

# Or with psql
psql -c "CREATE DATABASE bank_statements;"
```

**Step 3: Run Schema**
```bash
psql bank_statements < database/schema.sql
```

**Step 4: Verify Connection**
```bash
# Test connection
psql postgresql://bank_user:bank_password@localhost:5432/bank_statements

# List tables
psql bank_statements -c "\dt"
```

**Step 5: Check Connection String**
```python
# config.py
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://bank_user:bank_password@localhost:5432/bank_statements"
)
```

**Step 6: Check PostgreSQL Status**
```bash
# Check if running
pg_isready

# Start PostgreSQL (Ubuntu/Debian)
sudo systemctl start postgresql

# Start PostgreSQL (macOS)
brew services start postgresql
```

### Connection Pool Issues

**Problem:**
```python
asyncpg.exceptions.TooManyConnectionsError: too many connections
```

**Solution:**
```python
# Adjust pool size in config.py
DATABASE_MIN_SIZE: int = int(os.getenv("DATABASE_MIN_SIZE", "5"))
DATABASE_MAX_SIZE: int = int(os.getenv("DATABASE_MAX_SIZE", "20"))

# Or increase PostgreSQL max_connections
# Edit postgresql.conf:
max_connections = 100
```

## PDF Extraction Errors

### Problem
```python
# Error message
fitz.fitz.FileNotFoundError: cannot open file.pdf
```

### Root Cause
- PDF file doesn't exist
- Incorrect file path
- PDF is encrypted without password
- Corrupted PDF

### Solution

**Step 1: Check File Exists**
```python
import os

def extract_pdf(pdf_path: str):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    # Continue with extraction
```

**Step 2: Handle Encrypted PDFs**
```python
# infrastructure/pdf/pymupdf_extractor.py
import fitz

def extract(self, pdf_path: str, password: str = None) -> dict:
    doc = fitz.open(pdf_path)
    
    if doc.is_encrypted:
        if not password:
            raise ValueError("PDF is encrypted but no password provided")
        
        if not doc.authenticate(password):
            raise ValueError("Incorrect PDF password")
    
    # Continue extraction
```

**Step 3: Handle Corrupted PDFs**
```python
def extract(self, pdf_path: str, password: str = None) -> dict:
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise ValueError(f"Cannot open PDF: {str(e)}")
    
    # Continue extraction
```

## Thai Character Encoding Issues

### Problem
```python
# Thai text appears as: �������������
# Or UnicodeDecodeError
```

### Root Cause
- File not saved as UTF-8
- System locale not set to UTF-8
- PyMuPDF not handling Thai characters

### Solution

**Step 1: Ensure UTF-8 Encoding**
```python
# Always specify encoding when reading/writing
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()

with open("file.txt", "w", encoding="utf-8") as f:
    f.write("สวัสดี")
```

**Step 2: Check System Locale**
```bash
# Check locale
locale

# Set UTF-8 locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

**Step 3: PyMuPDF Extract**
```python
# PyMuPDF handles Thai correctly by default
doc = fitz.open("statement.pdf")
page = doc[0]
text = page.get_text("text")  # UTF-8 by default
print(text)  # Should display Thai correctly
```

## Import Path Issues

### Problem
```python
# Error message
ModuleNotFoundError: No module named 'domain'
```

### Root Cause
- PYTHONPATH not set
- Running from wrong directory
- Missing __init__.py files

### Solution

**Step 1: Set PYTHONPATH**
```bash
# Add src/ to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or run from src/ directory
cd src
python main.py
```

**Step 2: Check __init__.py Files**
```bash
# Ensure all packages have __init__.py
find src -type d -exec touch {}/__init__.py \;

# Check structure
tree src -I __pycache__
```

**Step 3: Use Relative Imports (if in same package)**
```python
# From src/api/v1/routes/analyze.py
from ..schemas import AnalyzeRequest  # Relative import
from api.v1.schemas import AnalyzeRequest  # Absolute import (preferred)
```

## Port Already in Use

### Problem
```bash
# Error message
OSError: [Errno 98] Address already in use
```

### Root Cause
- Another process using port 8001
- Previous uvicorn instance still running

### Solution

**Step 1: Find Process**
```bash
# Find process using port 8001
lsof -i :8001

# Or with netstat
netstat -tulpn | grep 8001
```

**Step 2: Kill Process**
```bash
# Kill by PID
kill -9 <PID>

# Or kill all python processes (careful!)
pkill -f "python main.py"
pkill -f uvicorn
```

**Step 3: Use Different Port**
```bash
# Change port in config
export API_PORT=8002

# Or in main.py
uvicorn.run("main:app", host="0.0.0.0", port=8002)
```

## Dependency Injection Not Working

### Problem
```python
# Error message
TypeError: get_analyze_use_case() got an unexpected keyword argument 'database'
```

### Root Cause
- Use case constructor doesn't accept parameter
- DI function not updated
- FastAPI Depends() not used correctly

### Solution

**Step 1: Update Use Case Constructor**
```python
# application/use_cases/analyze_statement.py
class AnalyzeStatementUseCase:
    def __init__(
        self,
        pdf_extractor: IPDFExtractor,
        database: IDatabase = None  # Add parameter
    ):
        self.pdf_extractor = pdf_extractor
        self.database = database
```

**Step 2: Update DI Function**
```python
# api/v1/dependencies.py
def get_analyze_use_case(
    pdf_extractor: IPDFExtractor = None,
    database: IDatabase = None  # Add parameter
) -> AnalyzeStatementUseCase:
    return AnalyzeStatementUseCase(
        pdf_extractor=pdf_extractor or get_pdf_extractor(),
        database=database  # Pass parameter
    )
```

**Step 3: Inject in Route**
```python
# api/v1/routes/analyze.py
from fastapi import Depends

@router.post("/analyze")
async def analyze(
    database: IDatabase = Depends(get_database)  # Inject
):
    use_case = get_analyze_use_case(database=database)
    result = await use_case.execute(...)
    return result
```

## Async/Await Errors

### Problem
```python
# Error message
RuntimeError: This event loop is already running
# Or
TypeError: object dict can't be used in 'await' expression
```

### Root Cause
- Mixing sync and async code
- Forgetting await keyword
- Wrong function signature (sync vs async)

### Solution

**Step 1: Consistent Async**
```python
# ❌ WRONG: Mixing sync and async
class PostgresDatabase:
    def connect(self):  # Sync function
        await self.pool.acquire()  # Can't use await in sync

# ✅ CORRECT: All async
class PostgresDatabase:
    async def connect(self):  # Async function
        await self.pool.acquire()  # Can use await
```

**Step 2: Use Await**
```python
# ❌ WRONG: Forgot await
result = database.save_analysis(...)  # Returns coroutine, not result

# ✅ CORRECT: Use await
result = await database.save_analysis(...)  # Returns result
```

**Step 3: Route Handler Async**
```python
# ❌ WRONG: Sync handler with async call
@router.post("/analyze")
def analyze(database: IDatabase = Depends(get_database)):
    await database.save_analysis(...)  # Can't use await in sync

# ✅ CORRECT: Async handler
@router.post("/analyze")
async def analyze(database: IDatabase = Depends(get_database)):
    await database.save_analysis(...)  # Can use await
```

## Testing Issues

### Problem: Tests Can't Find Modules
```bash
# Error message
ModuleNotFoundError: No module named 'domain'
```

**Solution:**
```bash
# Run from project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/

# Or use pytest config
# pytest.ini
[pytest]
pythonpath = src
```

### Problem: Tests Fail with Database
```bash
# Error message
asyncpg.exceptions.InvalidCatalogNameError: database "test_db" does not exist
```

**Solution:**
```python
# tests/conftest.py
import pytest
import asyncpg

@pytest.fixture(scope="session")
async def test_database():
    """Setup test database"""
    # Create test database
    conn = await asyncpg.connect(
        "postgresql://user:pass@localhost:5432/postgres"
    )
    await conn.execute("DROP DATABASE IF EXISTS test_db")
    await conn.execute("CREATE DATABASE test_db")
    await conn.close()
    
    yield "postgresql://user:pass@localhost:5432/test_db"
    
    # Cleanup
    conn = await asyncpg.connect(
        "postgresql://user:pass@localhost:5432/postgres"
    )
    await conn.execute("DROP DATABASE test_db")
    await conn.close()
```

## Quick Diagnostic Commands

**Check Python version:**
```bash
python --version  # Should be 3.10+
```

**Check installed packages:**
```bash
pip list | grep -E "fastapi|uvicorn|pymupdf|boto3|asyncpg"
```

**Check database connection:**
```bash
psql bank_statements -c "SELECT COUNT(*) FROM analyses;"
```

**Check S3 bucket:**
```bash
aws s3 ls s3://bank-statements-1761407671/ --region ap-southeast-1
```

**Check port availability:**
```bash
lsof -i :8001
```

**Check API health:**
```bash
curl http://localhost:8001/api/v1/health
```

## Next Steps

**For architecture patterns:**
→ Read 02-ARCHITECTURE.md

**For domain rules:**
→ Read 03-DOMAIN-RULES.md

**For running/testing:**
→ Read 04-DEVELOPMENT.md

**For code standards:**
→ Read 06-CODE-STANDARDS.md

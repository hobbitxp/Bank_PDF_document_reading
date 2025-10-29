# Architecture Guidelines

**Read this for: Coding tasks, adding adapters, understanding structure**

## Hexagonal Architecture (Ports & Adapters)

### Overview

The project uses Hexagonal Architecture (also called Ports & Adapters pattern) to:
- Isolate business logic from external dependencies
- Make testing easier (mock external systems)
- Allow swapping implementations without changing business logic
- Maintain clear separation of concerns

### Layers

**Domain Layer (Core)**
- Pure business logic
- No framework dependencies
- No imports from application/infrastructure
- Contains: Entities, Value Objects, Domain Services

**Application Layer (Use Cases)**
- Orchestrates domain objects
- Defines ports (interfaces)
- Contains: Use Cases, Port definitions

**Infrastructure Layer (Adapters)**
- Implements ports
- Talks to external systems
- Contains: Concrete implementations of ports

**API Layer (Entry Point)**
- FastAPI endpoints
- Request/Response schemas
- Dependency injection setup

### Project Structure

```
src/
├── domain/                     # Pure business logic
│   └── entities/              # Transaction, Statement, SalaryAnalysis
│       ├── transaction.py     # Transaction entity with scoring
│       ├── statement.py       # Statement aggregate root
│       └── salary_analysis.py # Analysis result entity
│
├── application/               # Use cases & interfaces
│   ├── ports/                 # Interface definitions
│   │   ├── pdf_extractor.py  # IPDFExtractor interface
│   │   ├── data_masker.py    # IDataMasker interface
│   │   ├── salary_analyzer.py # ISalaryAnalyzer interface
│   │   ├── storage.py         # IStorage interface
│   │   └── database.py        # IDatabase interface
│   └── use_cases/            # Business workflows
│       └── analyze_statement.py # AnalyzeStatementUseCase
│
├── infrastructure/            # External system adapters
│   ├── pdf/                  # PDF processing
│   │   └── pymupdf_extractor.py # PyMuPDF implementation
│   ├── masking/              # Data masking (PDPA)
│   │   └── regex_masker.py   # Regex-based masker
│   ├── analysis/             # Salary analysis
│   │   └── thai_analyzer.py  # Thai tax calculation
│   ├── storage/              # File storage
│   │   └── s3_storage.py     # S3 + Local implementations
│   └── database/             # Database access
│       └── postgres_adapter.py # PostgreSQL implementation
│
├── api/v1/                   # FastAPI endpoints
│   ├── routes/               # Route handlers
│   │   ├── health.py         # Health check
│   │   └── analyze.py        # Analysis endpoints
│   ├── schemas.py            # Pydantic models
│   └── dependencies.py       # DI container
│
├── config.py                 # Settings
└── main.py                   # FastAPI app entry point
```

### Data Flow

```
Mobile App
  ↓ (POST /api/v1/analyze-upload)
API Layer (FastAPI)
  ↓ (Inject dependencies)
Use Case (AnalyzeStatementUseCase)
  ↓
PDF Extractor Adapter (PyMuPDF)
  ↓
Statement Entity (Domain)
  ↓
Data Masker Adapter (Regex)
  ↓
Masked Statement + Mapping
  ↓
Salary Analyzer Adapter (Thai Tax)
  ↓
SalaryAnalysis Entity (Domain)
  ↓
Storage Adapter (S3)
  ↓
Database Adapter (PostgreSQL)
  ↓
Response JSON (API)
  ↓
Mobile App
```

## Critical Patterns

### 1. Dependency Rule

**Rule:** Dependencies point inward only

```
API → Application → Domain
  ↓
Infrastructure
```

**Allowed:**
- ✅ API imports Application
- ✅ API imports Infrastructure
- ✅ Application imports Domain
- ✅ Infrastructure imports Application (for ports)
- ✅ Infrastructure imports Domain

**FORBIDDEN:**
- ❌ Domain imports Application
- ❌ Domain imports Infrastructure
- ❌ Application imports Infrastructure

### 2. Port and Adapter Pattern

**Port (Interface):**
```python
# application/ports/pdf_extractor.py
from abc import ABC, abstractmethod

class IPDFExtractor(ABC):
    """Port for PDF extraction"""
    
    @abstractmethod
    def extract(self, pdf_path: str, password: str = None) -> dict:
        """Extract text from PDF"""
        pass
```

**Adapter (Implementation):**
```python
# infrastructure/pdf/pymupdf_extractor.py
import fitz  # PyMuPDF

class PyMuPDFExtractor(IPDFExtractor):
    """Adapter for PyMuPDF library"""
    
    def extract(self, pdf_path: str, password: str = None) -> dict:
        doc = fitz.open(pdf_path)
        if password:
            doc.authenticate(password)
        # ... extraction logic
        return result
```

### 3. Dependency Injection

**DI Container:**
```python
# api/v1/dependencies.py
from functools import lru_cache

@lru_cache()
def get_pdf_extractor() -> IPDFExtractor:
    """Get PDF extractor implementation"""
    return PyMuPDFExtractor()
```

**Usage in Route:**
```python
# api/v1/routes/analyze.py
from fastapi import Depends

@router.post("/analyze")
async def analyze(
    extractor: IPDFExtractor = Depends(get_pdf_extractor)
):
    result = extractor.extract(pdf_path)
    return result
```

**Usage in Use Case:**
```python
# application/use_cases/analyze_statement.py
class AnalyzeStatementUseCase:
    def __init__(
        self,
        pdf_extractor: IPDFExtractor,
        data_masker: IDataMasker,
        salary_analyzer: ISalaryAnalyzer
    ):
        self.pdf_extractor = pdf_extractor
        self.data_masker = data_masker
        self.salary_analyzer = salary_analyzer
```

### 4. Domain Entity Design

**Transaction Entity:**
```python
# domain/entities/transaction.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Transaction:
    """Transaction entity (rich domain model)"""
    
    page: int
    amount: float
    description: str
    is_credit: bool
    time: Optional[str] = None
    channel: Optional[str] = None
    payer: Optional[str] = None
    score: int = 0
    cluster_id: Optional[int] = None
    
    def is_excluded(self) -> bool:
        """Business logic: Check if transaction is excluded"""
        exclusion_keywords = ["ทรูมันนี่", "พร้อมเพย์", "เงินสด"]
        return any(kw in self.description for kw in exclusion_keywords)
    
    def has_keyword(self, keywords: list[str]) -> bool:
        """Business logic: Check if description contains keywords"""
        return any(kw in self.description for kw in keywords)
    
    def is_early_morning(self) -> bool:
        """Business logic: Check if transaction is in payroll window"""
        if not self.time:
            return False
        hour = int(self.time.split(":")[0])
        return 1 <= hour <= 6
```

**Key Principles:**
- Rich domain model (not anemic)
- Business logic in domain methods
- No framework dependencies
- Immutable where possible

### 5. Use Case Pattern

**Structure:**
```python
# application/use_cases/analyze_statement.py
class AnalyzeStatementUseCase:
    """
    Use case: Analyze bank statement
    
    Orchestrates:
    1. PDF extraction
    2. Data masking
    3. Salary analysis
    4. Storage
    5. Database recording
    """
    
    def __init__(
        self,
        pdf_extractor: IPDFExtractor,
        data_masker: IDataMasker,
        salary_analyzer: ISalaryAnalyzer,
        storage: IStorage,
        database: IDatabase
    ):
        # Inject all dependencies
        self.pdf_extractor = pdf_extractor
        self.data_masker = data_masker
        self.salary_analyzer = salary_analyzer
        self.storage = storage
        self.database = database
    
    async def execute(
        self,
        pdf_path: str,
        user_id: str,
        **options
    ) -> dict:
        # 1. Extract
        raw_data = self.pdf_extractor.extract(pdf_path)
        
        # 2. Mask
        masked_data, mapping = self.data_masker.mask(raw_data)
        
        # 3. Analyze
        analysis = self.salary_analyzer.analyze(masked_data)
        
        # 4. Store files
        urls = await self.storage.upload_results(...)
        
        # 5. Record in database
        await self.database.save_analysis(...)
        
        return result
```

## Adding New Adapter

### Step-by-Step Guide

**Step 1: Define Port (Interface)**

Create file in `application/ports/`:
```python
# application/ports/email_notifier.py
from abc import ABC, abstractmethod

class IEmailNotifier(ABC):
    """Port for email notifications"""
    
    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        body: str
    ) -> bool:
        """Send email notification"""
        pass
```

**Step 2: Implement Adapter**

Create file in `infrastructure/email/`:
```python
# infrastructure/email/sendgrid_notifier.py
from application.ports.email_notifier import IEmailNotifier
import sendgrid

class SendGridNotifier(IEmailNotifier):
    """Adapter for SendGrid email service"""
    
    def __init__(self, api_key: str):
        self.client = sendgrid.SendGridAPIClient(api_key)
    
    async def send(
        self,
        to: str,
        subject: str,
        body: str
    ) -> bool:
        message = {
            "to": to,
            "subject": subject,
            "body": body
        }
        response = self.client.send(message)
        return response.status_code == 200
```

**Step 3: Register in DI Container**

Update `api/v1/dependencies.py`:
```python
# api/v1/dependencies.py
from infrastructure.email.sendgrid_notifier import SendGridNotifier
from application.ports.email_notifier import IEmailNotifier
from config import settings

@lru_cache()
def get_email_notifier() -> IEmailNotifier:
    """Get email notifier implementation"""
    return SendGridNotifier(api_key=settings.SENDGRID_API_KEY)
```

**Step 4: Inject in Use Case**

Update use case constructor:
```python
# application/use_cases/analyze_statement.py
class AnalyzeStatementUseCase:
    def __init__(
        self,
        pdf_extractor: IPDFExtractor,
        email_notifier: IEmailNotifier = None  # Optional
    ):
        self.pdf_extractor = pdf_extractor
        self.email_notifier = email_notifier
    
    async def execute(self, ...):
        # ... analysis logic
        
        if self.email_notifier:
            await self.email_notifier.send(
                to=user_email,
                subject="Analysis Complete",
                body=f"Your analysis is ready"
            )
```

**Step 5: Update Route Handler**

Inject via FastAPI Depends:
```python
# api/v1/routes/analyze.py
@router.post("/analyze")
async def analyze(
    pdf_file: UploadFile,
    email_notifier: IEmailNotifier = Depends(get_email_notifier)
):
    use_case = get_analyze_use_case(
        email_notifier=email_notifier
    )
    result = await use_case.execute(...)
    return result
```

## Common Patterns

### Pattern 1: Async Operations

**Port:**
```python
class IStorage(ABC):
    @abstractmethod
    async def upload(self, file_path: str, content: bytes) -> str:
        """Upload file asynchronously"""
        pass
```

**Adapter:**
```python
class S3Storage(IStorage):
    async def upload(self, file_path: str, content: bytes) -> str:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.s3_client.put_object,
            self.bucket_name,
            file_path,
            content
        )
        return f"s3://{self.bucket_name}/{file_path}"
```

### Pattern 2: Connection Pooling

**Global instance for connection reuse:**
```python
# api/v1/dependencies.py
_database_instance: PostgresDatabase | None = None

async def get_database() -> IDatabase:
    global _database_instance
    
    if _database_instance is None:
        _database_instance = PostgresDatabase(
            database_url=settings.DATABASE_URL,
            min_size=5,
            max_size=20
        )
        await _database_instance.connect()
    
    return _database_instance
```

**Cleanup on shutdown:**
```python
# main.py
@app.on_event("shutdown")
async def shutdown_event():
    await close_database()
```

### Pattern 3: Factory Methods

**Domain entity factories:**
```python
# domain/entities/statement.py
class Statement:
    def get_credit_transactions(self) -> list[Transaction]:
        """Factory method: Get only credit transactions"""
        return [tx for tx in self.transactions if tx.is_credit]
    
    def get_debit_transactions(self) -> list[Transaction]:
        """Factory method: Get only debit transactions"""
        return [tx for tx in self.transactions if not tx.is_credit]
```

### Pattern 4: Configuration

**Settings class:**
```python
# config.py
import os

class Settings:
    # AWS
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "bank-statements")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:pass@localhost:5432/db"
    )
    
    # API
    API_PORT: int = int(os.getenv("API_PORT", "8001"))

settings = Settings()
```

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Direct Import in Domain
```python
# domain/entities/statement.py
from infrastructure.pdf.pymupdf_extractor import PyMuPDFExtractor  # WRONG

class Statement:
    def load_from_pdf(self, path: str):
        extractor = PyMuPDFExtractor()  # Tight coupling
```

**✅ Correct:**
```python
# Domain should not know about infrastructure
# Use dependency injection from use case instead
```

### ❌ Anti-Pattern 2: Use Case with Concrete Implementation
```python
# application/use_cases/analyze_statement.py
from infrastructure.pdf.pymupdf_extractor import PyMuPDFExtractor  # WRONG

class AnalyzeStatementUseCase:
    def __init__(self):
        self.extractor = PyMuPDFExtractor()  # Tight coupling
```

**✅ Correct:**
```python
class AnalyzeStatementUseCase:
    def __init__(self, pdf_extractor: IPDFExtractor):
        self.extractor = pdf_extractor  # Depend on interface
```

### ❌ Anti-Pattern 3: No Port Definition
```python
# infrastructure/email/sendgrid_notifier.py
class SendGridNotifier:  # No interface
    def send(self, to: str, subject: str, body: str):
        pass
```

**✅ Correct:**
```python
# 1. Define port first
# application/ports/email_notifier.py
class IEmailNotifier(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str):
        pass

# 2. Implement adapter
# infrastructure/email/sendgrid_notifier.py
class SendGridNotifier(IEmailNotifier):
    def send(self, to: str, subject: str, body: str):
        # Implementation
```

### ❌ Anti-Pattern 4: Business Logic in Adapter
```python
# infrastructure/analysis/thai_analyzer.py
class ThaiSalaryAnalyzer:
    def analyze(self, statement: Statement) -> SalaryAnalysis:
        # Salary detection logic (WRONG - should be in domain)
        if tx.amount > 30000:
            # Business rule in adapter
```

**✅ Correct:**
```python
# Business logic in domain
# domain/entities/transaction.py
class Transaction:
    def is_salary_candidate(self) -> bool:
        return self.amount > 30000  # Business rule

# Adapter uses domain methods
# infrastructure/analysis/thai_analyzer.py
class ThaiSalaryAnalyzer:
    def analyze(self, statement: Statement):
        candidates = [
            tx for tx in statement.transactions
            if tx.is_salary_candidate()  # Use domain method
        ]
```

## Testing Strategy

### Unit Tests (Domain)
```python
# tests/unit/domain/test_transaction.py
def test_is_excluded():
    tx = Transaction(
        page=1,
        amount=100,
        description="ทรูมันนี่",
        is_credit=True
    )
    assert tx.is_excluded() == True
```

### Integration Tests (Adapters)
```python
# tests/integration/infrastructure/test_s3_storage.py
@pytest.mark.asyncio
async def test_s3_upload():
    storage = S3Storage(bucket_name="test-bucket")
    url = await storage.upload("test.json", b"data")
    assert url.startswith("s3://")
```

### E2E Tests (API)
```python
# tests/e2e/api/test_analyze.py
def test_analyze_endpoint(client):
    response = client.post(
        "/api/v1/analyze-upload",
        files={"pdf_file": open("test.pdf", "rb")}
    )
    assert response.status_code == 200
```

## Next Steps

**For domain rules:**
→ Read 03-DOMAIN-RULES.md

**For running/testing:**
→ Read 04-DEVELOPMENT.md

**For debugging:**
→ Read 05-COMMON-ISSUES.md

**For code standards:**
→ Read 06-CODE-STANDARDS.md

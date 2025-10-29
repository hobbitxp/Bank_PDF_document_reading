# Code Standards & Conventions

**Read this for: Code style, conventions, before committing**

## Python Conventions

### Type Hints (Required)

**Use Python 3.10+ syntax:**
```python
# ✅ CORRECT: Modern syntax
from typing import Optional

def process(data: dict[str, int]) -> tuple[str, int]:
    return ("result", 42)

# ❌ WRONG: Old syntax
from typing import Dict, Tuple

def process(data: Dict[str, int]) -> Tuple[str, int]:
    return ("result", 42)
```

**Always use type hints:**
```python
# ✅ CORRECT: Full type hints
def calculate_tax(
    gross_salary: float,
    deductions: float = 0.0
) -> float:
    return (gross_salary - deductions) * 0.05

# ❌ WRONG: No type hints
def calculate_tax(gross_salary, deductions=0.0):
    return (gross_salary - deductions) * 0.05
```

**Optional vs None:**
```python
from typing import Optional

# ✅ CORRECT: Use Optional for nullable
def find_user(user_id: str) -> Optional[dict]:
    return user or None

# ❌ WRONG: Missing Optional
def find_user(user_id: str) -> dict:
    return user or None  # Can return None but type says dict
```

### Dataclasses (Preferred for Entities)

**Use dataclass decorator:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Transaction:
    """Transaction entity"""
    page: int
    amount: float
    description: str
    is_credit: bool
    time: Optional[str] = None
    score: int = 0
```

**Benefits:**
- Automatic `__init__`, `__repr__`, `__eq__`
- Type hints integrated
- Less boilerplate

### Error Handling

**Specific exceptions:**
```python
# ✅ CORRECT: Specific exceptions
try:
    result = parse_pdf(path)
except FileNotFoundError:
    logger.error(f"PDF not found: {path}")
    raise
except PermissionError:
    logger.error(f"No permission to read: {path}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# ❌ WRONG: Catch all exceptions
try:
    result = parse_pdf(path)
except Exception:
    pass  # Silently swallows errors
```

**Informative error messages:**
```python
# ✅ CORRECT: Context in error
if not os.path.exists(pdf_path):
    raise FileNotFoundError(
        f"PDF file not found: {pdf_path}\n"
        f"Current directory: {os.getcwd()}\n"
        f"Expected path: {os.path.abspath(pdf_path)}"
    )

# ❌ WRONG: Generic error
if not os.path.exists(pdf_path):
    raise FileNotFoundError("File not found")
```

**Thai error messages for user-facing:**
```python
# User-facing errors (Thai)
if not password:
    raise ValueError("ไม่พบรหัสผ่าน PDF กรุณาระบุรหัสผ่าน")

if salary < 0:
    raise ValueError("เงินเดือนต้องเป็นจำนวนบวก")

# Internal errors (English)
if not self.database_connected:
    raise RuntimeError("Database connection not established")
```

### Naming Conventions

**Variables and functions: snake_case**
```python
# ✅ CORRECT
user_id = "12345"
gross_salary = 50000.0

def calculate_net_salary(gross: float) -> float:
    return gross * 0.8
```

**Classes: PascalCase**
```python
# ✅ CORRECT
class SalaryAnalyzer:
    pass

class PostgresDatabase:
    pass
```

**Constants: UPPER_SNAKE_CASE**
```python
# ✅ CORRECT
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
SALARY_KEYWORDS = ["เงินเดือน", "BSD02", "Payroll"]
```

**Private methods: _leading_underscore**
```python
class Analyzer:
    def analyze(self):
        result = self._calculate_score()
        return result
    
    def _calculate_score(self) -> int:
        """Private helper method"""
        return 42
```

### Imports

**Order:**
```python
# 1. Standard library
import os
import sys
from typing import Optional

# 2. Third-party
import fitz
import pandas as pd
from fastapi import APIRouter

# 3. Local application
from domain.entities.transaction import Transaction
from application.ports.database import IDatabase
```

**Absolute imports (preferred):**
```python
# ✅ CORRECT: Absolute
from application.ports.database import IDatabase
from infrastructure.database.postgres_adapter import PostgresDatabase

# ❌ AVOID: Relative (only within same package)
from ..ports.database import IDatabase
```

**One import per line:**
```python
# ✅ CORRECT
from domain.entities.transaction import Transaction
from domain.entities.statement import Statement
from domain.entities.salary_analysis import SalaryAnalysis

# ❌ WRONG
from domain.entities.transaction import Transaction; from domain.entities.statement import Statement
```

## Documentation Standards

### NO ICONS/EMOJIS POLICY

**CRITICAL: This is a firm rule**

**❌ FORBIDDEN in ALL documentation:**
```markdown
## 🌟 Features
- 📄 PDF Extraction
- 🔒 Data Masking
- ✅ Tests passed
⚠️ Warning: Check this
```

**✅ CORRECT: Plain text only:**
```markdown
## Features
- PDF Extraction
- Data Masking
- Tests passed
WARNING: Check this
```

**Rationale:**
- Professional documentation
- Better accessibility (screen readers)
- Universal compatibility (all terminals/editors)
- No encoding issues
- Easier to grep/search

**Exception:** None. This rule has no exceptions.

### Docstrings (Required for Public APIs)

**Function docstrings:**
```python
def calculate_progressive_tax(taxable_income: float) -> float:
    """
    Calculate Thai progressive income tax.
    
    Args:
        taxable_income: Annual taxable income in THB
    
    Returns:
        Annual tax amount in THB
    
    Example:
        >>> calculate_progressive_tax(500_000)
        22500.0
    """
    pass
```

**Class docstrings:**
```python
class PostgresDatabase(IDatabase):
    """
    PostgreSQL database adapter.
    
    Implements IDatabase port using asyncpg for async operations.
    Uses connection pooling for performance.
    
    Attributes:
        database_url: PostgreSQL connection string
        pool: Connection pool (asyncpg.Pool)
    
    Example:
        >>> db = PostgresDatabase("postgresql://...")
        >>> await db.connect()
        >>> await db.save_analysis(...)
    """
    pass
```

**Module docstrings:**
```python
"""
Domain Entities: Transaction

This module defines the Transaction entity with business logic
for salary detection scoring and exclusion rules.
"""

from dataclasses import dataclass
...
```

### Comments

**Explain WHY, not WHAT:**
```python
# ✅ CORRECT: Explains reasoning
# Use 3% threshold because Thai salaries typically vary by rounding
cluster_threshold = 0.03

# ❌ WRONG: States the obvious
# Set threshold to 0.03
cluster_threshold = 0.03
```

**Thai comments for Thai-specific logic:**
```python
# Thai tax brackets (2024)
# วงเงินแรก 150,000 บาท: ยกเว้น
# 150,001-300,000 บาท: 5%
# 300,001-500,000 บาท: 10%
tax_brackets = [
    (150_000, 0.00),
    (150_000, 0.05),
    (200_000, 0.10),
]
```

**TODO comments:**
```python
# TODO(username): Add support for multiple currencies
# FIXME: This breaks when amount is negative
# HACK: Temporary workaround until API v2
```

## File Structure Standards

### Maximum File Length

**Guideline:** 500 lines max per file

**If exceeding:**
- Break into multiple files
- Extract helper functions
- Separate concerns

**Example:**
```python
# Instead of one 800-line analyze_salary.py:
analyze_salary.py          # Main analyzer (300 lines)
tax_calculator.py          # Tax logic (150 lines)
clustering.py              # Clustering algorithm (150 lines)
```

### File Organization

**Within a file:**
```python
"""Module docstring"""

# 1. Imports
import os
from typing import Optional

# 2. Constants
MAX_RETRIES = 3

# 3. Helper functions (private)
def _validate_input(data: dict) -> bool:
    pass

# 4. Main classes/functions (public)
class Analyzer:
    pass

# 5. Main execution (if script)
if __name__ == "__main__":
    pass
```

### Module __init__.py

**Export public API:**
```python
# infrastructure/database/__init__.py
from .postgres_adapter import PostgresDatabase

__all__ = ["PostgresDatabase"]
```

**Benefits:**
- Clear public API
- Easier imports
- Prevents internal imports

## Git Commit Standards

### Commit Message Format

**Structure:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `test`: Add/modify tests
- `chore`: Build/tooling changes

**Examples:**
```bash
# Good commits
git commit -m "feat(api): add database integration to health check"
git commit -m "fix(domain): correct salary clustering threshold"
git commit -m "docs(readme): update installation instructions"
git commit -m "refactor(storage): extract S3 connection to separate class"

# Bad commits
git commit -m "fixed stuff"
git commit -m "update"
git commit -m "wip"
```

### What to Commit

**✅ Commit:**
- Source code (.py files)
- Configuration files (.env.example, not .env)
- Documentation (.md files)
- Requirements (requirements.txt)
- Database schema (schema.sql)
- Tests

**❌ Never commit:**
- `*_mapping.json` files (contain unmasked data)
- `.env` files (contain secrets)
- `__pycache__/` directories
- `.pyc` files
- `venv/` or `env/` directories
- IDE config (.vscode/, .idea/)
- Large binary files (PDFs)

### .gitignore Template

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Secrets
.env
.env.local
*_mapping.json

# IDE
.vscode/
.idea/
*.swp
*.swo

# Data
data/raw/*.pdf
data/json/*_masked.json
data/storage/

# OS
.DS_Store
Thumbs.db

# Allowed exceptions
!.env.example
!data/json/.gitkeep
```

## Testing Standards

### Test File Naming

**Pattern: test_*.py**
```
tests/
├── unit/
│   └── domain/
│       └── test_transaction.py
├── integration/
│   └── infrastructure/
│       └── test_postgres_adapter.py
└── e2e/
    └── api/
        └── test_analyze.py
```

### Test Function Naming

**Pattern: test_<what>_<expected>**
```python
def test_is_excluded_returns_true_for_ewallet():
    pass

def test_calculate_tax_returns_zero_for_low_income():
    pass

def test_save_analysis_raises_error_when_disconnected():
    pass
```

### Test Structure (AAA Pattern)

```python
def test_calculate_score_with_all_factors():
    # Arrange
    tx = Transaction(
        page=1,
        amount=50000,
        description="เงินเดือน มกราคม",
        is_credit=True,
        time="03:45",
        payer="ACME Corp"
    )
    keywords = ["เงินเดือน"]
    employer = "ACME Corp"
    
    # Act
    score = tx.calculate_score(keywords, employer, cluster_bonus=True)
    
    # Assert
    assert score == 15  # Max score
```

## CLI Standards

### Argparse Usage

**Thai help text:**
```python
import argparse

parser = argparse.ArgumentParser(
    description="วิเคราะห์เงินเดือนจาก bank statement"
)

parser.add_argument(
    "pdf_path",
    help="ไฟล์ PDF bank statement"
)

parser.add_argument(
    "--password",
    help="รหัสผ่าน PDF (ถ้ามี)"
)

parser.add_argument(
    "--expected-gross",
    type=float,
    help="เงินเดือน gross ที่คาดหวัง (บาท)"
)

args = parser.parse_args()
```

**Usage output:**
```bash
$ python analyze.py --help
usage: analyze.py [-h] [--password PASSWORD] [--expected-gross EXPECTED_GROSS] pdf_path

วิเคราะห์เงินเดือนจาก bank statement

positional arguments:
  pdf_path              ไฟล์ PDF bank statement

optional arguments:
  -h, --help            show this help message and exit
  --password PASSWORD   รหัสผ่าน PDF (ถ้ามี)
  --expected-gross EXPECTED_GROSS
                        เงินเดือน gross ที่คาดหวัง (บาท)
```

## Code Review Checklist

Before submitting code for review:

**Functionality:**
- [ ] Code works as intended
- [ ] All tests pass
- [ ] No regressions

**Architecture:**
- [ ] Follows Hexagonal Architecture
- [ ] No domain → infrastructure imports
- [ ] Uses dependency injection

**Code Quality:**
- [ ] Type hints on all functions
- [ ] Docstrings on public APIs
- [ ] No magic numbers (use constants)
- [ ] Error handling implemented

**Documentation:**
- [ ] NO emoji icons used
- [ ] README.md updated (if needed)
- [ ] DESIGN.md updated (if architecture changed)
- [ ] tasks.json updated

**Security:**
- [ ] No secrets in code
- [ ] No `*_mapping.json` committed
- [ ] PDPA compliance maintained

**Testing:**
- [ ] Unit tests for domain logic
- [ ] Integration tests for adapters
- [ ] E2E tests for critical paths

## Next Steps

**For workflow:**
→ Read 01-WORKFLOW.md

**For architecture:**
→ Read 02-ARCHITECTURE.md

**For domain rules:**
→ Read 03-DOMAIN-RULES.md

**For running/testing:**
→ Read 04-DEVELOPMENT.md

**For debugging:**
→ Read 05-COMMON-ISSUES.md

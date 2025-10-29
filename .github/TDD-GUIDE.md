# TDD Quick Reference

## Test-Driven Development (TDD) Workflow

**MANDATORY for all features**

### Red-Green-Refactor Cycle

```
┌──────────────────────────────┐
│ 1. RED: Write failing test  │
│    ├─ Read requirements      │
│    ├─ Define expectations    │
│    └─ pytest → FAIL          │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 2. GREEN: Make it pass       │
│    ├─ Minimal implementation │
│    ├─ Focus on passing test  │
│    └─ pytest → PASS          │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 3. REFACTOR: Improve code    │
│    ├─ Clean up logic         │
│    ├─ Apply patterns         │
│    └─ pytest → STILL PASS    │
└──────────┬───────────────────┘
           ↓
         REPEAT
```

## Test Types

### 1. Unit Tests (Fast, Isolated)

**Characteristics:**
- No I/O operations
- Use mocks for dependencies
- Test single units in isolation
- Run in <0.5s

**Coverage requirements:**
- Domain: 100%
- Application: 90%

**Location:** `tests/test_*.py` (no `_integration` suffix)

**Example:**
```python
# tests/test_salary_analyzer.py
import pytest
from unittest.mock import MagicMock

def test_detect_salary():
    """Unit test with mocked data"""
    analyzer = SalaryAnalyzer()
    mock_data = [{"amount": 50000, "description": "เงินเดือน"}]
    
    result = analyzer.detect(mock_data)
    
    assert result == 50000.0
```

**Run:**
```bash
pytest tests/ -v -m "not integration"
```

### 2. Integration Tests (Slower, Real Dependencies)

**Characteristics:**
- Real database/storage/PDF operations
- Requires Docker services
- Tests adapter implementations
- Run in 1-10s per test

**Coverage requirements:**
- Infrastructure: 70%

**Location:** `tests/test_*_integration.py`

**Marker:** `@pytest.mark.integration`

**Example:**
```python
# tests/test_database_integration.py
import pytest

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_save_to_real_db(db_connection):
    """Integration test with real PostgreSQL"""
    db = PostgresDatabase(connection_string=TEST_DB_URL)
    await db.connect()
    
    result = await db.save_analysis(...)
    
    assert isinstance(result, UUID)
```

**Run:**
```bash
# Start services
docker compose up -d db

# Set env var
export TEST_DATABASE_URL="postgresql://..."

# Run tests
pytest tests/ -v -m integration
```

## TDD Workflow Example

**Task: Implement salary detection**

### Step 1: Write Failing Test (RED)

```bash
# Create test file
cat > tests/test_salary_detector.py << 'EOF'
import pytest
from domain.services.salary_detector import SalaryDetector

def test_detect_with_keyword():
    """Test detection with 'เงินเดือน' keyword"""
    detector = SalaryDetector()
    transactions = [
        {"amount": 50000, "description": "เงินเดือน"},
        {"amount": 100, "description": "ค่าอาหาร"}
    ]
    
    result = detector.detect(transactions)
    
    assert result.amount == 50000
    assert result.confidence == "high"

def test_detect_without_keyword():
    """Test detection by pattern (early morning)"""
    detector = SalaryDetector()
    transactions = [
        {"amount": 45000, "description": "โอนเงิน", "time": "03:30"}
    ]
    
    result = detector.detect(transactions)
    
    assert result.amount == 45000
    assert result.confidence == "medium"
EOF

# Run test - should FAIL
pytest tests/test_salary_detector.py -v
```

**Expected output:**
```
FAILED: ModuleNotFoundError: No module named 'salary_detector'
```

### Step 2: Minimal Implementation (GREEN)

```bash
# Create minimal code to pass test
mkdir -p src/domain/services
cat > src/domain/services/salary_detector.py << 'EOF'
class DetectionResult:
    def __init__(self, amount, confidence):
        self.amount = amount
        self.confidence = confidence

class SalaryDetector:
    def detect(self, transactions):
        # Minimal logic to pass tests
        for tx in transactions:
            if "เงินเดือน" in tx.get("description", ""):
                return DetectionResult(tx["amount"], "high")
            if tx.get("time", "").startswith("03:"):
                return DetectionResult(tx["amount"], "medium")
        return DetectionResult(0, "none")
EOF

# Run test - should PASS
pytest tests/test_salary_detector.py -v
```

**Expected output:**
```
test_detect_with_keyword PASSED
test_detect_without_keyword PASSED
=================== 2 passed in 0.05s ===================
```

### Step 3: Refactor (REFACTOR)

```python
# Improve implementation
class SalaryDetector:
    SALARY_KEYWORDS = ["เงินเดือน", "salary", "payroll"]
    EARLY_MORNING_START = "03:"
    
    def detect(self, transactions):
        """Detect salary with improved algorithm"""
        candidates = []
        
        for tx in transactions:
            score = 0
            description = tx.get("description", "")
            
            # Check keywords
            if any(kw in description for kw in self.SALARY_KEYWORDS):
                score += 10
            
            # Check timing
            if tx.get("time", "").startswith(self.EARLY_MORNING_START):
                score += 5
            
            if score > 0:
                candidates.append((tx["amount"], score))
        
        if not candidates:
            return DetectionResult(0, "none")
        
        # Select highest score
        amount, score = max(candidates, key=lambda x: x[1])
        confidence = "high" if score >= 10 else "medium"
        
        return DetectionResult(amount, confidence)
```

**Run tests again - should still PASS:**
```bash
pytest tests/test_salary_detector.py -v
```

### Step 4: Add More Tests

```python
def test_multiple_salary_transactions():
    """Test when multiple salaries exist"""
    detector = SalaryDetector()
    transactions = [
        {"amount": 50000, "description": "เงินเดือน มกราคม"},
        {"amount": 51000, "description": "เงินเดือน กุมภาพันธ์"},
    ]
    
    result = detector.detect(transactions)
    
    assert result.amount in [50000, 51000]
    assert result.confidence == "high"
```

## Commands Cheat Sheet

```bash
# Unit tests only (fast)
pytest tests/ -v -m "not integration"

# Integration tests only (requires Docker)
pytest tests/ -v -m integration

# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing

# Specific test file
pytest tests/test_salary_detector.py -v

# Specific test function
pytest tests/test_salary_detector.py::test_detect_with_keyword -v

# Watch mode (re-run on file changes)
ptw tests/ -- -v -m "not integration"
```

## Pre-Commit Checklist

Before marking task as complete:

- [ ] All unit tests written and passing
- [ ] Integration tests written (if applicable)
- [ ] Coverage ≥ minimum requirements
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No lint errors
- [ ] tasks.json updated with test results

## Coverage Requirements

| Layer           | Minimum | Test Type   |
|-----------------|---------|-------------|
| Domain          | 100%    | Unit        |
| Application     | 90%     | Unit        |
| Infrastructure  | 70%     | Integration |
| API             | 80%     | E2E + Unit  |

**Check coverage:**
```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Common Mistakes to Avoid

❌ **Writing implementation before tests**
✅ Write test first → See it fail → Implement

❌ **Testing implementation details**
✅ Test behavior and outcomes

❌ **Large tests covering multiple features**
✅ Small, focused tests (one assertion per test ideally)

❌ **Skipping integration tests**
✅ Test both mocked (unit) and real (integration)

❌ **Not running tests before commit**
✅ Always run full test suite

## TDD Benefits

1. **Better design** - Forces you to think about API first
2. **Documentation** - Tests show how to use the code
3. **Confidence** - Know when code works and when it breaks
4. **Refactoring safety** - Change code without fear
5. **Regression prevention** - Old bugs don't come back

## Resources

- Workflow: `.github/ai-instructions/01-WORKFLOW.md`
- Development: `.github/ai-instructions/04-DEVELOPMENT.md`
- pytest docs: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

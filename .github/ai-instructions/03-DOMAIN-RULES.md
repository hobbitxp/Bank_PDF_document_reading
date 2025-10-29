# Domain Rules

**Read this for: Domain logic, business rules, Thai banking context**

## Thai Banking Context

### Language & Character Encoding

**UTF-8 Support:**
- All strings must support Thai characters
- File encoding: UTF-8 with BOM optional
- Python string literals: Use `"สวัสดี"` directly

**Common Thai Terms:**
```python
# Names
THAI_TITLES = ["นาย", "นาง", "นางสาว", "ด.ช.", "ด.ญ."]

# Banking terms
"เงินเดือน"  # Salary
"โอน"         # Transfer
"ฝาก"         # Deposit
"ถอน"         # Withdraw
"ยอดเงิน"     # Balance
"รายการ"      # Transaction
```

### Number Format

**Thai Format:**
- Uses commas for thousands: `84,456.01`
- Decimal separator: `.` (period)
- Currency: THB or ฿ or บาท

**Parsing Pattern:**
```python
import re

# Match Thai number format
pattern = r"(\d{1,3}(?:,\d{3})*\.\d{2})"
amount = "84,456.01"
matches = re.findall(pattern, amount)
# Result: ["84,456.01"]

# Convert to float
value = float(matches[0].replace(",", ""))
# Result: 84456.01
```

### Name Patterns

**Format:** `[Title] [FirstName] [LastName]`

**Examples:**
```
นายสมชาย ใจดี
นางสาวสมหญิง รักษ์ดี
นางพิมพ์ใจ มั่นคง
```

**Masking:**
```python
# Original: นายสมชาย ใจดี
# Masked: NAME_001

# Original: นางสาวสมหญิง รักษ์ดี
# Masked: NAME_002
```

### Account Number Format

**Thai Bank Account Patterns:**
```
KBank:  xxx-x-xxxxx-x  (12 digits)
SCB:    xxx-x-xxxxx-x  (12 digits)
BBL:    xxx-x-xxxxx-x  (10 digits)
TMB:    xxx-x-xxxxx-x  (10 digits)
```

**Masking:**
```python
# Original: 123-4-56789-0
# Masked: ACCOUNT_001
```

### Phone Number Format

**Thai Mobile Pattern:**
```
0xx-xxx-xxxx
08x-xxx-xxxx  # Most common
09x-xxx-xxxx
06x-xxx-xxxx
```

**Masking:**
```python
# Original: 081-234-5678
# Masked: PHONE_001
```

## PDPA Compliance

### Personal Data Protection

**PDPA (Personal Data Protection Act):**
- Thai equivalent of GDPR
- Requires consent for personal data processing
- Mandates data masking for storage/transmission

### 6 Pattern Types for Masking

**1. Thai ID (13 digits):**
```python
pattern = r"\b\d{1}-\d{4}-\d{5}-\d{2}-\d{1}\b"
# Example: 1-2345-67890-12-3 → THAI_ID_001
```

**2. Account Numbers:**
```python
pattern = r"\b\d{3}-\d{1}-\d{5}-\d{1}\b"
# Example: 123-4-56789-0 → ACCOUNT_001
```

**3. Thai Names:**
```python
pattern = r"(นาย|นาง|นางสาว|ด\.ช\.|ด\.ญ\.)\s+[\u0E00-\u0E7F]+\s+[\u0E00-\u0E7F]+"
# Example: นายสมชาย ใจดี → NAME_001
```

**4. Phone Numbers:**
```python
pattern = r"\b0\d{1,2}-\d{3}-\d{4}\b"
# Example: 081-234-5678 → PHONE_001
```

**5. Addresses:**
```python
pattern = r"บ้านเลขที่\s+\d+.*?(จังหวัด|กรุงเทพ)"
# Example: บ้านเลขที่ 123 ถนนสุขุมวิท กรุงเทพ → ADDRESS_001
```

**6. Emails:**
```python
pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
# Example: user@example.com → EMAIL_001
```

### Output Files

**Two-File System:**

**1. Masked File (`*_masked.json`):**
- Contains masked data
- Safe to share/transmit
- Can be sent to APIs
- Can be committed to git (with caution)

**2. Mapping File (`*_mapping.json`):**
- Contains unmasked → masked mappings
- SECRET - must stay local
- NEVER send to APIs
- NEVER commit to git
- Add to .gitignore

**Example:**
```json
// statement_masked.json (Safe)
{
  "transactions": [
    {
      "description": "โอนเงินจาก NAME_001",
      "account": "ACCOUNT_001",
      "amount": 50000
    }
  ]
}

// statement_mapping.json (SECRET)
{
  "NAME_001": "นายสมชาย ใจดี",
  "ACCOUNT_001": "123-4-56789-0"
}
```

### Masking Rules

**CRITICAL:**
- ❌ NEVER commit `*_mapping.json` files
- ❌ NEVER send mapping files to external APIs
- ❌ NEVER log unmasked data
- ✅ Always use masked files for analysis
- ✅ Keep mapping files local only
- ✅ Delete mapping files after use (optional)

## Salary Detection Algorithm

### Multi-Factor Scoring System

**Score Calculation:**
```python
score = 0

# Factor 1: Keyword match (+5)
if has_keyword(["เงินเดือน", "BSD02", "Payroll"]):
    score += 5

# Factor 2: Employer match (+3)
if payer == expected_employer:
    score += 3

# Factor 3: Time heuristic (+2)
if is_early_morning(time):  # 01:00-06:00 AM
    score += 2

# Factor 4: Amount clustering (+3)
if in_cluster(amount, threshold=0.03):  # ±3%
    score += 3

# Factor 5: Not excluded (+2)
if not is_excluded(description):
    score += 2

# Maximum score: 15 points
```

### Exclusion Rules

**Excluded Channels:**
```python
EXCLUSION_KEYWORDS = [
    "ทรูมันนี่",      # TrueMoney wallet
    "พร้อมเพย์",      # PromptPay
    "เงินสด",          # Cash
    "เช็ค",            # Check
    "ATM ถอน",         # ATM withdrawal
    "7-11",            # Convenience store
    "โลตัส",           # Retail store
]
```

**Excluded Transaction Types:**
```python
def is_excluded(transaction: Transaction) -> bool:
    desc = transaction.description.lower()
    return any(keyword in desc for keyword in EXCLUSION_KEYWORDS)
```

### Clustering Algorithm

**Purpose:** Find recurring payments with similar amounts

**Algorithm:**
```python
def cluster_transactions(transactions: list[Transaction], threshold: float = 0.03):
    """
    Cluster transactions by amount (±3%)
    
    Args:
        transactions: List of credit transactions
        threshold: Percentage threshold (0.03 = 3%)
    
    Returns:
        dict: {cluster_id: [transactions]}
    """
    clusters = {}
    cluster_id = 0
    
    for tx in transactions:
        assigned = False
        
        for cid, cluster in clusters.items():
            avg = sum(t.amount for t in cluster) / len(cluster)
            
            if abs(tx.amount - avg) / avg <= threshold:
                cluster.append(tx)
                tx.cluster_id = cid
                assigned = True
                break
        
        if not assigned:
            clusters[cluster_id] = [tx]
            tx.cluster_id = cluster_id
            cluster_id += 1
    
    return clusters
```

### Thai Tax Model

**Progressive Tax Brackets (2024):**

| Taxable Income (THB/year) | Rate |
|---------------------------|------|
| 0 - 150,000               | 0%   |
| 150,001 - 300,000         | 5%   |
| 300,001 - 500,000         | 10%  |
| 500,001 - 750,000         | 15%  |
| 750,001 - 1,000,000       | 20%  |
| 1,000,001 - 2,000,000     | 25%  |
| 2,000,001 - 5,000,000     | 30%  |
| 5,000,001+                | 35%  |

**Social Security (SSO):**
```python
SSO_RATE = 0.05  # 5% of gross salary
SSO_CAP = 750    # Maximum 750 THB/month
```

**Deductions:**
```python
PERSONAL_ALLOWANCE = 60_000      # THB/year
EMPLOYMENT_EXPENSE_CAP = 100_000 # THB/year (50% of gross, max 100k)
```

**Calculation Function:**
```python
def thai_monthly_net_from_gross(
    gross: float,
    pvd_rate: float = 0.0,
    extra_deductions_yearly: float = 0.0
) -> tuple[float, float, float]:
    """
    Calculate net salary from gross (Thai tax system)
    
    Args:
        gross: Monthly gross salary (THB)
        pvd_rate: Provident fund rate (0.0-0.15)
        extra_deductions_yearly: Extra deductions (insurance, etc.)
    
    Returns:
        (net_salary, monthly_tax, monthly_sso)
    """
    # Annual gross
    annual_gross = gross * 12
    
    # SSO (5% capped at 750/month)
    monthly_sso = min(gross * 0.05, 750)
    annual_sso = monthly_sso * 12
    
    # Provident fund
    annual_pvd = annual_gross * pvd_rate
    
    # Employment expense (50% of gross, max 100k)
    employment_expense = min(annual_gross * 0.5, 100_000)
    
    # Taxable income
    taxable_income = annual_gross - annual_sso - annual_pvd - PERSONAL_ALLOWANCE - employment_expense - extra_deductions_yearly
    
    # Progressive tax
    annual_tax = calculate_progressive_tax(taxable_income)
    monthly_tax = annual_tax / 12
    
    # Net salary
    net_salary = gross - monthly_tax - monthly_sso - (annual_pvd / 12)
    
    return (net_salary, monthly_tax, monthly_sso)


def calculate_progressive_tax(taxable_income: float) -> float:
    """Calculate progressive tax"""
    if taxable_income <= 0:
        return 0.0
    
    brackets = [
        (150_000, 0.00),
        (150_000, 0.05),  # 150k-300k
        (200_000, 0.10),  # 300k-500k
        (250_000, 0.15),  # 500k-750k
        (250_000, 0.20),  # 750k-1M
        (1_000_000, 0.25),  # 1M-2M
        (3_000_000, 0.30),  # 2M-5M
        (float('inf'), 0.35)  # 5M+
    ]
    
    tax = 0.0
    remaining = taxable_income
    
    for bracket_size, rate in brackets:
        if remaining <= 0:
            break
        
        taxable_in_bracket = min(remaining, bracket_size)
        tax += taxable_in_bracket * rate
        remaining -= taxable_in_bracket
    
    return tax
```

## Domain Entity Design

### Transaction Entity

**Rich Domain Model:**
```python
# domain/entities/transaction.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Transaction:
    """
    Transaction entity (Value Object pattern)
    
    Business Rules:
    - Can check if excluded (e-wallet, cash, check)
    - Can check if has salary keywords
    - Can check if in payroll time window
    """
    
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
        """Check if transaction should be excluded from salary detection"""
        exclusion_keywords = [
            "ทรูมันนี่", "พร้อมเพย์", "เงินสด", "เช็ค",
            "ATM ถอน", "7-11", "โลตัส"
        ]
        return any(kw in self.description for kw in exclusion_keywords)
    
    def has_keyword(self, keywords: list[str]) -> bool:
        """Check if description contains any keyword"""
        return any(kw in self.description for kw in keywords)
    
    def is_early_morning(self) -> bool:
        """Check if transaction is in payroll time window (01:00-06:00)"""
        if not self.time:
            return False
        
        try:
            hour = int(self.time.split(":")[0])
            return 1 <= hour <= 6
        except (ValueError, IndexError):
            return False
    
    def calculate_score(
        self,
        salary_keywords: list[str],
        expected_employer: Optional[str],
        cluster_bonus: bool = False
    ) -> int:
        """Calculate salary detection score"""
        score = 0
        
        # Keyword match
        if self.has_keyword(salary_keywords):
            score += 5
        
        # Employer match
        if expected_employer and self.payer == expected_employer:
            score += 3
        
        # Time heuristic
        if self.is_early_morning():
            score += 2
        
        # Cluster bonus
        if cluster_bonus:
            score += 3
        
        # Not excluded
        if not self.is_excluded():
            score += 2
        
        return score
```

**Key Principles:**
- Business logic in domain methods
- No framework dependencies (no FastAPI, boto3, pandas)
- Immutable where possible (frozen=False for scoring)
- Rich model (not anemic)

### Statement Entity

**Aggregate Root:**
```python
# domain/entities/statement.py
from dataclasses import dataclass
from typing import List

@dataclass
class Statement:
    """
    Statement entity (Aggregate Root)
    
    Responsibilities:
    - Contains transactions
    - Provides filtered views
    - Enforces invariants
    """
    
    user_id: str
    statement_id: str
    transactions: List[Transaction]
    pages_processed: int
    bank_name: Optional[str] = None
    
    def get_credit_transactions(self) -> List[Transaction]:
        """Factory method: Get only credit transactions"""
        return [tx for tx in self.transactions if tx.is_credit]
    
    def get_debit_transactions(self) -> List[Transaction]:
        """Factory method: Get only debit transactions"""
        return [tx for tx in self.transactions if not tx.is_credit]
    
    def get_transactions_by_page(self, page: int) -> List[Transaction]:
        """Get transactions from specific page"""
        return [tx for tx in self.transactions if tx.page == page]
    
    def total_credits(self) -> float:
        """Calculate total credit amount"""
        return sum(tx.amount for tx in self.get_credit_transactions())
    
    def total_debits(self) -> float:
        """Calculate total debit amount"""
        return sum(tx.amount for tx in self.get_debit_transactions())
```

### SalaryAnalysis Entity

**Result Object:**
```python
# domain/entities/salary_analysis.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SalaryAnalysis:
    """
    Salary analysis result entity
    
    Contains:
    - Detected salary amount
    - Confidence level
    - Analysis metadata
    """
    
    detected_amount: float
    confidence: str  # "high", "medium", "low"
    transactions_analyzed: int
    clusters_found: int
    top_candidates_count: int
    matches_expected: Optional[bool] = None
    difference: Optional[float] = None
    difference_percentage: Optional[float] = None
    
    def is_high_confidence(self) -> bool:
        """Check if analysis has high confidence"""
        return self.confidence == "high"
    
    def matches_expected_salary(self, expected: float, tolerance: float = 0.05) -> bool:
        """Check if detected amount matches expected salary within tolerance"""
        if expected == 0:
            return False
        
        diff_pct = abs(self.detected_amount - expected) / expected
        return diff_pct <= tolerance
```

## Next Steps

**For architecture patterns:**
→ Read 02-ARCHITECTURE.md

**For running/testing:**
→ Read 04-DEVELOPMENT.md

**For debugging:**
→ Read 05-COMMON-ISSUES.md

**For code standards:**
→ Read 06-CODE-STANDARDS.md

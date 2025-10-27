"""
Infrastructure Adapter: Thai Salary Analyzer
Implements ISalaryAnalyzer with 6-month recurring pattern detection
"""

from typing import Optional, Dict, Any, List
from collections import defaultdict
import statistics
import re

from application.ports.salary_analyzer import ISalaryAnalyzer
from domain.entities.statement import Statement
from domain.entities.salary_analysis import SalaryAnalysis
from domain.entities.transaction import Transaction
from domain.enums import IncomeType


class ThaiSalaryAnalyzer(ISalaryAnalyzer):
    """Thai salary analysis with 6-month recurring pattern detection"""
    
    # Thai tax brackets (annual income in THB)
    TAX_BRACKETS = [
        (0, 150_000, 0.0),
        (150_000, 300_000, 0.05),
        (300_000, 500_000, 0.10),
        (500_000, 750_000, 0.15),
        (750_000, 1_000_000, 0.20),
        (1_000_000, 2_000_000, 0.25),
        (2_000_000, 5_000_000, 0.30),
        (5_000_000, float('inf'), 0.35)
    ]
    
    # Constants
    SSO_RATE = 0.05
    SSO_MAX = 750.0  # THB per month
    PERSONAL_ALLOWANCE = 60_000  # Annual
    EMPLOYMENT_EXPENSE_MAX = 100_000  # Annual
    
    # 6-Month Pattern Detection Parameters
    MIN_MONTHS_REQUIRED = 3  # At least 3 months (support shorter statements)
    IDEAL_MONTHS_REQUIRED = 5  # For high confidence
    AMOUNT_STABILITY_THRESHOLD = 0.05  # ±5%
    
    # Scoring weights (6-month pattern)
    RECURRENCE_SCORE = 6
    SOURCE_CONSISTENCY_SCORE = 5
    AMOUNT_STABILITY_SCORE = 4
    PAYROLL_TIME_SCORE = 2
    KEYWORD_SCORE = 2
    NOT_EXCLUDED_SCORE = 1
    
    # Keyword patterns
    SALARY_KEYWORDS = [
        "เงินเดือน", "BSD02", "Payroll", "SALARY", "SAL",
        "รับโอนเงิน", "เงินโอนเข้า", "IORSDT"
    ]
    
    # Exclusion patterns
    EXCLUSION_PATTERNS = [
        "truemoney", "wallet", "ทรูมันนี่",
        "ถอนเงิน", "เช็ค", "check", "โอนเงินออก", "จ่าย"
    ]
    
    def analyze(
        self, 
        statement: Statement,
        expected_gross: Optional[float] = None,
        employer: Optional[str] = None,
        pvd_rate: float = 0.0,
        extra_deductions: float = 0.0,
        income_type: Optional[IncomeType] = None
    ) -> SalaryAnalysis:
        """
        Analyze statement for income detection
        
        Args:
            statement: Bank statement with transactions
            expected_gross: Expected income (optional)
            employer: Employer name for salaried (optional)
            pvd_rate: PVD rate for salaried (optional)
            extra_deductions: Extra deductions for salaried (optional)
            income_type: Income type (SALARIED or SELF_EMPLOYED)
                        If None, auto-detect (default: SALARIED)
        
        Returns:
            SalaryAnalysis with income_type field
        """
        
        credits = statement.get_credit_transactions()
        
        # Auto-detect or use provided income_type
        if income_type is None:
            income_type = IncomeType.SALARIED  # Default
        
        # Route to appropriate analyzer
        if income_type == IncomeType.SELF_EMPLOYED:
            return self._calculate_self_employed_income(credits, expected_gross)
        
        # Original salaried logic below
        # 1) Detect monthly salary net pattern
        detected = self._detect_monthly_salary_net(credits, employer)
        
        months_detected = 0
        rejection_reason = None
        approved = False
        
        if not detected:
            rejection_reason = "No recurring salary pattern detected"
            if expected_gross:
                estimated_gross = expected_gross
                confidence = "low"
            else:
                return SalaryAnalysis(
                    detected_amount=0.0,
                    confidence="low",
                    income_type=IncomeType.SALARIED,
                    transactions_analyzed=len(credits),
                    clusters_found=0,
                    best_candidates=[],
                    all_scored_transactions=[],
                    expected_salary=expected_gross,
                    months_detected=0,
                    approved=False,
                    rejection_reason=rejection_reason
                )
        else:
            # 2) Convert net → gross
            months_detected = detected["months_detected"]
            monthly_net = detected["monthly_net_median"]
            estimated_gross = self._gross_from_net(monthly_net, pvd_rate, extra_deductions)
            
            # 3) Verify calculation
            annual_gross = estimated_gross * 12
            taxable = self._calculate_taxable_income(annual_gross, pvd_rate, extra_deductions)
            annual_tax = self._calculate_tax(taxable)
            monthly_tax = annual_tax / 12
            monthly_sso = min(estimated_gross * self.SSO_RATE, self.SSO_MAX)
            monthly_pvd = estimated_gross * pvd_rate
            net_again = estimated_gross - monthly_tax - monthly_sso - monthly_pvd
            
            # 4) Calculate confidence
            diff = abs(net_again - monthly_net) / max(1.0, monthly_net)
            months = detected["months_detected"]
            
            if months >= self.IDEAL_MONTHS_REQUIRED and diff <= 0.03:
                confidence = "high"
            elif months >= self.MIN_MONTHS_REQUIRED and diff <= 0.06:
                confidence = "medium"
            else:
                confidence = "low"
        
        # 5) Determine approval status
        # Rule 1: Must have at least 6 months of data
        if months_detected < 6:
            approved = False
            rejection_reason = f"Insufficient data: only {months_detected} months detected (required: 6)"
        # Rule 2: Must match expected salary (if provided)
        elif expected_gross is not None:
            matches = abs(estimated_gross - expected_gross) < 5000
            if not matches:
                approved = False
                diff_amount = estimated_gross - expected_gross
                diff_pct = (diff_amount / expected_gross) * 100
                rejection_reason = f"Salary mismatch: detected {estimated_gross:.2f} vs expected {expected_gross:.2f} (diff: {diff_pct:.1f}%)"
            else:
                approved = True
        else:
            # No expected salary to compare - approve based on confidence
            approved = confidence in ["high", "medium"]
            if not approved:
                rejection_reason = "Low confidence in detection"
        
        return SalaryAnalysis(
            detected_amount=round(estimated_gross, 2),
            confidence=confidence,
            income_type=IncomeType.SALARIED,
            transactions_analyzed=len(credits),
            clusters_found=1 if detected else 0,
            best_candidates=detected["transactions"][:10] if detected else [],
            all_scored_transactions=[],
            expected_salary=expected_gross,
            months_detected=months_detected,
            approved=approved,
            rejection_reason=rejection_reason
        )
    
    def _calculate_self_employed_income(
        self,
        credits: List[Transaction],
        expected_gross: Optional[float] = None
    ) -> SalaryAnalysis:
        """
        Calculate average income for self-employed/freelancers
        Strategy: Sum all credits for 6 months, divide by 6
        """
        # Filter out summary lines (รวมฝากเงิน, รวมถอนเงิน, etc.)
        filtered_credits = [
            tx for tx in credits 
            if tx.date and "รวม" not in tx.description
        ]
        
        print(f"[SELF_EMPLOYED] Analyzing {len(filtered_credits)} credit transactions (filtered from {len(credits)} total)")
        
        # Group by month
        monthly_totals = defaultdict(float)
        monthly_count = defaultdict(int)
        
        for tx in filtered_credits:
            # Extract year-month from DD/MM/YYYY or DD/MM/YY or DD-MM-YY (KBANK format)
            # Support both "/" and "-" separators
            date_str = tx.date.replace("-", "/")  # Normalize to slash separator
            parts = date_str.split("/")
            
            if len(parts) != 3:
                print(f"[SELF_EMPLOYED] Skipping invalid date format: {tx.date}")
                continue
                
            day, month, year = parts
            
            # Convert 2-digit Thai Buddhist year to 4-digit
            if len(year) == 2:
                year_int = int(year)
                # Assume 68 = 2568 (2025 AD)
                if year_int >= 50:  # 50-99 = 2550-2599
                    year = f"25{year}"
                else:  # 00-49 = 2600-2649
                    year = f"26{year}"
            
            month_key = f"{year}-{month.zfill(2)}"  # YYYY-MM
            monthly_totals[month_key] += tx.amount
            monthly_count[month_key] += 1
        
        print(f"[SELF_EMPLOYED] Grouped into {len(monthly_totals)} months: {dict(monthly_totals)}")
        
        months_detected = len(monthly_totals)
        
        if months_detected == 0:
            return SalaryAnalysis(
                detected_amount=0.0,
                confidence="low",
                income_type=IncomeType.SELF_EMPLOYED,
                transactions_analyzed=len(credits),
                clusters_found=0,
                best_candidates=[],
                expected_salary=expected_gross,
                months_detected=0,
                approved=False,
                rejection_reason="No dated transactions found for averaging"
            )
        
        # Calculate average
        total_income = sum(monthly_totals.values())
        average_monthly = total_income / months_detected
        
        # Determine confidence
        if months_detected >= 6:
            confidence = "high"
        elif months_detected >= 4:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Approval logic
        approved = False
        rejection_reason = None
        
        if months_detected < 6:
            rejection_reason = f"Insufficient data: only {months_detected} months detected (required: 6)"
        elif expected_gross is not None:
            matches = abs(average_monthly - expected_gross) < 5000
            if not matches:
                diff_amount = average_monthly - expected_gross
                diff_pct = (diff_amount / expected_gross) * 100
                rejection_reason = f"Income mismatch: detected {average_monthly:.2f} vs expected {expected_gross:.2f} (diff: {diff_pct:.1f}%)"
            else:
                approved = True
        else:
            approved = confidence == "high"
            if not approved:
                rejection_reason = "Insufficient months for approval"
        
        return SalaryAnalysis(
            detected_amount=round(average_monthly, 2),
            confidence=confidence,
            income_type=IncomeType.SELF_EMPLOYED,
            transactions_analyzed=len(credits),
            clusters_found=months_detected,
            best_candidates=credits[:10],  # Show sample transactions
            expected_salary=expected_gross,
            months_detected=months_detected,
            approved=approved,
            rejection_reason=rejection_reason
        )
    
    def _normalize_source(self, tx: Transaction) -> str:
        """Normalize transaction source for grouping"""
        if tx.payer:
            # Keep Thai characters, remove only special chars
            # Thai Unicode range: \u0E00-\u0E7F
            normalized = re.sub(r'[^\u0E00-\u0E7Fa-zA-Z0-9]', '', tx.payer.upper())
            # If result is empty after normalization, use original
            if not normalized:
                normalized = "UNKNOWN"
            print(f"[NORMALIZE_SOURCE] payer='{tx.payer}' → '{normalized}' (amt: {tx.amount})")
            return normalized
        
        desc = tx.description.upper()
        
        # Extract pattern codes (BSD02, IORSDT, etc.)
        pattern_match = re.search(r'\(([\w\d]+)\)', desc)
        if pattern_match:
            return pattern_match.group(1)
        
        # Clean and extract meaningful words
        desc = re.sub(r'(รับโอน|เงินโอน|โอนเข้า|TRANSFER|RECEIVE)', '', desc)
        words = desc.split()
        for word in words:
            if len(word) >= 3 and not re.match(r'^[\d\-/:.]+$', word):
                return re.sub(r'[^a-zA-Z0-9]', '', word)
        
        return "UNKNOWN"
    
    def _group_by_source(self, credits: List[Transaction]) -> Dict[str, List[Transaction]]:
        """Group transactions by normalized source"""
        groups = defaultdict(list)
        for tx in credits:
            source = self._normalize_source(tx)
            groups[source].append(tx)
        return dict(groups)
    
    def _amount_stability(self, amounts: List[float]) -> float:
        """Calculate stability using MAD (Median Absolute Deviation)"""
        if len(amounts) < 2:
            return 0.0
        
        median = statistics.median(amounts)
        if median == 0:
            return float('inf')
        
        deviations = [abs(a - median) for a in amounts]
        mad = statistics.median(deviations)
        
        return mad / median if median > 0 else float('inf')
    
    def _is_payroll_time(self, tx: Transaction) -> bool:
        """Check if transaction occurred during payroll hours (00:00-06:00)"""
        if not tx.time:
            return False
        try:
            hour = int(tx.time.split(":")[0])
            return 0 <= hour <= 6
        except:
            return False
    
    def _score_salary_group(
        self,
        transactions: List[Transaction],
        employer: Optional[str] = None
    ) -> int:
        """Score a group of transactions for salary likelihood"""
        score = 0
        
        # Recurrence
        if len(transactions) >= 6:
            score += self.RECURRENCE_SCORE
        elif len(transactions) >= self.IDEAL_MONTHS_REQUIRED:
            score += self.RECURRENCE_SCORE - 1
        elif len(transactions) >= self.MIN_MONTHS_REQUIRED:
            score += self.RECURRENCE_SCORE - 2
        
        # Source consistency (implicit)
        score += self.SOURCE_CONSISTENCY_SCORE
        
        # Amount stability
        amounts = [tx.amount for tx in transactions]
        stability = self._amount_stability(amounts)
        if stability <= 0.03:
            score += self.AMOUNT_STABILITY_SCORE
        elif stability <= self.AMOUNT_STABILITY_THRESHOLD:
            score += self.AMOUNT_STABILITY_SCORE - 1
        
        # Amount magnitude - NEW: Bonus for higher amounts (likely salary)
        avg_amount = sum(amounts) / len(amounts) if amounts else 0
        if avg_amount >= 50000:  # Likely salary range
            score += 8  # High bonus
        elif avg_amount >= 20000:
            score += 5  # Medium bonus
        elif avg_amount >= 10000:
            score += 3  # Small bonus
        elif avg_amount < 1000:
            score -= 5  # Penalty for very small amounts (likely not salary)
        
        # Payroll time
        payroll_count = sum(1 for tx in transactions if self._is_payroll_time(tx))
        if payroll_count >= len(transactions) * 0.5:
            score += self.PAYROLL_TIME_SCORE
        
        # Keywords
        if any(tx.has_keyword(self.SALARY_KEYWORDS) for tx in transactions):
            score += self.KEYWORD_SCORE
        
        # Not excluded
        if all(not tx.is_excluded(self.EXCLUSION_PATTERNS) for tx in transactions):
            score += self.NOT_EXCLUDED_SCORE
        
        # Employer
        if employer and any(employer.lower() in tx.description.lower() for tx in transactions):
            score += 3
        
        return score
    
    def _detect_monthly_salary_net(
        self,
        credits: List[Transaction],
        employer: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Detect monthly salary pattern using 6-month logic"""
        source_groups = self._group_by_source(credits)
        
        print(f"\n[SALARY_DETECT] Total sources: {len(source_groups)}")
        for src, txs in list(source_groups.items())[:10]:
            print(f"  - {src}: {len(txs)} txs, amounts: {[tx.amount for tx in txs[:3]]}")
        
        best_group = None
        best_score = 0
        
        for source, txs in source_groups.items():
            if len(txs) < self.MIN_MONTHS_REQUIRED:
                continue
            
            # Count unique months from transactions
            unique_months = set()
            for tx in txs:
                if tx.date:
                    match = re.search(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', tx.date)
                    if match:
                        day, month, year = match.groups()
                        if year:
                            if len(year) == 2:
                                year_int = int(year)
                                if year_int >= 50:
                                    year = f"25{year}"
                                else:
                                    year = f"26{year}"
                            month_key = f"{year}-{month.zfill(2)}"
                            unique_months.add(month_key)
            
            months_detected = len(unique_months)
            
            score = self._score_salary_group(txs, employer)
            print(f"[SCORE] source='{source}' txs={len(txs)} months={months_detected} score={score:.2f}")
            
            if score > best_score:
                best_score = score
                best_group = {
                    "source": source,
                    "transactions": txs,
                    "score": score,
                    "months_detected": months_detected  # Count unique months, not transactions
                }
        
        if not best_group:
            return None
        
        amounts = [tx.amount for tx in best_group["transactions"]]
        best_group["monthly_net_median"] = statistics.median(amounts)
        
        print(f"\n[BEST_GROUP] source='{best_group['source']}' months={best_group['months_detected']} median={best_group['monthly_net_median']:.2f}")
        
        return best_group
    
    def _gross_from_net(
        self,
        monthly_net: float,
        pvd_rate: float = 0.0,
        extra_deductions: float = 0.0,
        max_iterations: int = 50
    ) -> float:
        """Inverse: Find gross that produces given net (bisection search)"""
        lower_gross = monthly_net
        upper_gross = monthly_net * 2.0
        tolerance = 10.0
        
        for _ in range(max_iterations):
            mid_gross = (lower_gross + upper_gross) / 2.0
            
            annual_gross = mid_gross * 12
            taxable = self._calculate_taxable_income(annual_gross, pvd_rate, extra_deductions)
            annual_tax = self._calculate_tax(taxable)
            monthly_tax = annual_tax / 12
            monthly_sso = min(mid_gross * self.SSO_RATE, self.SSO_MAX)
            monthly_pvd = mid_gross * pvd_rate
            
            calculated_net = mid_gross - monthly_tax - monthly_sso - monthly_pvd
            
            if abs(calculated_net - monthly_net) < tolerance:
                return mid_gross
            
            if calculated_net > monthly_net:
                upper_gross = mid_gross
            else:
                lower_gross = mid_gross
        
        return (lower_gross + upper_gross) / 2.0
    
    def _calculate_taxable_income(
        self,
        annual_gross: float,
        pvd_rate: float,
        extra_deductions: float
    ) -> float:
        """Calculate annual taxable income"""
        pvd_deduction = annual_gross * pvd_rate
        employment_expense = min(annual_gross * 0.5, self.EMPLOYMENT_EXPENSE_MAX)
        
        total_deductions = (
            self.PERSONAL_ALLOWANCE +
            employment_expense +
            pvd_deduction +
            extra_deductions
        )
        
        taxable = annual_gross - total_deductions
        return max(taxable, 0.0)
    
    def _calculate_tax(self, taxable_income: float) -> float:
        """Calculate annual tax using Thai progressive brackets"""
        total_tax = 0.0
        remaining = taxable_income
        
        for lower, upper, rate in self.TAX_BRACKETS:
            if remaining <= 0:
                break
            
            bracket_amount = min(remaining, upper - lower)
            bracket_tax = bracket_amount * rate
            
            total_tax += bracket_tax
            remaining -= bracket_amount
        
        return total_tax

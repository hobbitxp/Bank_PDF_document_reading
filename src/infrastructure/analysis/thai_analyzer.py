"""
Infrastructure Adapter: Thai Salary Analyzer
Implements ISalaryAnalyzer with Thai tax model and clustering
"""

from typing import Optional, Dict, Any
from collections import defaultdict
from datetime import time

from application.ports.salary_analyzer import ISalaryAnalyzer
from domain.entities.statement import Statement
from domain.entities.salary_analysis import SalaryAnalysis
from domain.entities.transaction import Transaction


class ThaiSalaryAnalyzer(ISalaryAnalyzer):
    """Thai salary analysis with tax calculation and clustering"""
    
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
    
    # Scoring weights
    KEYWORD_SCORE = 5
    EMPLOYER_SCORE = 3
    TIME_SCORE = 2
    CLUSTER_SCORE = 3
    NOT_EXCLUDED_SCORE = 2
    
    # Keyword patterns for salary detection
    SALARY_KEYWORDS = [
        "เงินเดือน", "BSD02", "Payroll", "SALARY",
        "รับโอนเงิน", "เงินโอนเข้า"
    ]
    
    # Exclusion patterns
    EXCLUSION_PATTERNS = [
        "truemoney", "wallet", "ทรูมันนี่",
        "ถอนเงิน", "เช็ค", "check"
    ]
    
    def analyze(
        self, 
        statement: Statement,
        expected_gross: Optional[float] = None,
        employer: Optional[str] = None,
        pvd_rate: float = 0.0,
        extra_deductions: float = 0.0
    ) -> SalaryAnalysis:
        """Analyze statement for salary transactions"""
        
        # Get credit transactions only
        credits = statement.get_credit_transactions()
        
        # Score each transaction
        scored_transactions = []
        for tx in credits:
            score = self._calculate_score(tx, employer)
            tx.score = score
            scored_transactions.append(tx)
        
        # Cluster transactions by amount
        clusters = self._cluster_by_amount(scored_transactions)
        
        # Assign cluster IDs
        for tx in scored_transactions:
            for cluster_id, cluster_txs in clusters.items():
                if tx in cluster_txs:
                    tx.cluster_id = cluster_id
                    tx.score += self.CLUSTER_SCORE
                    break
        
        # Find top candidates (above median score)
        scores = [tx.score for tx in scored_transactions]
        median_score = sorted(scores)[len(scores) // 2] if scores else 0
        top_candidates = [tx for tx in scored_transactions if tx.score >= median_score]
        
        # Estimate gross salary
        estimated_gross = self._estimate_gross(top_candidates, expected_gross)
        
        # Calculate net from gross
        annual_gross = estimated_gross * 12
        
        # Tax calculation
        taxable_income = self._calculate_taxable_income(
            annual_gross, pvd_rate, extra_deductions
        )
        annual_tax = self._calculate_tax(taxable_income)
        monthly_tax = annual_tax / 12
        
        # SSO calculation
        monthly_sso = min(estimated_gross * self.SSO_RATE, self.SSO_MAX)
        
        # PVD calculation
        monthly_pvd = estimated_gross * pvd_rate
        
        # Net salary
        net_salary = estimated_gross - monthly_tax - monthly_sso - monthly_pvd
        
        # Confidence level
        confidence = self._calculate_confidence(
            top_candidates, estimated_gross, expected_gross
        )
        
        return SalaryAnalysis(
            detected_amount=round(estimated_gross, 2),
            confidence=confidence,
            transactions_analyzed=len(credits),
            clusters_found=len(clusters),
            best_candidates=top_candidates[:10],  # Top 10
            all_scored_transactions=scored_transactions,
            expected_salary=expected_gross
        )
    
    def _calculate_score(self, tx: Transaction, employer: Optional[str]) -> int:
        """Calculate salary likelihood score"""
        
        score = 0
        
        # Keyword match
        if tx.has_keyword(self.SALARY_KEYWORDS):
            score += self.KEYWORD_SCORE
        
        # Employer match
        if employer and employer.lower() in tx.description.lower():
            score += self.EMPLOYER_SCORE
        
        # Time heuristic (early morning payroll window)
        if tx.is_early_morning():
            score += self.TIME_SCORE
        
        # Not excluded
        if not tx.is_excluded(self.EXCLUSION_PATTERNS):
            score += self.NOT_EXCLUDED_SCORE
        
        return score
    
    def _cluster_by_amount(
        self, 
        transactions: list[Transaction],
        threshold: float = 0.03
    ) -> Dict[int, list[Transaction]]:
        """Cluster transactions by amount (±3% threshold)"""
        
        clusters = {}
        cluster_id = 1
        
        sorted_txs = sorted(transactions, key=lambda t: t.amount)
        
        for tx in sorted_txs:
            # Check if fits in existing cluster
            found_cluster = False
            for cid, cluster_txs in clusters.items():
                cluster_avg = sum(t.amount for t in cluster_txs) / len(cluster_txs)
                if abs(tx.amount - cluster_avg) / cluster_avg <= threshold:
                    clusters[cid].append(tx)
                    found_cluster = True
                    break
            
            # Create new cluster
            if not found_cluster and len(clusters) < 20:  # Limit clusters
                clusters[cluster_id] = [tx]
                cluster_id += 1
        
        # Filter clusters with multiple transactions
        return {cid: txs for cid, txs in clusters.items() if len(txs) >= 2}
    
    def _estimate_gross(
        self, 
        candidates: list[Transaction],
        expected: Optional[float]
    ) -> float:
        """Estimate gross salary from candidates"""
        
        if not candidates:
            return expected or 0.0
        
        # Use highest scored transaction as estimate
        top_tx = max(candidates, key=lambda t: t.score)
        estimated = top_tx.amount
        
        # If expected provided and close, use expected
        if expected:
            diff_pct = abs(estimated - expected) / expected
            if diff_pct <= 0.10:  # Within 10%
                return expected
        
        return estimated
    
    def _calculate_taxable_income(
        self,
        annual_gross: float,
        pvd_rate: float,
        extra_deductions: float
    ) -> float:
        """Calculate annual taxable income"""
        
        # Deductions
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
    
    def _calculate_confidence(
        self,
        candidates: list[Transaction],
        estimated: float,
        expected: Optional[float]
    ) -> str:
        """Calculate confidence level"""
        
        if not candidates:
            return "low"
        
        # Check match with expected
        if expected:
            diff_pct = abs(estimated - expected) / expected
            if diff_pct <= 0.05:
                return "high"
            elif diff_pct <= 0.15:
                return "medium"
            else:
                return "low"
        
        # Check based on candidate count and scores
        avg_score = sum(t.score for t in candidates) / len(candidates)
        
        if len(candidates) >= 3 and avg_score >= 8:
            return "high"
        elif len(candidates) >= 2 and avg_score >= 5:
            return "medium"
        else:
            return "low"

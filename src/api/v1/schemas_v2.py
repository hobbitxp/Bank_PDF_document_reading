"""
API Schemas V2: Enhanced response format for bank statement analysis
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PeriodSchema(BaseModel):
    """Statement period"""
    startDate: str = Field(..., description="Start date (YYYY-MM-DD)")
    endDate: str = Field(..., description="End date (YYYY-MM-DD)")


class StatementScoreSchema(BaseModel):
    """Statement quality score"""
    value: float = Field(..., ge=0.0, le=1.0, description="Score 0-1")
    version: str = Field(..., description="Scoring algorithm version")
    reasons: List[str] = Field(default_factory=list, description="Score factors")


class TransactionV2Schema(BaseModel):
    """Individual transaction"""
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., description="Transaction amount")
    type: str = Field(..., description="credit or debit")
    balanceAfter: Optional[float] = Field(None, description="Balance after transaction")
    channel: Optional[str] = Field(None, description="Transaction channel")
    counterparty: Optional[str] = Field(None, description="Counterparty name")
    category: Optional[str] = Field(None, description="Transaction category")


class SalaryCreditSchema(BaseModel):
    """Identified salary credit"""
    date: str = Field(..., description="Payment date (YYYY-MM-DD)")
    amount: float = Field(..., description="Salary amount")
    employerName: Optional[str] = Field(None, description="Employer name")
    payCycle: str = Field("monthly", description="Pay cycle: monthly, bi-weekly")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")


class MonthlySummarySchema(BaseModel):
    """Monthly summary"""
    month: str = Field(..., description="Month (YYYY-MM)")
    totalCredit: float = Field(..., description="Total credits")
    totalDebit: float = Field(..., description="Total debits")
    salaryCount: int = Field(..., description="Number of salary payments")
    cashDepositAmount: float = Field(0.0, description="Cash deposit amount")


class BankStatementSchema(BaseModel):
    """Bank statement details"""
    holderName: str = Field("", description="Account holder name (masked)")
    bankName: str = Field("", description="Bank name")
    accountName: str = Field("", description="Account name")
    accountNumberMasked: str = Field(..., description="Masked account number")
    accountType: str = Field("SAVING", description="Account type")
    period: PeriodSchema = Field(..., description="Statement period")
    totalMonths: int = Field(..., description="Total months covered")
    avgMonthlyIncome: float = Field(..., description="Average monthly income")
    avgSalary: float = Field(..., description="Average salary (if salaried)")
    missingMonths: List[str] = Field(default_factory=list, description="Missing months")
    totalCredit: float = Field(..., description="Total credits")
    totalDebit: float = Field(..., description="Total debits")
    language: str = Field("th", description="Statement language")
    ocrConfidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence")
    parsingConfidence: float = Field(..., ge=0.0, le=1.0, description="Parsing confidence")
    sourceFileName: str = Field(..., description="Source file name")
    sourceFileHash: str = Field(..., description="File hash (sha256)")
    pages: int = Field(..., description="Number of pages")
    mimeType: str = Field("application/pdf", description="MIME type")
    exportedAt: str = Field(..., description="Export timestamp (ISO 8601)")
    statementScore: StatementScoreSchema = Field(..., description="Statement quality score")
    transactions: List[TransactionV2Schema] = Field(default_factory=list, description="All transactions")
    salaryCredits: List[SalaryCreditSchema] = Field(default_factory=list, description="Identified salary credits")
    monthlySummaries: List[MonthlySummarySchema] = Field(default_factory=list, description="Monthly summaries")


class PayslipSchema(BaseModel):
    """Payslip information"""
    salary: float = Field(..., description="Gross salary")
    netSalary: float = Field(..., description="Net salary")
    employerName: str = Field(..., description="Employer name")
    paydate: str = Field(..., description="Payment date (YYYY-MM-DD)")


class AnalysisSummarySchema(BaseModel):
    """Overall analysis summary"""
    total_avg_monthly_income: float = Field(..., description="Total average monthly income")
    primary_income_source: str = Field(..., description="Primary income source")
    total_accounts: int = Field(1, description="Total accounts analyzed")


class MetadataSchema(BaseModel):
    """Processing metadata"""
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    ocr_version: str = Field("2.1.0", description="OCR version")
    started_at: str = Field(..., description="Start timestamp (ISO 8601)")
    completed_at: str = Field(..., description="Completion timestamp (ISO 8601)")


class AnalyzeResponseV2(BaseModel):
    """Enhanced response schema for bank statement analysis"""
    requestId: str = Field(..., description="Unique request ID")
    customerId: str = Field(..., description="Customer ID")
    processingStatus: str = Field(..., description="SUCCESS, FAILED, PARTIAL")
    bankstatement: List[BankStatementSchema] = Field(default_factory=list, description="Bank statements")
    payslip: List[PayslipSchema] = Field(default_factory=list, description="Payslips")
    analysis_summary: AnalysisSummarySchema = Field(..., description="Analysis summary")
    metadata: MetadataSchema = Field(..., description="Processing metadata")

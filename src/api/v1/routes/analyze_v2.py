"""
API Routes: Analyze Statement V2 (Enhanced Response Format)
"""

import os
import hashlib
import tempfile
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from api.v1.schemas_v2 import (
    AnalyzeResponseV2,
    BankStatementSchema,
    PeriodSchema,
    StatementScoreSchema,
    TransactionV2Schema,
    SalaryCreditSchema,
    MonthlySummarySchema,
    PayslipSchema,
    AnalysisSummarySchema,
    MetadataSchema
)
from api.v1.dependencies import get_analyze_use_case
from application.use_cases.analyze_statement import AnalyzeStatementUseCase
from domain.enums import IncomeType


router = APIRouter()


def generate_request_id() -> str:
    """Generate unique request ID"""
    now = datetime.now(timezone.utc)
    return f"REQ-{now.strftime('%Y-%m-%d-%H%M%S')}"


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return f"sha256:{sha256_hash.hexdigest()}"


def convert_date_to_iso(date_str: str) -> str:
    """Convert Thai date format to ISO (YYYY-MM-DD)"""
    if not date_str:
        return ""
    
    # Parse DD/MM/YYYY or DD-MM-YY formats
    date_str = date_str.replace("-", "/")
    parts = date_str.split("/")
    
    if len(parts) != 3:
        return ""
    
    day, month, year = parts
    
    # Convert 2-digit year to 4-digit
    if len(year) == 2:
        year_int = int(year)
        if year_int >= 50:  # 50-99 = 2550-2599 (Buddhist)
            year = f"25{year}"
        else:  # 00-49 = 2600-2649
            year = f"26{year}"
    
    # Convert Buddhist year to Gregorian (subtract 543)
    if int(year) > 2500:
        year = str(int(year) - 543)
    
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


@router.post("/analyze-statement-v2")
async def analyze_statement_v2(
    pdf_file: UploadFile = File(..., description="Bank statement PDF file"),
    customer_id: str = Form(..., description="Customer identifier"),
    pdf_password: Optional[str] = Form(None, description="PDF password if encrypted"),
    expected_gross: Optional[float] = Form(None, description="Expected gross salary/income"),
    employer: Optional[str] = Form(None, description="Employer name (for salaried)"),
    income_type: Optional[str] = Form("salaried", description="Income type: salaried or self_employed"),
    use_case: AnalyzeStatementUseCase = Depends(get_analyze_use_case)
):
    """
    Analyze bank statement with enhanced response format
    
    Returns comprehensive analysis including:
    - Transaction details
    - Monthly summaries
    - Salary identification
    - Statement quality score
    - Processing metadata
    """
    
    start_time = datetime.now(timezone.utc)
    request_id = generate_request_id()
    
    # Validate file
    if not pdf_file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    try:
        content = await pdf_file.read()
        temp_file.write(content)
        temp_file.flush()
        temp_file_path = temp_file.name
        temp_file.close()
        
        # Calculate file hash
        file_hash = calculate_file_hash(temp_file_path)
        
        # Parse income type
        income_type_enum = IncomeType.SALARIED
        if income_type and income_type.lower() == "self_employed":
            income_type_enum = IncomeType.SELF_EMPLOYED
        
        # Execute analysis use case
        result = await use_case.execute(
            pdf_path=temp_file_path,
            user_id=customer_id,
            pdf_password=pdf_password,
            expected_gross=expected_gross,
            employer=employer,
            income_type=income_type_enum,
            upload_to_storage=True
        )
        
        # Convert transactions to V2 format
        transactions_v2 = []
        salary_credits = []
        
        for tx in result.get("transactions", []):
            tx_v2 = TransactionV2Schema(
                date=convert_date_to_iso(tx.get("date", "")),
                description=tx.get("description", ""),
                amount=tx.get("amount", 0.0),
                type="credit" if tx.get("is_credit", False) else "debit",
                balanceAfter=None,
                channel=tx.get("channel"),
                counterparty=tx.get("payer"),
                category="salary" if tx.get("cluster_id") == 0 else None
            )
            transactions_v2.append(tx_v2)
            
            # Identify salary credits
            if tx.get("is_credit") and tx.get("cluster_id") == 0:
                salary_credits.append(SalaryCreditSchema(
                    date=convert_date_to_iso(tx.get("date", "")),
                    amount=tx.get("amount", 0.0),
                    employerName=tx.get("payer") or employer or "",
                    payCycle="monthly",
                    confidence=0.95 if tx.get("score", 0) > 15 else 0.75
                ))
        
        # Calculate monthly summaries
        from collections import defaultdict
        monthly_data = defaultdict(lambda: {"credit": 0.0, "debit": 0.0, "salary_count": 0})
        
        for tx in result.get("transactions", []):
            if not tx.get("date"):
                continue
            
            iso_date = convert_date_to_iso(tx["date"])
            if not iso_date:
                continue
            
            month_key = iso_date[:7]  # YYYY-MM
            
            if tx.get("is_credit"):
                monthly_data[month_key]["credit"] += tx.get("amount", 0.0)
                if tx.get("cluster_id") == 0:
                    monthly_data[month_key]["salary_count"] += 1
            else:
                monthly_data[month_key]["debit"] += tx.get("amount", 0.0)
        
        monthly_summaries = [
            MonthlySummarySchema(
                month=month,
                totalCredit=data["credit"],
                totalDebit=data["debit"],
                salaryCount=data["salary_count"],
                cashDepositAmount=0.0
            )
            for month, data in sorted(monthly_data.items())
        ]
        
        # Determine period
        dates = [convert_date_to_iso(tx.get("date", "")) for tx in result.get("transactions", []) if tx.get("date")]
        dates = [d for d in dates if d]
        
        start_date = min(dates) if dates else ""
        end_date = max(dates) if dates else ""
        
        # Calculate statement score
        analysis = result.get("analysis", {})
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
        base_score = confidence_map.get(analysis.get("confidence", "low"), 0.5)
        
        score_reasons = []
        if analysis.get("months_detected", 0) >= 6:
            score_reasons.append("sufficient_data_period")
            base_score += 0.05
        if analysis.get("approved", False):
            score_reasons.append("stable_monthly_salary")
            base_score += 0.05
        
        statement_score = StatementScoreSchema(
            value=min(base_score, 1.0),
            version="1.1.0",
            reasons=score_reasons
        )
        
        # Build bank statement object
        bank_statement = BankStatementSchema(
            holderName="",
            bankName="",
            accountName="",
            accountNumberMasked="XXX-XXX-XXXX",
            accountType="SAVING",
            period=PeriodSchema(
                startDate=start_date,
                endDate=end_date
            ),
            totalMonths=analysis.get("months_detected", 0),
            avgMonthlyIncome=analysis.get("detected_amount", 0.0),
            avgSalary=analysis.get("detected_amount", 0.0) if income_type_enum == IncomeType.SALARIED else 0.0,
            missingMonths=[],
            totalCredit=sum(tx.get("amount", 0.0) for tx in result.get("transactions", []) if tx.get("is_credit")),
            totalDebit=sum(tx.get("amount", 0.0) for tx in result.get("transactions", []) if not tx.get("is_credit")),
            language="th",
            ocrConfidence=0.92,
            parsingConfidence=0.90,
            sourceFileName=pdf_file.filename,
            sourceFileHash=file_hash,
            pages=result.get("statistics", {}).get("pages_processed", 0),
            mimeType="application/pdf",
            exportedAt=datetime.now(timezone.utc).isoformat(),
            statementScore=statement_score,
            transactions=transactions_v2,
            salaryCredits=salary_credits,
            monthlySummaries=monthly_summaries
        )
        
        # Build payslip (if salaried)
        payslips = []
        if income_type_enum == IncomeType.SALARIED and salary_credits:
            latest_salary = salary_credits[-1]
            payslips.append(PayslipSchema(
                salary=analysis.get("detected_amount", 0.0),
                netSalary=latest_salary.amount,
                employerName=latest_salary.employerName,
                paydate=latest_salary.date
            ))
        
        # Build analysis summary
        analysis_summary = AnalysisSummarySchema(
            total_avg_monthly_income=analysis.get("detected_amount", 0.0),
            primary_income_source=employer or salary_credits[0].employerName if salary_credits else "",
            total_accounts=1
        )
        
        # Build metadata
        end_time = datetime.now(timezone.utc)
        processing_time = int((end_time - start_time).total_seconds() * 1000)
        
        metadata = MetadataSchema(
            processing_time_ms=processing_time,
            ocr_version="2.1.0",
            started_at=start_time.isoformat(),
            completed_at=end_time.isoformat()
        )
        
        # Build response
        return AnalyzeResponseV2(
            requestId=request_id,
            customerId=customer_id,
            processingStatus="SUCCESS",
            bankstatement=[bank_statement],
            payslip=payslips,
            analysis_summary=analysis_summary,
            metadata=metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    finally:
        # Cleanup
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

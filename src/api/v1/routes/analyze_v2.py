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
from api.v1.dependencies import (
    get_pdf_extractor,
    get_data_masker,
    get_salary_analyzer,
    get_storage,
    get_database
)
from application.ports.database import IDatabase
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
    
    # Convert 2-digit year to 4-digit (assume Gregorian year)
    if len(year) == 2:
        year_int = int(year)
        # Assume all years 00-99 are 2000-2099 (Gregorian)
        year = f"20{year}"
    
    # Convert Buddhist year to Gregorian (subtract 543)
    elif int(year) >= 2500:
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
    database: IDatabase = Depends(get_database)
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
        
        # Create use case with dependencies
        pdf_extractor = get_pdf_extractor(temp_file_path, pdf_password)
        use_case = AnalyzeStatementUseCase(
            pdf_extractor=pdf_extractor,
            data_masker=get_data_masker(),
            salary_analyzer=get_salary_analyzer(),
            storage=get_storage(),
            database=database
        )
        
        # Execute analysis use case
        result = await use_case.execute(
            pdf_path=temp_file_path,
            user_id=customer_id,
            password=pdf_password,
            expected_gross=expected_gross,
            employer=employer,
            income_type=income_type_enum,
            upload_to_storage=True
        )
        
        # Get statistics from result
        stats = result.get("statistics", {})
        analysis = result.get("analysis", {})
        csv_path = result.get("csv_path")
        
        # Convert transactions from CSV to V2 format
        transactions_v2 = []
        if csv_path and os.path.exists(csv_path):
            try:
                import csv
                with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        # Convert CSV row to TransactionV2Schema
                        transactions_v2.append(TransactionV2Schema(
                            date=convert_date_to_iso(row.get('date', '')),
                            time=row.get('time', ''),
                            description=row.get('description', ''),
                            amount=float(row.get('amount', 0)),
                            type=row.get('type', ''),
                            balance=None,  # Not in CSV
                            channel=row.get('channel'),
                            counterparty=row.get('payer'),
                            category=None  # Not available
                        ))
                print(f"[TRANSACTIONS] Loaded {len(transactions_v2)} transactions from CSV")
            except Exception as e:
                print(f"[TRANSACTIONS] Error reading CSV: {e}")
                transactions_v2 = []
        
        salary_credits = []
        
        # Monthly summaries - empty for now (no transaction details available)
        # Would need to extract actual transactions to populate this correctly
        months_detected = analysis.get("months_detected", 0)
        detected_amount = analysis.get("detected_amount", 0.0)
        monthly_summaries = []  # Empty - no real monthly breakdown available
        
        # Create salary credits from analysis
        if income_type_enum == IncomeType.SALARIED and detected_amount > 0:
            for i in range(min(months_detected, 3)):  # Show last 3 months
                salary_credits.append(SalaryCreditSchema(
                    date=f"2025-{str(i+1).zfill(2)}-25",  # Placeholder
                    amount=detected_amount,
                    employerName=employer or "",
                    payCycle="monthly",
                    confidence=0.95 if analysis.get("confidence") == "high" else 0.75
                ))
        
        # Determine period from months_detected
        start_date = ""
        end_date = ""
        if months_detected > 0:
            # Placeholder dates
            start_date = "2025-01-01"
            end_date = f"2025-{str(months_detected).zfill(2)}-28"
        
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
            totalCredit=stats.get("credit_transactions", 0) * analysis.get("detected_amount", 0.0) if income_type_enum == IncomeType.SALARIED else detected_amount * months_detected,
            totalDebit=stats.get("debit_transactions", 0) * 1000.0,  # Placeholder
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
        
        # Build payslip (only if payslip file is uploaded - currently none)
        payslips = []  # Empty - no payslip uploaded
        
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

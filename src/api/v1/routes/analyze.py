"""
API Routes: Analyze Statement
"""

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from api.v1.schemas import AnalyzeResponse, ErrorResponse
from api.v1.dependencies import get_analyze_use_case, get_database
from application.use_cases.analyze_statement import AnalyzeStatementUseCase
from application.ports.database import IDatabase
from domain.enums import IncomeType


router = APIRouter()


@router.post("/analyze-upload", response_model=AnalyzeResponse)
async def analyze_upload(
    pdf_file: UploadFile = File(..., description="Bank statement PDF file"),
    user_id: str = Form(..., description="User identifier"),
    pdf_password: Optional[str] = Form(None, description="PDF password if encrypted"),
    expected_gross: Optional[float] = Form(None, description="Expected gross salary/income"),
    employer: Optional[str] = Form(None, description="Employer name (for salaried)"),
    pvd_rate: float = Form(0.0, description="Provident fund rate (for salaried)"),
    extra_deductions: float = Form(0.0, description="Extra deductions (for salaried)"),
    income_type: Optional[str] = Form(None, description="Income type: salaried or self_employed"),
    upload_to_storage: bool = Form(True, description="Upload to S3"),
    database: IDatabase = Depends(get_database)
):
    """
    Analyze bank statement from uploaded PDF
    
    Workflow:
    1. Extract transactions from PDF (PyMuPDF)
    2. Mask sensitive data (PDPA compliance)
    3. Analyze salary/income (Thai tax model for salaried, average for self-employed)
    4. Upload PDF to S3/storage
    5. Save results to PostgreSQL database
    
    Income Types:
    - salaried: Regular salary from employer (recurring pattern detection)
    - self_employed: Freelance/business income (6-month average of all credits)
    - Default: salaried (if not specified)
    """
    
    # Validate PDF file
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Parse income_type
    parsed_income_type = None
    if income_type:
        try:
            parsed_income_type = IncomeType(income_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid income_type: {income_type}. Must be 'salaried' or 'self_employed'"
            )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = await pdf_file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Get PDF extractor based on bank detection
        from api.v1.dependencies import get_pdf_extractor
        pdf_extractor = get_pdf_extractor(tmp_path, pdf_password)
        
        # Get use case with database and detected extractor injected
        use_case = get_analyze_use_case(
            pdf_extractor=pdf_extractor,
            database=database
        )
        
        # Execute use case
        result = await use_case.execute(
            pdf_path=tmp_path,
            user_id=user_id,
            password=pdf_password,
            expected_gross=expected_gross,
            employer=employer,
            pvd_rate=pvd_rate,
            extra_deductions=extra_deductions,
            income_type=parsed_income_type,
            upload_to_storage=upload_to_storage
        )
        
        return AnalyzeResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/analyze-s3", response_model=AnalyzeResponse)
async def analyze_s3(
    s3_key: str = Form(..., description="S3 object key for PDF"),
    user_id: str = Form(..., description="User identifier"),
    pdf_password: Optional[str] = Form(None, description="PDF password if encrypted"),
    expected_gross: Optional[float] = Form(None, description="Expected gross salary"),
    employer: Optional[str] = Form(None, description="Employer name"),
    pvd_rate: float = Form(0.0, description="Provident fund rate"),
    extra_deductions: float = Form(0.0, description="Extra deductions")
):
    """
    Analyze bank statement from S3
    
    For mobile apps: Upload PDF to S3 first, then call this endpoint
    """
    
    # Get use case and storage
    use_case = get_analyze_use_case()
    storage = use_case.storage
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Download from S3
        storage.download(s3_key, tmp_path)
        
        # Execute use case
        result = use_case.execute(
            pdf_path=tmp_path,
            user_id=user_id,
            password=pdf_password,
            expected_gross=expected_gross,
            employer=employer,
            pvd_rate=pvd_rate,
            extra_deductions=extra_deductions,
            upload_to_storage=True
        )
        
        return AnalyzeResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

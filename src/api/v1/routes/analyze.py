"""
API Routes: Analyze Statement
"""

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from api.v1.schemas import AnalyzeResponse, ErrorResponse
from api.v1.dependencies import get_analyze_use_case
from application.use_cases.analyze_statement import AnalyzeStatementUseCase


router = APIRouter()


@router.post("/analyze-upload", response_model=AnalyzeResponse)
async def analyze_upload(
    pdf_file: UploadFile = File(..., description="Bank statement PDF file"),
    user_id: str = Form(..., description="User identifier"),
    pdf_password: Optional[str] = Form(None, description="PDF password if encrypted"),
    expected_gross: Optional[float] = Form(None, description="Expected gross salary"),
    employer: Optional[str] = Form(None, description="Employer name"),
    pvd_rate: float = Form(0.0, description="Provident fund rate"),
    extra_deductions: float = Form(0.0, description="Extra deductions"),
    upload_to_storage: bool = Form(True, description="Upload to S3")
):
    """
    Analyze bank statement from uploaded PDF
    
    Workflow:
    1. Extract transactions from PDF (PyMuPDF)
    2. Mask sensitive data (PDPA compliance)
    3. Analyze salary (Thai tax model)
    4. Upload results to S3/storage
    """
    
    # Validate PDF file
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = await pdf_file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Get use case
        use_case = get_analyze_use_case()
        
        # Execute use case
        result = use_case.execute(
            pdf_path=tmp_path,
            user_id=user_id,
            password=pdf_password,
            expected_gross=expected_gross,
            employer=employer,
            pvd_rate=pvd_rate,
            extra_deductions=extra_deductions,
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

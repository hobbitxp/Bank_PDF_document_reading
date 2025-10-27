"""
API Schemas: Pydantic models for request/response validation
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request schema for analyze endpoint"""
    
    user_id: str = Field(..., description="User identifier")
    pdf_password: Optional[str] = Field(None, description="PDF password if encrypted")
    expected_gross: Optional[float] = Field(None, description="Expected gross salary for validation")
    employer: Optional[str] = Field(None, description="Employer name for matching")
    pvd_rate: float = Field(0.0, ge=0.0, le=0.15, description="Provident fund rate (0.0-0.15)")
    extra_deductions: float = Field(0.0, ge=0.0, description="Extra annual deductions (THB)")
    upload_to_storage: bool = Field(True, description="Upload results to S3/storage")


class TransactionSchema(BaseModel):
    """Transaction schema"""
    
    page: int
    amount: float
    description: str
    is_credit: bool
    time: Optional[str]
    channel: Optional[str]
    payer: Optional[str]
    score: Optional[int]
    cluster_id: Optional[int]


class StatisticsSchema(BaseModel):
    """Statistics schema"""
    
    total_transactions: int
    credit_transactions: int
    debit_transactions: int
    masked_items: int
    pages_processed: int


class AnalysisSchema(BaseModel):
    """Analysis result schema"""
    
    detected_amount: float
    confidence: str
    income_type: str
    transactions_analyzed: int
    clusters_found: int
    months_detected: int
    approved: bool
    rejection_reason: Optional[str]
    top_candidates_count: int
    matches_expected: Optional[bool]
    difference: Optional[float]
    difference_percentage: Optional[float]


class AnalyzeResponse(BaseModel):
    """Response schema for analyze endpoint"""
    
    success: bool
    analysis_id: str
    user_id: str
    timestamp: str
    statistics: StatisticsSchema
    analysis: AnalysisSchema
    pdf_storage_url: Optional[str] = None
    database_saved: bool = False


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str
    service: str
    version: str
    architecture: str
    storage_type: str
    database_status: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema"""
    
    success: bool = False
    error: str
    detail: Optional[str] = None

"""
API Routes: Health Check
"""

from fastapi import APIRouter

from api.v1.schemas import HealthResponse
from api.v1.dependencies import get_storage
from config import settings


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    
    # Check storage type
    storage = get_storage()
    storage_type = "s3" if hasattr(storage, 's3_client') else "local"
    
    return HealthResponse(
        status="healthy",
        service="bank-statement-analyzer",
        version="3.0.0-hexagonal",
        architecture="hexagonal",
        storage_type=storage_type
    )

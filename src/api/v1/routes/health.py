"""
API Routes: Health Check
"""

from fastapi import APIRouter, Depends

from api.v1.schemas import HealthResponse
from api.v1.dependencies import get_storage, get_database
from application.ports.database import IDatabase
from config import settings


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    database: IDatabase = Depends(get_database)
):
    """Health check endpoint"""
    
    # Check storage type
    storage = get_storage()
    storage_type = "s3" if hasattr(storage, 's3_client') else "local"
    
    # Check database health
    try:
        db_health = await database.health_check()
        database_status = "connected"
    except Exception as e:
        database_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy" if database_status == "connected" else "degraded",
        service="bank-statement-analyzer",
        version="3.0.0-hexagonal",
        architecture="hexagonal",
        storage_type=storage_type,
        database_status=database_status
    )

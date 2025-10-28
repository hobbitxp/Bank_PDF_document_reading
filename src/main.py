"""
FastAPI Application: Hexagonal Architecture
Main entry point for Bank Statement Analyzer API v3
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.v1.routes import health, analyze, analyze_v2
from api.v1.dependencies import get_database, close_database


# Create FastAPI app
app = FastAPI(
    title="Bank Statement Analyzer API",
    description="Hexagonal architecture for Thai bank statement analysis",
    version="3.0.0-hexagonal",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection pool on startup"""
    try:
        db = await get_database()
        health_status = await db.health_check()
        print(f"✅ Database connected: {health_status}")
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("API will start but database operations will fail")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection pool on shutdown"""
    await close_database()
    print("✅ Database connection closed")


# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(analyze_v2.router, prefix="/api/v1", tags=["Analysis V2"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Bank Statement Analyzer API",
        "version": "3.0.0-hexagonal",
        "architecture": "Hexagonal (Ports & Adapters)",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,  # Different port from legacy API
        reload=True,
        log_level="info"
    )

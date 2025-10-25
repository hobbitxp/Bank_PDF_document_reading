"""
Configuration Settings
"""

import os
from pathlib import Path


class Settings:
    """Application settings"""
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "bank-statements")
    S3_PRESIGNED_URL_EXPIRATION: int = int(os.getenv("S3_PRESIGNED_URL_EXPIRATION", "3600"))
    
    # Local Storage Configuration
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "data/storage")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()

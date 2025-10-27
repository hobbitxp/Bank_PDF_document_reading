"""
API Dependencies: Dependency Injection Container
"""

import os
from functools import lru_cache

from typing import Optional

from application.ports.pdf_extractor import IPDFExtractor
from application.ports.data_masker import IDataMasker
from application.ports.salary_analyzer import ISalaryAnalyzer
from application.ports.storage import IStorage
from application.ports.database import IDatabase
from application.use_cases.analyze_statement import AnalyzeStatementUseCase
from infrastructure.pdf.kbank_extractor import KBankPDFExtractor
from infrastructure.pdf.ktb_extractor import KTBPDFExtractor
from infrastructure.pdf.ttb_extractor import TTBPDFExtractor
from infrastructure.pdf.scb_extractor import SCBPDFExtractor
from infrastructure.pdf.bbl_extractor import BangkokBankPDFExtractor
from infrastructure.pdf.bank_detector import BankDetector
from infrastructure.masking.regex_masker import RegexDataMasker
from infrastructure.analysis.thai_analyzer import ThaiSalaryAnalyzer
from infrastructure.storage.s3_storage import S3Storage, LocalStorage
from infrastructure.database.postgres_adapter import PostgresDatabase
from config import settings


# Global database instance for connection pooling
_database_instance: PostgresDatabase | None = None


async def get_database() -> IDatabase:
    """Get database implementation with connection pooling"""
    global _database_instance
    
    if _database_instance is None:
        _database_instance = PostgresDatabase(
            connection_string=settings.DATABASE_URL,
            min_pool_size=settings.DATABASE_MIN_SIZE,
            max_pool_size=settings.DATABASE_MAX_SIZE
        )
        await _database_instance.connect()
    
    return _database_instance


async def close_database():
    """Close database connection pool"""
    global _database_instance
    
    if _database_instance is not None:
        await _database_instance.close()
        _database_instance = None


def get_pdf_extractor(pdf_path: str, password: Optional[str] = None) -> IPDFExtractor:
    """
    Factory function to get appropriate PDF extractor based on bank detection
    
    Args:
        pdf_path: Path to PDF file for bank detection
        password: PDF password (if encrypted)
    
    Returns:
        Appropriate extractor (KTBPDFExtractor, KBankPDFExtractor, TTBPDFExtractor, etc.)
    """
    bank = BankDetector.detect_bank(pdf_path, password)
    
    print(f"[BANK_DETECT] Detected: {bank}")
    
    if bank == "KTB":
        return KTBPDFExtractor()
    elif bank == "KBANK":
        return KBankPDFExtractor()  # KBank parser (state machine)
    elif bank == "TMB":
        return TTBPDFExtractor()  # TMB/TTB parser
    elif bank == "SCB":
        return SCBPDFExtractor()  # SCB parser
    elif bank == "BBL":
        return BangkokBankPDFExtractor()  # Bangkok Bank parser
    else:
        print(f"[WARN] Unknown bank '{bank}', using KBank parser as fallback")
        return KBankPDFExtractor()


@lru_cache()
def get_data_masker() -> IDataMasker:
    """Get data masker implementation"""
    return RegexDataMasker()


@lru_cache()
def get_salary_analyzer() -> ISalaryAnalyzer:
    """Get salary analyzer implementation"""
    return ThaiSalaryAnalyzer()


@lru_cache()
def get_storage() -> IStorage:
    """Get storage implementation (S3 or Local fallback)"""
    
    # Try S3 if credentials available
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        try:
            return S3Storage(
                bucket_name=settings.S3_BUCKET_NAME,
                aws_access_key=settings.AWS_ACCESS_KEY_ID,
                aws_secret_key=settings.AWS_SECRET_ACCESS_KEY,
                region=settings.AWS_REGION,
                url_expiration=settings.S3_PRESIGNED_URL_EXPIRATION,
                endpoint_url=getattr(settings, 'S3_ENDPOINT_URL', None)
            )
        except Exception as e:
            print(f"⚠️  S3 initialization failed, using local storage: {e}")
    
    # Fallback to local storage
    return LocalStorage(base_path=settings.LOCAL_STORAGE_PATH)


def get_analyze_use_case(
    pdf_extractor: IPDFExtractor = None,
    data_masker: IDataMasker = None,
    salary_analyzer: ISalaryAnalyzer = None,
    storage: IStorage = None,
    database: IDatabase = None
) -> AnalyzeStatementUseCase:
    """Get analyze statement use case with injected dependencies"""
    
    return AnalyzeStatementUseCase(
        pdf_extractor=pdf_extractor or get_pdf_extractor(),
        data_masker=data_masker or get_data_masker(),
        salary_analyzer=salary_analyzer or get_salary_analyzer(),
        storage=storage or get_storage(),
        database=database  # Will be injected from route handler
    )

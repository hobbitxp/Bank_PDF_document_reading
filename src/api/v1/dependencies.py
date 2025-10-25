"""
API Dependencies: Dependency Injection Container
"""

import os
from functools import lru_cache

from application.ports.pdf_extractor import IPDFExtractor
from application.ports.data_masker import IDataMasker
from application.ports.salary_analyzer import ISalaryAnalyzer
from application.ports.storage import IStorage
from application.use_cases.analyze_statement import AnalyzeStatementUseCase
from infrastructure.pdf.pymupdf_extractor import PyMuPDFExtractor
from infrastructure.masking.regex_masker import RegexDataMasker
from infrastructure.analysis.thai_analyzer import ThaiSalaryAnalyzer
from infrastructure.storage.s3_storage import S3Storage, LocalStorage
from config import settings


@lru_cache()
def get_pdf_extractor() -> IPDFExtractor:
    """Get PDF extractor implementation"""
    return PyMuPDFExtractor()


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
                url_expiration=settings.S3_PRESIGNED_URL_EXPIRATION
            )
        except Exception as e:
            print(f"⚠️  S3 initialization failed, using local storage: {e}")
    
    # Fallback to local storage
    return LocalStorage(base_path=settings.LOCAL_STORAGE_PATH)


def get_analyze_use_case(
    pdf_extractor: IPDFExtractor = None,
    data_masker: IDataMasker = None,
    salary_analyzer: ISalaryAnalyzer = None,
    storage: IStorage = None
) -> AnalyzeStatementUseCase:
    """Get analyze statement use case with injected dependencies"""
    
    return AnalyzeStatementUseCase(
        pdf_extractor=pdf_extractor or get_pdf_extractor(),
        data_masker=data_masker or get_data_masker(),
        salary_analyzer=salary_analyzer or get_salary_analyzer(),
        storage=storage or get_storage()
    )

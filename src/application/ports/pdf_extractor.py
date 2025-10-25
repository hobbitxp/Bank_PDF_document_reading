"""
Port: PDF Extractor Interface
Defines contract for PDF extraction implementations
"""

from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.statement import Statement


class IPDFExtractor(ABC):
    """Interface for PDF extraction"""
    
    @abstractmethod
    def extract(self, pdf_path: str, password: Optional[str] = None) -> Statement:
        """
        Extract text and metadata from PDF
        
        Args:
            pdf_path: Path to PDF file
            password: PDF password if encrypted
            
        Returns:
            Statement entity with extracted data
            
        Raises:
            ValueError: If password is required but not provided
            Exception: If extraction fails
        """
        pass

"""
Database Port Interface
Defines the contract for database operations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID


class IDatabase(ABC):
    """
    Port interface for database operations
    Following Hexagonal Architecture - this is the application layer port
    """
    
    @abstractmethod
    async def save_analysis(
        self,
        user_id: str,
        detected_salary: Optional[float],
        confidence: str,
        transactions_analyzed: int,
        credit_transactions: int,
        debit_transactions: int,
        clusters_found: int,
        months_detected: int,
        approved: bool,
        rejection_reason: Optional[str],
        top_candidates_count: int,
        expected_gross: Optional[float],
        matches_expected: Optional[bool],
        difference: Optional[float],
        difference_percentage: Optional[float],
        employer: Optional[str],
        pvd_rate: Optional[float],
        extra_deductions: Optional[float],
        pdf_filename: Optional[str],
        pages_processed: int,
        masked_items: int,
        metadata: Dict[str, Any]
    ) -> UUID:
        """
        Save analysis results to database
        
        Args:
            user_id: User identifier
            detected_salary: Detected salary amount
            confidence: Confidence level (high, medium, low)
            transactions_analyzed: Total transactions analyzed
            credit_transactions: Number of credit transactions
            debit_transactions: Number of debit transactions
            clusters_found: Number of salary clusters detected
            top_candidates_count: Number of top candidates
            expected_gross: Expected gross salary (optional)
            matches_expected: Whether detected matches expected
            difference: Difference from expected
            difference_percentage: Percentage difference
            employer: Employer name (optional)
            pvd_rate: Provident fund rate (optional)
            extra_deductions: Extra deductions (optional)
            pdf_filename: Original PDF filename
            pages_processed: Number of pages processed
            masked_items: Number of PDPA-masked items
            metadata: Additional metadata in JSON format (top candidates, statistics)
            
        Returns:
            UUID: Analysis ID
        """
        pass
    
    @abstractmethod
    async def get_analysis(self, analysis_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis by ID
        
        Args:
            analysis_id: Analysis UUID
            
        Returns:
            Dict with analysis data or None if not found
        """
        pass
    
    @abstractmethod
    async def get_user_analyses(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> list[Dict[str, Any]]:
        """
        Get all analyses for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of analysis records
        """
        pass
    
    @abstractmethod
    async def save_audit_log(
        self,
        user_id: str,
        analysis_id: Optional[UUID],
        action: str,
        status: str,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        request_payload: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Save audit log entry
        
        Args:
            user_id: User identifier
            analysis_id: Related analysis ID (optional)
            action: Action performed (e.g., 'analyze_upload')
            status: Status (success, failed, pending)
            error_message: Error message if failed
            error_type: Error type/category
            ip_address: Client IP address
            user_agent: Client user agent
            processing_time_ms: Processing time in milliseconds
            request_payload: Request parameters (excluding sensitive data)
            
        Returns:
            UUID: Log entry ID
        """
        pass
    
    @abstractmethod
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        analysis_id: Optional[UUID] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Dict[str, Any]]:
        """
        Query audit logs with filters
        
        Args:
            user_id: Filter by user (optional)
            analysis_id: Filter by analysis (optional)
            action: Filter by action (optional)
            status: Filter by status (optional)
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of audit log entries
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check database connection health
        
        Returns:
            bool: True if database is accessible
        """
        pass
    
    @abstractmethod
    async def close(self):
        """
        Close database connection and cleanup resources
        """
        pass

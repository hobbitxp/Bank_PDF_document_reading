"""
PostgreSQL Database Adapter
Implements IDatabase port using asyncpg
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import asyncpg
from asyncpg.pool import Pool

from application.ports.database import IDatabase


class PostgresDatabase(IDatabase):
    """
    PostgreSQL adapter implementing IDatabase port
    Uses asyncpg for async database operations
    """
    
    def __init__(self, connection_string: str, min_pool_size: int = 5, max_pool_size: int = 20):
        """
        Initialize PostgreSQL adapter
        
        Args:
            connection_string: PostgreSQL connection string
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
        """
        self.connection_string = connection_string
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.pool: Optional[Pool] = None
    
    async def connect(self):
        """
        Establish database connection pool
        Must be called before using the adapter
        """
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=60
            )
    
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
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        query = """
            INSERT INTO analyses (
                user_id, detected_salary, confidence, transactions_analyzed,
                credit_transactions, debit_transactions, clusters_found,
                months_detected, approved, rejection_reason,
                top_candidates_count, expected_gross, matches_expected,
                difference, difference_percentage, employer, pvd_rate,
                extra_deductions, pdf_filename, pages_processed,
                masked_items, metadata, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                $21, $22, NOW()
            )
            RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            analysis_id = await conn.fetchval(
                query,
                user_id,
                detected_salary,
                confidence,
                transactions_analyzed,
                credit_transactions,
                debit_transactions,
                clusters_found,
                months_detected,
                approved,
                rejection_reason,
                top_candidates_count,
                expected_gross,
                matches_expected,
                difference,
                difference_percentage,
                employer,
                pvd_rate,
                extra_deductions,
                pdf_filename,
                pages_processed,
                masked_items,
                json.dumps(metadata)
            )
        
        return analysis_id
    
    async def get_analysis(self, analysis_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis by ID
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        query = """
            SELECT 
                id, user_id, detected_salary, confidence, transactions_analyzed,
                credit_transactions, debit_transactions, clusters_found,
                top_candidates_count, expected_gross, matches_expected,
                difference, difference_percentage, employer, pvd_rate,
                extra_deductions, pdf_filename, pages_processed,
                masked_items, metadata, created_at
            FROM analyses
            WHERE id = $1
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, analysis_id)
        
        if row is None:
            return None
        
        return dict(row)
    
    async def get_user_analyses(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> list[Dict[str, Any]]:
        """
        Get all analyses for a user
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        query = """
            SELECT 
                id, user_id, detected_salary, confidence, transactions_analyzed,
                credit_transactions, debit_transactions, clusters_found,
                top_candidates_count, expected_gross, matches_expected,
                difference, difference_percentage, employer, pvd_rate,
                extra_deductions, pdf_filename, pages_processed,
                masked_items, metadata, created_at
            FROM analyses
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, user_id, limit, offset)
        
        return [dict(row) for row in rows]
    
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
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        query = """
            INSERT INTO audit_logs (
                user_id, analysis_id, action, status, error_message,
                error_type, ip_address, user_agent, processing_time_ms,
                request_payload, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW()
            )
            RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            log_id = await conn.fetchval(
                query,
                user_id,
                analysis_id,
                action,
                status,
                error_message,
                error_type,
                ip_address,
                user_agent,
                processing_time_ms,
                json.dumps(request_payload) if request_payload else None
            )
        
        return log_id
    
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
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        # Build dynamic query with filters
        conditions = []
        params = []
        param_count = 1
        
        if user_id:
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)
            param_count += 1
        
        if analysis_id:
            conditions.append(f"analysis_id = ${param_count}")
            params.append(analysis_id)
            param_count += 1
        
        if action:
            conditions.append(f"action = ${param_count}")
            params.append(action)
            param_count += 1
        
        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT 
                id, user_id, analysis_id, action, status, error_message,
                error_type, ip_address, user_agent, processing_time_ms,
                request_payload, created_at
            FROM audit_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        params.extend([limit, offset])
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]
    
    async def health_check(self) -> bool:
        """
        Check database connection health
        """
        if self.pool is None:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False
    
    async def close(self):
        """
        Close database connection pool
        """
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

"""
Application Use Case: Analyze Bank Statement
Orchestrates all adapters to process statement
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid

from application.ports.pdf_extractor import IPDFExtractor
from application.ports.data_masker import IDataMasker
from application.ports.salary_analyzer import ISalaryAnalyzer
from application.ports.storage import IStorage
from application.ports.database import IDatabase
from domain.entities.statement import Statement
from domain.entities.salary_analysis import SalaryAnalysis


class AnalyzeStatementUseCase:
    """Use case for analyzing bank statements"""
    
    def __init__(
        self,
        pdf_extractor: IPDFExtractor,
        data_masker: IDataMasker,
        salary_analyzer: ISalaryAnalyzer,
        storage: IStorage,
        database: Optional[IDatabase] = None
    ):
        """Initialize use case with dependencies"""
        
        self.pdf_extractor = pdf_extractor
        self.data_masker = data_masker
        self.salary_analyzer = salary_analyzer
        self.storage = storage
        self.database = database
    
    async def execute(
        self,
        pdf_path: str,
        user_id: str,
        password: Optional[str] = None,
        expected_gross: Optional[float] = None,
        employer: Optional[str] = None,
        pvd_rate: float = 0.0,
        extra_deductions: float = 0.0,
        upload_to_storage: bool = True
    ) -> Dict[str, Any]:
        """Execute statement analysis workflow"""
        
        # Generate unique IDs
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # 1. Extract from PDF
        statement = self.pdf_extractor.extract(pdf_path, password)
        
        # 2. Mask sensitive data
        masked_statement, masking_mapping = self.data_masker.mask(statement)
        
        # 3. Analyze salary
        analysis = self.salary_analyzer.analyze(
            masked_statement,
            expected_gross=expected_gross,
            employer=employer,
            pvd_rate=pvd_rate,
            extra_deductions=extra_deductions
        )
        
        # 4. Upload PDF to storage (if enabled)
        pdf_storage_url = None
        if upload_to_storage:
            try:
                base_filename = Path(pdf_path).stem
                object_key = f"{user_id}/{timestamp}_{base_filename}.pdf"
                
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
                
                pdf_storage_url = self.storage.upload(
                    pdf_path,
                    object_key,
                    metadata={
                        "user_id": user_id,
                        "timestamp": timestamp,
                        "analysis_id": analysis_id
                    }
                )
            except Exception as e:
                # Continue even if upload fails
                pdf_storage_url = f"Upload failed: {e}"
        
        # 5. Save to database (if available)
        if self.database:
            try:
                # Prepare metadata
                metadata = {
                    "expected_gross": expected_gross,
                    "employer": employer,
                    "pvd_rate": pvd_rate,
                    "extra_deductions": extra_deductions,
                    "total_transactions": len(masked_statement.transactions),
                    "credit_transactions": len(masked_statement.get_credit_transactions()),
                    "debit_transactions": len(masked_statement.get_debit_transactions()),
                    "pages_processed": len(masked_statement.pages),
                    "top_candidates": [
                        {
                            "page": tx.page,
                            "amount": tx.amount,
                            "description": tx.description,
                            "time": tx.time,
                            "score": tx.score,
                            "cluster_id": tx.cluster_id
                        }
                        for tx in analysis.best_candidates[:10]  # Store top 10
                    ]
                }
                
                # Save analysis to database
                await self.database.save_analysis(
                    analysis_id=analysis_id,
                    user_id=user_id,
                    pdf_s3_key=object_key if upload_to_storage else None,
                    detected_salary=analysis.detected_amount,
                    confidence_level=analysis.confidence,
                    transactions_analyzed=analysis.transactions_analyzed,
                    clusters_found=analysis.clusters_found,
                    top_candidates_count=len(analysis.best_candidates),
                    matches_expected=analysis.matches_expected,
                    expected_salary=expected_gross,
                    difference_amount=analysis.difference,
                    difference_percentage=analysis.difference_percentage,
                    masked_items_count=masked_statement.masked_items_count,
                    pages_processed=len(masked_statement.pages),
                    pvd_rate=pvd_rate,
                    extra_deductions=extra_deductions,
                    employer_name=employer,
                    metadata=metadata
                )
                
                # Save audit log
                await self.database.save_audit_log(
                    user_id=user_id,
                    action="analyze_statement",
                    resource_type="analysis",
                    resource_id=analysis_id,
                    status="success",
                    request_payload={
                        "pdf_path": Path(pdf_path).name,
                        "expected_gross": expected_gross,
                        "employer": employer
                    },
                    response_data={
                        "detected_salary": analysis.detected_amount,
                        "confidence": analysis.confidence
                    },
                    ip_address=None,  # Will be set by API layer
                    user_agent=None   # Will be set by API layer
                )
                
            except Exception as e:
                # Log error but don't fail the whole operation
                print(f"Database save failed: {e}")
                
                # Try to log the error
                if self.database:
                    try:
                        await self.database.save_audit_log(
                            user_id=user_id,
                            action="analyze_statement",
                            resource_type="analysis",
                            resource_id=analysis_id,
                            status="error",
                            request_payload={"pdf_path": Path(pdf_path).name},
                            error_message=str(e),
                            ip_address=None,
                            user_agent=None
                        )
                    except:
                        pass  # Ignore audit log errors
        
        # 6. Build response
        return {
            "success": True,
            "analysis_id": analysis_id,
            "user_id": user_id,
            "timestamp": timestamp,
            "statistics": {
                "total_transactions": len(masked_statement.transactions),
                "credit_transactions": len(masked_statement.get_credit_transactions()),
                "debit_transactions": len(masked_statement.get_debit_transactions()),
                "masked_items": masked_statement.masked_items_count,
                "pages_processed": len(masked_statement.pages)
            },
            "analysis": {
                "detected_amount": analysis.detected_amount,
                "confidence": analysis.confidence,
                "transactions_analyzed": analysis.transactions_analyzed,
                "clusters_found": analysis.clusters_found,
                "top_candidates_count": len(analysis.best_candidates),
                "matches_expected": analysis.matches_expected,
                "difference": analysis.difference,
                "difference_percentage": analysis.difference_percentage
            },
            "pdf_storage_url": pdf_storage_url,
            "database_saved": self.database is not None
        }

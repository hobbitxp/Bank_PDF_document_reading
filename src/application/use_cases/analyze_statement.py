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
from domain.enums import IncomeType


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
        income_type: Optional[IncomeType] = None,
        upload_to_storage: bool = True
    ) -> Dict[str, Any]:
        """Execute statement analysis workflow"""
        
        # Generate unique IDs
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # 1. Extract from PDF
        statement = self.pdf_extractor.extract(pdf_path, password)
        
        # 1.1. Export transactions to CSV
        import os
        csv_filename = f"{user_id}_{timestamp.replace(':', '-').replace('.', '_')}_transactions.csv"
        csv_path = os.path.join("/app/tmp", csv_filename)
        try:
            statement.to_csv(csv_path)
            print(f"[CSV_EXPORT] Saved: {csv_path}")
        except Exception as e:
            print(f"[CSV_EXPORT] Error: {e}")
        
        # 2. Mask sensitive data
        masked_statement, masking_mapping = self.data_masker.mask(statement)
        
        # 3. Analyze salary
        analysis = self.salary_analyzer.analyze(
            masked_statement,
            expected_gross=expected_gross,
            employer=employer,
            pvd_rate=pvd_rate,
            extra_deductions=extra_deductions,
            income_type=income_type
        )
        
        # 4. Upload PDF to storage (if enabled)
        pdf_storage_url = None
        temp_storage_path = None
        if upload_to_storage:
            try:
                base_filename = Path(pdf_path).stem
                object_key = f"{user_id}/{timestamp}_{base_filename}.pdf"
                
                # Upload to S3
                pdf_storage_url = self.storage.upload(
                    pdf_path,
                    object_key,
                    metadata={
                        "user_id": user_id,
                        "timestamp": timestamp,
                        "analysis_id": analysis_id
                    }
                )
                
                # Verify upload by downloading back
                # Save to local tmp directory (inside container)
                tmp_dir = Path("/app/tmp")
                tmp_dir.mkdir(parents=True, exist_ok=True)
                
                temp_storage_path = tmp_dir / f"{timestamp}_{base_filename}.pdf"
                
                # Download from S3 to verify
                self.storage.download(object_key, str(temp_storage_path))
                
                # Verify file size
                original_size = Path(pdf_path).stat().st_size
                downloaded_size = temp_storage_path.stat().st_size
                
                if original_size != downloaded_size:
                    raise Exception(f"File size mismatch: original={original_size}, downloaded={downloaded_size}")
                
                print(f"✅ PDF verified and saved to: {temp_storage_path}")
                
            except Exception as e:
                # Continue even if upload fails
                pdf_storage_url = f"Upload failed: {e}"
                if temp_storage_path and temp_storage_path.exists():
                    temp_storage_path.unlink()  # Clean up on error
                temp_storage_path = None
        
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
                    user_id=user_id,
                    detected_salary=analysis.detected_amount,
                    confidence=analysis.confidence,
                    income_type=analysis.income_type.value,
                    transactions_analyzed=analysis.transactions_analyzed,
                    credit_transactions=len(masked_statement.get_credit_transactions()),
                    debit_transactions=len(masked_statement.get_debit_transactions()),
                    clusters_found=analysis.clusters_found,
                    months_detected=analysis.months_detected,
                    approved=analysis.approved,
                    rejection_reason=analysis.rejection_reason,
                    top_candidates_count=len(analysis.best_candidates),
                    expected_gross=expected_gross,
                    matches_expected=analysis.matches_expected,
                    difference=analysis.difference,
                    difference_percentage=analysis.difference_percentage,
                    employer=employer,
                    pvd_rate=pvd_rate,
                    extra_deductions=extra_deductions,
                    pdf_filename=Path(pdf_path).name,
                    pages_processed=len(masked_statement.pages),
                    masked_items=masked_statement.masked_items_count,
                    metadata=metadata
                )
                
                # Save audit log
                await self.database.save_audit_log(
                    user_id=user_id,
                    analysis_id=None,  # Will be set by database after save_analysis returns UUID
                    action="analyze_upload",
                    status="success",
                    request_payload={
                        "pdf_filename": Path(pdf_path).name,
                        "expected_gross": expected_gross,
                        "employer": employer,
                        "pvd_rate": pvd_rate,
                        "extra_deductions": extra_deductions
                    }
                )
                
            except Exception as e:
                # Log error but don't fail the whole operation
                print(f"❌ Database save failed: {e}")
                import traceback
                traceback.print_exc()
                
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
        else:
            print(f"⚠️  DEBUG: Database not available (self.database is None), skipping save")
        
        # 6. Clean up temporary storage file
        if temp_storage_path and temp_storage_path.exists():
            try:
                temp_storage_path.unlink()
                print(f"✅ Cleaned up temporary file: {temp_storage_path}")
            except Exception as e:
                print(f"⚠️  Failed to clean up temporary file: {e}")
        
        # 7. Build response
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
                "income_type": analysis.income_type.value,
                "transactions_analyzed": analysis.transactions_analyzed,
                "clusters_found": analysis.clusters_found,
                "months_detected": analysis.months_detected,
                "approved": analysis.approved,
                "rejection_reason": analysis.rejection_reason,
                "top_candidates_count": len(analysis.best_candidates),
                "matches_expected": analysis.matches_expected,
                "difference": analysis.difference,
                "difference_percentage": analysis.difference_percentage
            },
            "pdf_storage_url": pdf_storage_url,
            "database_saved": self.database is not None
        }

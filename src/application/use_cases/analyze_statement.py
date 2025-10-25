"""
Application Use Case: Analyze Bank Statement
Orchestrates all adapters to process statement
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from application.ports.pdf_extractor import IPDFExtractor
from application.ports.data_masker import IDataMasker
from application.ports.salary_analyzer import ISalaryAnalyzer
from application.ports.storage import IStorage
from domain.entities.statement import Statement
from domain.entities.salary_analysis import SalaryAnalysis


class AnalyzeStatementUseCase:
    """Use case for analyzing bank statements"""
    
    def __init__(
        self,
        pdf_extractor: IPDFExtractor,
        data_masker: IDataMasker,
        salary_analyzer: ISalaryAnalyzer,
        storage: IStorage
    ):
        """Initialize use case with dependencies"""
        
        self.pdf_extractor = pdf_extractor
        self.data_masker = data_masker
        self.salary_analyzer = salary_analyzer
        self.storage = storage
    
    def execute(
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
        
        # 4. Prepare outputs
        base_filename = Path(pdf_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_prefix = f"{user_id}/{timestamp}_{base_filename}"
        
        # Create output files
        outputs = self._create_output_files(
            masked_statement,
            masking_mapping,
            analysis,
            base_filename,
            timestamp
        )
        
        # 5. Upload to storage (if enabled)
        storage_urls = {}
        
        if upload_to_storage:
            for output_type, file_path in outputs.items():
                object_key = f"{output_prefix}_{output_type}.{self._get_extension(output_type)}"
                
                try:
                    url = self.storage.upload(
                        file_path,
                        object_key,
                        metadata={
                            "user_id": user_id,
                            "timestamp": timestamp,
                            "type": output_type
                        }
                    )
                    storage_urls[output_type] = url
                except Exception as e:
                    # Continue even if upload fails
                    storage_urls[output_type] = f"Upload failed: {e}"
        
        # 6. Build response
        return {
            "success": True,
            "statement_id": f"{timestamp}_{base_filename}",
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
            "storage_urls": storage_urls,
            "local_files": outputs
        }
    
    def _create_output_files(
        self,
        statement: Statement,
        mapping: Dict[str, str],
        analysis: SalaryAnalysis,
        base_filename: str,
        timestamp: str
    ) -> Dict[str, str]:
        """Create output files locally"""
        
        output_dir = Path("data/json")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        outputs = {}
        
        # 1. Masked statement JSON
        masked_path = output_dir / f"{base_filename}_masked.json"
        with open(masked_path, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "metadata": {
                        "filename": base_filename,
                        "timestamp": timestamp,
                        "masked": True
                    },
                    "pages": statement.pages,
                    "transactions": [
                        {
                            "page": tx.page,
                            "amount": tx.amount,
                            "description": tx.description,
                            "is_credit": tx.is_credit,
                            "time": tx.time,
                            "channel": tx.channel,
                            "payer": tx.payer
                        }
                        for tx in statement.transactions
                    ]
                },
                f,
                indent=2,
                ensure_ascii=False
            )
        outputs["masked"] = str(masked_path)
        
        # 2. Masking mapping JSON (SECRET - local only)
        mapping_path = output_dir / f"{base_filename}_mapping.json"
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "metadata": {
                        "filename": base_filename,
                        "timestamp": timestamp,
                        "warning": "SECRET FILE - DO NOT SHARE"
                    },
                    "mapping": mapping
                },
                f,
                indent=2,
                ensure_ascii=False
            )
        outputs["mapping"] = str(mapping_path)
        
        # 3. Analysis JSON
        analysis_path = output_dir / f"{base_filename}_analysis.json"
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "metadata": {
                        "filename": base_filename,
                        "timestamp": timestamp
                    },
                    "analysis": {
                        "detected_amount": analysis.detected_amount,
                        "confidence": analysis.confidence,
                        "transactions_analyzed": analysis.transactions_analyzed,
                        "clusters_found": analysis.clusters_found,
                        "matches_expected": analysis.matches_expected,
                        "difference": analysis.difference,
                        "difference_percentage": analysis.difference_percentage
                    },
                    "top_candidates": [
                        {
                            "page": tx.page,
                            "amount": tx.amount,
                            "description": tx.description,
                            "time": tx.time,
                            "channel": tx.channel,
                            "payer": tx.payer,
                            "score": tx.score,
                            "cluster_id": tx.cluster_id
                        }
                        for tx in analysis.best_candidates
                    ]
                },
                f,
                indent=2,
                ensure_ascii=False
            )
        outputs["analysis"] = str(analysis_path)
        
        return outputs
    
    def _get_extension(self, output_type: str) -> str:
        """Get file extension for output type"""
        
        return {
            "masked": "json",
            "mapping": "json",
            "analysis": "json",
            "excel": "xlsx"
        }.get(output_type, "json")

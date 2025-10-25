"""
Port: Salary Analyzer Interface
Defines contract for salary detection implementations
"""

from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.statement import Statement
from domain.entities.salary_analysis import SalaryAnalysis


class ISalaryAnalyzer(ABC):
    """Interface for salary analysis"""
    
    @abstractmethod
    def analyze(
        self, 
        statement: Statement,
        expected_salary: Optional[float] = None,
        employer_name: Optional[str] = None
    ) -> SalaryAnalysis:
        """
        Analyze statement to detect salary transactions
        
        Args:
            statement: Statement entity with transactions
            expected_salary: Expected gross salary for validation
            employer_name: Employer name for matching
            
        Returns:
            SalaryAnalysis entity with detection results
        """
        pass

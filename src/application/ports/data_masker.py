"""
Port: Data Masker Interface
Defines contract for data masking implementations (PDPA compliance)
"""

from abc import ABC, abstractmethod
from domain.entities.statement import Statement


class IDataMasker(ABC):
    """Interface for data masking"""
    
    @abstractmethod
    def mask(self, statement: Statement) -> tuple[Statement, dict[str, str]]:
        """
        Mask sensitive personal data in statement
        
        Args:
            statement: Statement entity with unmasked data
            
        Returns:
            Tuple of (masked_statement, mapping_dict)
            - masked_statement: Statement with masked data
            - mapping_dict: Dictionary mapping masked tokens to original values
            
        Note:
            Mapping dict should be stored securely and never shared
        """
        pass

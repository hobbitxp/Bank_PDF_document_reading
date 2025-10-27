"""Income Type Enumeration

Defines types of income sources for salary analysis.
"""

from enum import Enum


class IncomeType(str, Enum):
    """Income type classification
    
    SALARIED: Regular salary from employer (recurring pattern)
    SELF_EMPLOYED: Freelance/business income (averaged over period)
    """
    
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    
    def __str__(self) -> str:
        return self.value

"""
Bank statement parsers module
"""
from .base_parser import BaseParser
from .scb_parser import SCBParser
from .tmb_parser import TMBParser
from .bbl_parser import BBLParser
from .kbank_parser import KBANKParser
from .ktb_parser import KTBParser


# Parser registry
PARSERS = {
    'scb': SCBParser,
    'tmb': TMBParser,
    'bbl': BBLParser,
    'kbank': KBANKParser,
    'ktb': KTBParser,
}


def get_parser(bank_code: str) -> BaseParser:
    """
    Get parser instance for a specific bank.

    Args:
        bank_code: Bank code ('scb', 'tmb', 'bbl', 'kbank', 'ktb')

    Returns:
        Parser instance

    Raises:
        ValueError: If bank code is not supported
    """
    bank_code = bank_code.lower()

    if bank_code not in PARSERS:
        supported = ', '.join(PARSERS.keys())
        raise ValueError(
            f"Unsupported bank: {bank_code}. "
            f"Supported banks: {supported}"
        )

    parser_class = PARSERS[bank_code]
    return parser_class()


def list_supported_banks() -> list:
    """
    Get list of supported bank codes.

    Returns:
        List of bank codes
    """
    return list(PARSERS.keys())


__all__ = [
    'BaseParser',
    'SCBParser',
    'TMBParser',
    'BBLParser',
    'KBANKParser',
    'KTBParser',
    'get_parser',
    'list_supported_banks',
]

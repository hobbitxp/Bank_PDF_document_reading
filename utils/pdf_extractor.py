"""
PDF extraction utilities using pdfplumber
"""
import pdfplumber
from typing import List, Dict, Any, Optional
from pathlib import Path


class PDFExtractor:
    """
    Utility class for extracting text and tables from PDF files.
    """

    def __init__(self, pdf_path: str):
        """
        Initialize the PDF extractor.

        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    def extract_text(self, page_numbers: Optional[List[int]] = None) -> str:
        """
        Extract text from PDF pages.

        Args:
            page_numbers: List of page numbers to extract (0-indexed).
                         If None, extract all pages.

        Returns:
            Extracted text as string
        """
        text = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            pages = pdf.pages if page_numbers is None else [pdf.pages[i] for i in page_numbers]

            for page in pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        return text

    def extract_tables(self, page_numbers: Optional[List[int]] = None,
                      table_settings: Optional[Dict] = None) -> List[List[List]]:
        """
        Extract tables from PDF pages.

        Args:
            page_numbers: List of page numbers to extract (0-indexed).
                         If None, extract all pages.
            table_settings: Custom table extraction settings for pdfplumber

        Returns:
            List of tables (each table is a list of rows, each row is a list of cells)
        """
        all_tables = []
        default_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
        }

        settings = {**default_settings, **(table_settings or {})}

        with pdfplumber.open(self.pdf_path) as pdf:
            pages = pdf.pages if page_numbers is None else [pdf.pages[i] for i in page_numbers]

            for page in pages:
                tables = page.extract_tables(table_settings=settings)
                if tables:
                    all_tables.extend(tables)

        return all_tables

    def extract_text_and_tables(self, page_numbers: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Extract both text and tables from PDF.

        Args:
            page_numbers: List of page numbers to extract (0-indexed).
                         If None, extract all pages.

        Returns:
            Dictionary with 'text' and 'tables' keys
        """
        return {
            "text": self.extract_text(page_numbers),
            "tables": self.extract_tables(page_numbers)
        }

    def get_page_count(self) -> int:
        """
        Get the total number of pages in the PDF.

        Returns:
            Number of pages
        """
        with pdfplumber.open(self.pdf_path) as pdf:
            return len(pdf.pages)

    def extract_page(self, page_number: int) -> Dict[str, Any]:
        """
        Extract text and tables from a specific page.

        Args:
            page_number: Page number (0-indexed)

        Returns:
            Dictionary with 'text' and 'tables' for that page
        """
        with pdfplumber.open(self.pdf_path) as pdf:
            if page_number >= len(pdf.pages):
                raise IndexError(f"Page {page_number} does not exist")

            page = pdf.pages[page_number]
            return {
                "text": page.extract_text() or "",
                "tables": page.extract_tables() or []
            }

    def search_text(self, search_term: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Search for text across all pages.

        Args:
            search_term: Text to search for
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            List of matches with page numbers and context
        """
        matches = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""

                if not case_sensitive:
                    text_search = text.lower()
                    term_search = search_term.lower()
                else:
                    text_search = text
                    term_search = search_term

                if term_search in text_search:
                    # Find the line containing the search term
                    lines = text.split('\n')
                    for line_num, line in enumerate(lines):
                        line_check = line if case_sensitive else line.lower()
                        if term_search in line_check:
                            matches.append({
                                "page": i,
                                "line": line_num,
                                "text": line.strip()
                            })

        return matches

    @staticmethod
    def is_valid_pdf(pdf_path: str) -> bool:
        """
        Check if a file is a valid PDF.

        Args:
            pdf_path: Path to check

        Returns:
            True if valid PDF, False otherwise
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages) > 0
        except Exception:
            return False


def extract_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Convenience function to extract text and tables from a PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with extracted data
    """
    extractor = PDFExtractor(pdf_path)
    return extractor.extract_text_and_tables()

"""
Thai date parsing utilities
Handles Buddhist calendar (พ.ศ.) to Gregorian (ค.ศ.) conversion
"""
import re
from datetime import datetime
from typing import Optional, Union
from dateutil import parser as dateutil_parser


class ThaiDateParser:
    """
    Parser for Thai dates with support for Buddhist calendar.
    """

    # Thai month names (full)
    THAI_MONTHS_FULL = {
        "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
        "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
        "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
    }

    # Thai month names (abbreviated)
    THAI_MONTHS_ABBR = {
        "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4,
        "พ.ค.": 5, "มิ.ย.": 6, "ก.ค.": 7, "ส.ค.": 8,
        "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12
    }

    # Common date patterns
    PATTERNS = [
        # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
        r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})',
        # DD Month YYYY (Thai)
        r'(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})',
        # DD Abbr. YYYY (Thai)
        r'(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*(\d{4})',
        # YYYY-MM-DD (ISO format)
        r'(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})',
    ]

    @staticmethod
    def buddhist_to_gregorian_year(buddhist_year: int) -> int:
        """
        Convert Buddhist calendar year to Gregorian calendar year.

        Args:
            buddhist_year: Year in Buddhist calendar (พ.ศ.)

        Returns:
            Year in Gregorian calendar (ค.ศ.)
        """
        return buddhist_year - 543

    @staticmethod
    def gregorian_to_buddhist_year(gregorian_year: int) -> int:
        """
        Convert Gregorian calendar year to Buddhist calendar year.

        Args:
            gregorian_year: Year in Gregorian calendar (ค.ศ.)

        Returns:
            Year in Buddhist calendar (พ.ศ.)
        """
        return gregorian_year + 543

    @classmethod
    def parse_thai_date(cls, date_str: str, assume_buddhist: bool = True) -> Optional[datetime]:
        """
        Parse Thai date string to datetime object.

        Args:
            date_str: Date string in various Thai formats
            assume_buddhist: If True, assume 4-digit years > 2500 are Buddhist calendar

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str or not isinstance(date_str, str):
            return None

        date_str = date_str.strip()

        # Try each pattern
        for pattern in cls.PATTERNS:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groups()

                # Handle different pattern types
                if pattern == cls.PATTERNS[0]:  # DD/MM/YYYY
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                elif pattern == cls.PATTERNS[1]:  # DD Month YYYY (full)
                    day = int(groups[0])
                    month = cls.THAI_MONTHS_FULL.get(groups[1])
                    year = int(groups[2])
                elif pattern == cls.PATTERNS[2]:  # DD Abbr. YYYY
                    day = int(groups[0])
                    month = cls.THAI_MONTHS_ABBR.get(groups[1])
                    year = int(groups[2])
                elif pattern == cls.PATTERNS[3]:  # YYYY-MM-DD
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                else:
                    continue

                # Convert Buddhist year if needed
                if assume_buddhist and year > 2500:
                    year = cls.buddhist_to_gregorian_year(year)

                try:
                    return datetime(year, month, day)
                except ValueError:
                    continue

        # Try dateutil as fallback
        try:
            return dateutil_parser.parse(date_str, dayfirst=True)
        except Exception:
            return None

    @classmethod
    def parse_date_flexible(cls, date_str: str) -> Optional[str]:
        """
        Parse date string and return in ISO format (YYYY-MM-DD).

        Args:
            date_str: Date string in various formats

        Returns:
            Date in ISO format or None
        """
        dt = cls.parse_thai_date(date_str)
        return dt.strftime("%Y-%m-%d") if dt else None

    @classmethod
    def parse_datetime_flexible(cls, date_str: str, time_str: Optional[str] = None) -> Optional[str]:
        """
        Parse date and time strings and return in ISO format.

        Args:
            date_str: Date string
            time_str: Optional time string (HH:MM:SS or HH:MM)

        Returns:
            Datetime in ISO format or None
        """
        dt = cls.parse_thai_date(date_str)
        if not dt:
            return None

        if time_str:
            # Parse time
            time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                second = int(time_match.group(3)) if time_match.group(3) else 0

                try:
                    dt = dt.replace(hour=hour, minute=minute, second=second)
                except ValueError:
                    pass

        return dt.isoformat()

    @staticmethod
    def normalize_thai_year(year: Union[int, str]) -> int:
        """
        Normalize year to Gregorian calendar.
        Automatically detects and converts Buddhist years.

        Args:
            year: Year as int or string

        Returns:
            Year in Gregorian calendar
        """
        year = int(year)

        # If year is > 2500, assume it's Buddhist calendar
        if year > 2500:
            return year - 543

        # If year is 2-digit, assume it's in 2000s
        if year < 100:
            return 2000 + year

        return year


def parse_thai_date(date_str: str) -> Optional[str]:
    """
    Convenience function to parse Thai date.

    Args:
        date_str: Date string in various Thai formats

    Returns:
        Date in ISO format (YYYY-MM-DD) or None
    """
    return ThaiDateParser.parse_date_flexible(date_str)


def parse_thai_datetime(date_str: str, time_str: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to parse Thai date and time.

    Args:
        date_str: Date string
        time_str: Optional time string

    Returns:
        Datetime in ISO format or None
    """
    return ThaiDateParser.parse_datetime_flexible(date_str, time_str)

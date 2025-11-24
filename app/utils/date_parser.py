"""
Date Parser Utility

Provides flexible date parsing for publication dates, similar to Zotero.
Accepts year-only, year-month, or full date formats and converts to datetime.date.
"""

from datetime import date
from typing import Optional, Union
import re


def parse_flexible_date(date_input: Union[str, int, date, None]) -> Optional[date]:
    """
    Parse flexible date formats into a datetime.date object.

    Accepts:
    - Year only: 2020, "2020" → 2020-01-01
    - Year-Month: "2020-05" → 2020-05-01
    - Full date: "2020-05-15" → 2020-05-15
    - Already a date object → return as-is

    Args:
        date_input: Year (int), partial date (str), or full date

    Returns:
        datetime.date object or None if invalid

    Examples:
        >>> parse_flexible_date(2020)
        datetime.date(2020, 1, 1)

        >>> parse_flexible_date("2020-05")
        datetime.date(2020, 5, 1)

        >>> parse_flexible_date("2020-05-15")
        datetime.date(2020, 5, 15)
    """
    if date_input is None:
        return None

    # Already a date object
    if isinstance(date_input, date):
        return date_input

    # Convert to string
    date_str = str(date_input).strip()

    if not date_str:
        return None

    try:
        # Pattern 1: Year only (4 digits)
        if re.match(r'^\d{4}$', date_str):
            year = int(date_str)
            return date(year, 1, 1)

        # Pattern 2: Year-Month (YYYY-MM)
        match = re.match(r'^(\d{4})-(\d{1,2})$', date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            return date(year, month, 1)

        # Pattern 3: Full date (YYYY-MM-DD)
        match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return date(year, month, day)

        # Pattern 4: Try other common formats
        # YYYY/MM/DD
        match = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return date(year, month, day)

        return None

    except (ValueError, OverflowError):
        # Invalid date values (e.g., month 13, day 32)
        return None


def format_date_display(publication_date: Optional[date]) -> str:
    """
    Format a publication date for display.

    If only year is meaningful (Jan 1), show only year.
    If only year-month (day is 1st), show year-month.
    Otherwise show full date.

    Args:
        publication_date: Date object to format

    Returns:
        Formatted date string

    Examples:
        >>> format_date_display(date(2020, 1, 1))
        '2020'

        >>> format_date_display(date(2020, 5, 1))
        '2020-05'

        >>> format_date_display(date(2020, 5, 15))
        '2020-05-15'
    """
    if not publication_date:
        return ''

    # Year only (Jan 1)
    if publication_date.month == 1 and publication_date.day == 1:
        return str(publication_date.year)

    # Year-Month (1st of month)
    if publication_date.day == 1:
        return f"{publication_date.year}-{publication_date.month:02d}"

    # Full date
    return publication_date.isoformat()

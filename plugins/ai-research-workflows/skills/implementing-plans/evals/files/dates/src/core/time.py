"""Date and time helpers."""
from datetime import date


def parse_date(text):
    """Parse an ISO date string (YYYY-MM-DD)."""
    return date.fromisoformat(text.strip())

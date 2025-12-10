"""
API Key utility functions.

This module provides helper functions for API key management.
"""

from datetime import datetime, timedelta


def parse_expiry(duration_str: str) -> datetime:
    """
    Parse expiry duration string to datetime.

    Args:
        duration_str (str): Duration in format "1Min", "1H", "1D", "1M", "1Y"

    Returns:
        datetime: Expiry datetime (naive UTC)
    """
    # Handle "Min" suffix for minutes
    if duration_str.upper().endswith("MIN"):
        value = int(duration_str[:-3])
        return datetime.utcnow() + timedelta(minutes=value)

    units = {"H": "hours", "D": "days", "M": "days", "Y": "days"}
    multipliers = {"H": 1, "D": 1, "M": 30, "Y": 365}

    value = int(duration_str[:-1])
    unit = duration_str[-1].upper()

    kwargs = {units[unit]: value * multipliers[unit]}
    return datetime.utcnow() + timedelta(**kwargs)

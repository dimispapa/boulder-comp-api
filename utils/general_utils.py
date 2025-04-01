"""
Utility functions for general purposes.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Union


def format_time_from_seconds(seconds: int) -> str:
    """
    Format seconds into a human-readable time string (e.g. "2h 30m 15s").

    Args:
        seconds (int): Number of seconds to format

    Returns:
        str: Formatted time string
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def normalize_url(url: str) -> str:
    """
    Normalize URLs to consistently exclude www. for 27crags.com

    Args:
        url (str): URL to normalize

    Returns:
        str: Normalized URL without www.
    """
    if url and "www.27crags.com" in url:
        return url.replace("https://www.27crags.com", "https://27crags.com")
    return url


def format_name(display_name: str) -> str:
    """
    Format display name to standard name format (lowercase with hyphens).

    Args:
        display_name (str): Display name to format

    Returns:
        str: Formatted name
    """
    return display_name.lower().replace(' ', '-')


def extract_datetime_from_filename(filename: Union[str, Path]) -> datetime:
    """
    Extract datetime from filename with pattern containing YYYYMMDD_HHMMSS.

    Args:
        filename (Union[str, Path]): The filename or Path object to extract
                                     datetime from

    Returns:
        datetime: The extracted datetime or min datetime if parsing fails
    """
    # Convert Path to string if needed
    if isinstance(filename, Path):
        filename_str = filename.name
    else:
        filename_str = str(filename)

    # Extract YYYYMMDD_HHMMSS pattern from filename
    match = re.search(r'(\d{8}_\d{6})', filename_str)
    if match:
        timestamp_str = match.group(1)
        # Parse into datetime object
        try:
            return datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
        except ValueError:
            pass

    # Return minimum datetime as fallback if parsing fails
    # This ensures files without valid timestamps sort last
    return datetime.min

"""
Utility functions for time formatting and calculations.
"""


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

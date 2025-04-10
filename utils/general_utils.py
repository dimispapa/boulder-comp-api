"""
Utility functions for general purposes.
"""
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Union

from fastapi import HTTPException
from utils.loggers import logger


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


def get_most_recent_json_file(data_dir: Path = Path("data/scraped"),
                              crag_name: str = "inia-droushia") -> Path:
    """
    Get the most recent file in the data directory matching the pattern.

    Args:
        data_dir (Path): The directory to search for files
        pattern (str): The pattern to match for files

    Returns:
        Path: The most recent file matching the pattern
    """
    # Format crag name to match file naming pattern
    formatted_crag_name = crag_name.lower().replace(' ', '_')
    logger.info(f"Finding most recent file for crag: {crag_name}")

    # Get all matching files
    pattern = f"{formatted_crag_name}_*.json"
    matching_files = list(data_dir.glob(pattern))

    if not matching_files:
        logger.error(f"No data files found for crag: {crag_name}")
        raise HTTPException(
            status_code=404,
            detail=f"No scraped data found for crag: {crag_name}")

    # Log all found files with creation date and embedded timestamp
    logger.info(f"Found {len(matching_files)} matching files:")
    for i, file in enumerate(matching_files, 1):
        embedded_date = extract_datetime_from_filename(file)
        logger.info(
            f"  {i}. {file.name} - Created: "
            f"{datetime.fromtimestamp(
                file.stat().st_ctime).isoformat()} - "
            f"Embedded timestamp: {embedded_date.isoformat()}")

    # Sort by the timestamp embedded in the filename (YYYYMMDD_HHMMSS)
    matching_files.sort(key=extract_datetime_from_filename,
                        reverse=True)
    file_path = str(matching_files[0])
    logger.info(
        f"Selected most recent file by embedded timestamp: {file_path}"
    )

    return file_path


def convert_csv_to_json():
    """Convert CSV files to JSON files and move to data/initial."""
    csv_files = {"boulder_sector_mappings": "data/boulder_sector_mappings.csv"}

    # Handle boulder_sector_mappings.csv
    for name, csv_path in csv_files.items():
        csv_path = Path(csv_path)
        json_path = Path(f'data/initial/{name}.json')

        if csv_path.exists() and not json_path.exists():
            try:
                import csv
                import json
                records = []
                with open(csv_path, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        records.append(dict(row))

                with open(json_path, 'w') as jsonfile:
                    json.dump(records, jsonfile, indent=2)

                logger.info(f"Converted {csv_path} to {json_path}")
            except Exception as e:
                logger.error(f"Error converting {csv_path} to JSON: {str(e)}")


def load_sql_file(filename: str) -> str:
    """Load SQL files from the sql directory.
    Works in both local and Docker environments.

    Args:
        filename (str): The name of the SQL file to load

    Returns:
        str: The contents of the SQL file
    """
    # Try different possible locations
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    possible_paths = [
        # Local dev path
        os.path.join(base_dir, "database", "sql", filename),
        # Docker container path
        os.path.join("/app", "database", "sql", filename),
        # Fallback path
        os.path.join(base_dir, "sql", filename)
    ]

    # Try each path until one works
    for sql_path in possible_paths:
        if os.path.exists(sql_path):
            with open(sql_path, "r") as f:
                return f.read()

    # If no paths worked, raise a more helpful error
    raise FileNotFoundError(
        f"Could not find SQL file '{filename}' in any of these locations:"
        f" {possible_paths}")

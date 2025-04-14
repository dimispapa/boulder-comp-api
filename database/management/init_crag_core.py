#!/usr/bin/env python
"""
Script to import boulder and route data from scraped files into the database.

This is the recommended way to import scraped crag data into the database.
After using the scraper tools to scrape data from 27crags.com, use this script
to import that data into your database.

Usage:
    python -m database.management.init_crag_core [--file FILE] [--crag CRAG]

Can be run as a standalone script or imported as a module.
"""
import argparse
import sys

from utils.loggers import logger
from utils.general_utils import get_most_recent_json_file


def import_boulder_route_data(file_path=None, crag_name="inia-droushia"):
    """
    Import boulder and route data from the most recent scraped file.

    This function loads the scraped crag data from a JSON file and
    imports it into the database. It uses the store_crag_data_task
    from the scraper module, but runs it synchronously.

    Args:
        file_path (str, optional): Path to the JSON file containing scraped
            data. If not provided, will use the most recent file for the
            specified crag.
        crag_name (str, optional): Name of the crag to find the most recent
            file for. Defaults to "inia-droushia".

    Returns:
        bool: True if the import was successful, False otherwise.
    """
    try:
        # Get the most recent scraped data file if not specified
        if not file_path:
            file_path = get_most_recent_json_file(crag_name=crag_name)

        if not file_path:
            logger.error("No scraped data files found. "
                         "Please run the scraper first.")
            return False

        logger.info(f"Importing boulder and route data from: {file_path}")

        # Load the file and store data
        try:
            # The store_crag_data_task function reconstructs the crag object
            # We can reuse that code
            from tasks.scraper_tasks import store_crag_data_task

            # Run the task synchronously, not as a Celery background task
            result = store_crag_data_task.run(str(file_path))

            if result["status"] == "success":
                logger.info("Successfully imported boulder and route data")
                return True
            else:
                logger.error(
                    f"Failed to import boulder and route data: {result}")
                return False

        except Exception as e:
            logger.error(f"Error importing boulder and route data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    except ImportError as e:
        logger.error(f"Import error when loading scraper modules: {str(e)}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import boulder and route data from scraped files into "
        "the database.")
    parser.add_argument("--file",
                        type=str,
                        help="Path to the JSON file with scraped data")
    parser.add_argument("--crag",
                        type=str,
                        default="inia-droushia",
                        help="Crag name to use for file search")
    args = parser.parse_args()

    success = import_boulder_route_data(args.file, args.crag)
    if not success:
        logger.error("Failed to import boulder and route data")
        sys.exit(1)

    logger.info("Boulder and route data import complete")

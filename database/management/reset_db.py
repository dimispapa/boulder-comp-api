#!/usr/bin/env python
"""
Reset the database, recreate all tables, and populate with mock data.
"""
import sys
import argparse

from database.management.base import create_db_and_tables, get_db_session
from utils.loggers import logger

# Import the standalone modules
from database.management.init_crag_core import import_boulder_route_data
from database.management.init_boulder_photos import reupload_boulder_photos

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset database and recreate tables.")
    # Argument to skip confirmation
    parser.add_argument("--force",
                        action="store_true",
                        help="Force reset without confirmation")
    # Argument to create mock competition data
    parser.add_argument("--mock-comp",
                        action="store_true",
                        help="Create mock competition data")
    # Argument to create default competition (for production)
    parser.add_argument(
        "--default-comp",
        action="store_true",
        help="Create default Spring Bouldering Festival competition "
        "(for production)")
    # Argument to skip boulder/route data import
    parser.add_argument("--skip-boulder-import",
                        action="store_true",
                        help="Skip importing boulder and route data")
    args = parser.parse_args()

    # Validate arguments - can't have both mock and default competition
    if args.mock_comp and args.default_comp:
        logger.error(
            "Cannot specify both --mock-comp and --default-comp. Choose one.")
        sys.exit(1)

    # Ask for confirmation if not --force argument
    if not args.force:
        response = input("Are you sure you want to reset the database? "
                         "All data will be lost! (y/n): ")
        if response.lower() != 'y':
            logger.info("Operation cancelled.")
            sys.exit(0)

    logger.info("Resetting database and recreating tables...")

    # First, reset the database (drop and create tables with crag data)
    create_db_and_tables(reset=True)
    logger.info("Database tables have been reset and recreated.")

    # Next, import boulder and route data (unless skipped)
    if not args.skip_boulder_import:
        logger.info("Importing boulder and route data from scraped files...")
        # Run the import boulder and route data function
        success = import_boulder_route_data()
        if success:
            logger.info("Boulder and route data import complete. "
                        "Re-uploading boulder photos...")
            # Run the re-upload photos function - reset_urls=False to avoid
            # resetting storage URLs as the tables are new
            success = reupload_boulder_photos(reset_urls=False)
            if success:
                logger.info("Boulder photos re-upload complete.")
            else:
                logger.warning("Failed to re-upload boulder photos.")
        else:
            logger.warning("Failed to import boulder and route data.")
            if args.mock_comp or args.default_comp:
                response = input(
                    "Do you want to continue with competition data import? "
                    "(y/n): ")
                if response.lower() != 'y':
                    logger.info("Competition data import cancelled.")
                    sys.exit(1)

    # Import mock competition data if requested
    if args.mock_comp:
        logger.info("Importing mock competition data...")
        from database.management.init_mock_comp import (
            initialize_mock_competition_data)

        with get_db_session() as session:
            # Import mock competition data
            initialize_mock_competition_data(session)
        logger.info("Mock competition data import complete.")

    # Import default competition data if requested (for production)
    if args.default_comp:
        logger.info(
            "Importing default Spring Bouldering Festival competition...")
        from database.management.init_default_comp import (
            initialize_default_competition)

        with get_db_session() as session:
            # Import default competition data
            initialize_default_competition(session)
        logger.info("Default competition data import complete.")

    logger.info("Database reset complete!")

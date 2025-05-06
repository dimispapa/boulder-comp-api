#!/usr/bin/env python
"""
Initialize all database tables with required data.

This script is used to set up a new database with both required core data
(crags, boulders, routes) and default competition data. It does not drop any
existing tables - for a complete reset, use reset_db.py.
"""
import argparse

from utils.loggers import logger
from database.management.base import create_db_and_tables, get_db_session
from database.management.init_crag_core import import_boulder_route_data
from database.management.init_boulder_photos import reupload_boulder_photos
from database.management.init_default_comp import (
    initialize_default_competition)
from database.management.init_default_workshops import (
    initialize_default_workshops)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize database with all required data.")
    parser.add_argument("--force",
                        action="store_true",
                        help="Skip confirmations")
    args = parser.parse_args()

    # Create tables if they don't exist (without resetting)
    create_db_and_tables(reset=False)

    # Import boulder and route data
    logger.info("Importing boulder and route data...")
    import_boulder_route_data()

    # Re-upload boulder photos
    logger.info("Re-uploading boulder photos...")
    reupload_boulder_photos(reset_urls=False)

    # Initialize default competition
    with get_db_session() as session:
        logger.info("Initializing default competition...")
        initialize_default_competition(session)

        logger.info("Initializing default workshops...")
        initialize_default_workshops(session)

    logger.info("Database initialization complete!")

"""
Utility script to create all database tables.

Run this script once to initialize the database schema.
"""
import argparse
# Import all models to ensure they are registered with SQLModel
from database.models import *  # noqa: F403, F401
from database.base import create_db_and_tables

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize database and recreate tables.")
    # Argument to create mock competition data
    parser.add_argument("--mock-comp",
                        action="store_true",
                        help="Create mock competition data")
    args = parser.parse_args()

    create_db_and_tables(mock_competition=args.mock_comp)

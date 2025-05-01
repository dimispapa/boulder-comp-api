"""
Utility script to create all database tables.

Run this script once to initialize the database schema.
"""
import argparse
# Import all models to ensure they are registered with SQLModel
from database.models import *  # noqa: F403, F401
from database.management.base import (
    create_db_and_tables,
    init_mock_competition_data,
    init_default_competition_data,
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize database and recreate tables.")
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
    args = parser.parse_args()

    # Validate arguments - can't have both mock and default competition
    if args.mock_comp and args.default_comp:
        raise ValueError(
            "Cannot specify both --mock-comp and --default-comp. Choose one.")

    create_db_and_tables()

    if args.mock_comp:
        init_mock_competition_data()
    elif args.default_comp:
        init_default_competition_data()

"""
Utility script to create all database tables.

Run this script once to initialize the database schema.
"""
# Import all models to ensure they are registered with SQLModel
from database.models import *  # noqa: F403, F401
from database.base import create_db_and_tables

if __name__ == "__main__":
    create_db_and_tables()

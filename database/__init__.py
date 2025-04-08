"""
Database package for the Boulder Competition API.
"""
# Import key database components for easier imports from other modules
from database.management.base import (  # noqa: F401
    get_db_session,
    create_db_and_tables,
    engine)

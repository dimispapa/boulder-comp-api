"""
Database package for the Boulder Competition API.
"""
# Import key database components for easier imports from other modules
from database.base import (get_db_session, create_db_and_tables,  # noqa: F401
                           engine)

"""
Database connection configuration using SQLModel with Neon DB.
"""
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine
from typing import Generator

# Load environment variables
load_dotenv()

# Get database connection details from environment variables
NEON_DB_URL = os.getenv("NEON_DB_URL")

if not NEON_DB_URL:
    raise ValueError("NEON_DB_URL environment variable is not set")

# Create SQLAlchemy engine
engine = create_engine(
    NEON_DB_URL,
    echo=os.getenv("DEBUG", "False").lower() == "true",
    # Connection pool settings
    pool_pre_ping=True,
    pool_recycle=300,  # Recycle connections every 5 minutes
)


def create_db_and_tables():
    """Create all tables defined by SQLModel models."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session."""
    return Session(engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Automatically closes the session when exiting the context.

    Example:
        with get_db_session() as session:
            session.add(model)
            session.commit()
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()

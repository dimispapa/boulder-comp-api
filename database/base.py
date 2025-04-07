"""
Database connection configuration using SQLModel with Neon DB.
"""
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine
from typing import Generator

from utils.loggers import logger

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


def drop_tables():
    """Drop all tables defined by SQLModel models."""

    # This will drop all tables in reverse dependency order
    SQLModel.metadata.drop_all(engine)
    logger.info("All database tables have been dropped")


def create_db_and_tables(reset=False):
    """
    Create all tables defined by SQLModel models and import initial data.

    Args:
        reset (bool): If True, drop all tables before creating them.

    """
    from database.models import competitions, crags, scoring, media  # noqa

    if reset:
        # Drop tables if reset is True
        drop_tables()

    # Create db tables based on models
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables have been created")

    # Import initial data
    with get_db_session() as session:
        # Import functions
        from .init_crag_config import initialize_crag_data

        # Import initial crag data
        initialize_crag_data(session)


def init_mock_competition_data():
    """
    Initialize the database with mock competition data.
    Separate function to allow more control over initialization workflow.
    """
    from .init_mock_comp import initialize_mock_competition_data

    with get_db_session() as session:
        initialize_mock_competition_data(session)
    logger.info("Mock competition data has been initialized")


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


def get_db():
    """
    FastAPI dependency for database sessions.

    This is different from get_db_session() which is a context manager.
    This function is specifically designed for FastAPI's dependency injection.
    """
    db = get_session()
    try:
        yield db
    finally:
        db.close()

"""Pytest configuration for scraper tests."""
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_debug_dir():
    """Ensure debug directory exists for test artifacts."""
    debug_dir = os.path.join(os.path.dirname(__file__), "debug")
    os.makedirs(debug_dir, exist_ok=True)
    return debug_dir

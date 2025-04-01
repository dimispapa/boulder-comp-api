"""Tests for general API endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.mark.api
def test_root_endpoint():
    """Test the root endpoint returns the expected message."""
    response = client.get("/")
    assert response.status_code == 200
    msg = "Boulder Competition API is running"
    assert response.json() == {"message": msg}

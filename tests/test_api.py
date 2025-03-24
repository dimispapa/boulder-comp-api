from fastapi.testclient import TestClient
import pytest
from main import app

# Initialize test client
client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns the expected message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Boulder Competition API is running"}


def test_scraper_endpoint_structure():
    """Test the basic structure of the scraper endpoint (not actual functionality)."""
    # We don't actually want to trigger a scraping task, just check the endpoint exists
    # This is a structure test only
    scrape_url = "https://27crags.com/crags/example"
    response = client.post("/api/scraper/scrape",
                           json={
                               "crag_url": scrape_url,
                               "update_db": False
                           })

    # We expect a 422 error since the URL is not real, but the endpoint exists
    # In a real test, you'd use a mock URL that works
    assert response.status_code in [200, 422]

    # If we got 200, make sure we got a task ID
    if response.status_code == 200:
        assert "task_id" in response.json()
        assert "status" in response.json()


def test_scoring_endpoint_structure():
    """Test the basic structure of the scoring endpoint (not actual functionality)."""
    # Similar to above, we're just testing the endpoint exists, not functionality
    response = client.post("/api/scoring/calculate",
                           json={
                               "competition_id": "test-comp-id",
                               "update_leaderboard": False
                           })

    # Since this is a fake competition ID, we might get an error
    # But the endpoint should still exist and accept the request structure
    assert response.status_code in [200, 422, 500]

    # If 200, check for task_id
    if response.status_code == 200:
        assert "task_id" in response.json()
        assert "status" in response.json()


# Add more comprehensive tests as you develop your API

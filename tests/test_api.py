from fastapi.testclient import TestClient
from main import app

# Initialize test client
client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns the expected message."""
    response = client.get("/")
    assert response.status_code == 200
    msg = "Boulder Competition API is running"
    assert response.json() == {"message": msg}


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
    """Test the basic structure of the scoring endpoint."""
    # Test Marathon category
    marathon_json = {
        "competition_id": "test-comp-id",
        "update_leaderboard": False,
        "category": "marathon"
    }
    marathon_url = "/api/scoring/calculate/test-comp-id"
    response = client.post(marathon_url, json=marathon_json)
    assert response.status_code in [200, 422, 500]
    if response.status_code == 200:
        assert "task_id" in response.json()
        assert "status" in response.json()

    # Test Boulder Beasts category
    boulder_beasts_json = {
        "competition_id": "test-comp-id",
        "update_leaderboard": False,
        "category": "boulder_beasts"
    }
    boulder_beasts_url = "/api/scoring/calculate/test-comp-id"
    response = client.post(boulder_beasts_url, json=boulder_beasts_json)
    assert response.status_code in [200, 422, 500]
    if response.status_code == 200:
        assert "task_id" in response.json()
        assert "status" in response.json()

    # Test both categories
    both_categories_json = {
        "competition_id": "test-comp-id",
        "update_leaderboard": False
    }
    both_categories_url = "/api/scoring/calculate/test-comp-id"
    response = client.post(both_categories_url, json=both_categories_json)
    assert response.status_code in [200, 422, 500]
    if response.status_code == 200:
        assert "task_id" in response.json()
        assert "status" in response.json()


def test_rankings_endpoint():
    """Test the rankings endpoint structure."""
    # Test Marathon category
    marathon_url = ("/api/scoring/rankings/test-comp-id?category=marathon")
    response = client.get(marathon_url)
    assert response.status_code in [200, 404, 500]
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "rankings" in data
        if data["rankings"]:
            rank = data["rankings"][0]
            assert "team_id" in rank
            assert "base_score" in rank
            assert "volume_score" in rank
            assert "unique_ascent_score" in rank
            assert "team_ascent_bonus" in rank
            assert "master_grade_bonus" in rank
            assert "total_score" in rank
            assert "rank" in rank

    # Test Boulder Beasts category
    boulder_beasts_url = (
        "/api/scoring/rankings/test-comp-id?category=boulder_beasts")
    response = client.get(boulder_beasts_url)
    assert response.status_code in [200, 404, 500]
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "rankings" in data
        if data["rankings"]:
            rank = data["rankings"][0]
            assert "participant_id" in rank
            assert "top_grades" in rank
            assert "total_score" in rank
            assert "rank" in rank

    # Test both categories
    response = client.get("/api/scoring/rankings/test-comp-id")
    assert response.status_code in [200, 404, 500]
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "marathon" in data
        assert "boulder_beasts" in data


def test_leaderboard_endpoint():
    """Test the leaderboard endpoint structure."""
    # Test Marathon category
    marathon_url = "/api/scoring/leaderboard/test-comp-id?category=marathon"
    response = client.get(marathon_url)
    assert response.status_code in [200, 404, 500]
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "data" in data
        leaderboard = data["data"]
        assert "competition_id" in leaderboard
        assert "category" in leaderboard
        assert leaderboard["category"] == "marathon"
        assert "teams" in leaderboard
        if leaderboard["teams"]:
            team = leaderboard["teams"][0]
            assert "team_id" in team
            assert "name" in team
            assert "score" in team
            assert "rank" in team

    # Test Boulder Beasts category
    boulder_beasts_url = (
        "/api/scoring/leaderboard/test-comp-id?category=boulder_beasts")
    response = client.get(boulder_beasts_url)
    assert response.status_code in [200, 404, 500]
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "data" in data
        leaderboard = data["data"]
        assert "competition_id" in leaderboard
        assert "category" in leaderboard
        assert leaderboard["category"] == "boulder_beasts"
        assert "participants" in leaderboard
        if leaderboard["participants"]:
            participant = leaderboard["participants"][0]
            assert "participant_id" in participant
            assert "name" in participant
            assert "score" in participant
            assert "rank" in participant
            assert "top_grades" in participant

    # Test both categories
    response = client.get("/api/scoring/leaderboard/test-comp-id")
    assert response.status_code in [200, 404, 500]
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "data" in data
        leaderboard = data["data"]
        assert "competition_id" in leaderboard
        assert "marathon" in leaderboard
        assert "boulder_beasts" in leaderboard
        assert "teams" in leaderboard["marathon"]
        assert "participants" in leaderboard["boulder_beasts"]
        assert "last_updated" in leaderboard


# Add more comprehensive tests as you develop your API

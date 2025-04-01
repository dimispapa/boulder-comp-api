"""
Tests for scraper API endpoints.

NOTE: These tests have been updated to support the new database schema that includes:
1. Crag and sector relationships
2. Boulder-sector mappings
3. Both name and display_name fields for entities
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from main import app

client = TestClient(app)


@pytest.fixture
def mock_celery_task():
    """Fixture to mock Celery task."""
    with patch("tasks.scraper_tasks.scrape_crag_task") as mock_task:
        # Configure the mock
        task_instance = MagicMock()
        task_instance.id = "mock-task-id"
        mock_task.delay.return_value = task_instance
        yield mock_task


@pytest.fixture
def mock_store_task():
    """Fixture to mock store Celery task."""
    with patch("tasks.scraper_tasks.store_crag_data_task") as mock_task:
        # Configure the mock
        task_instance = MagicMock()
        task_instance.id = "mock-store-task-id"
        mock_task.delay.return_value = task_instance
        yield mock_task


@pytest.fixture
def mock_scraped_files():
    """Fixture to mock scraped files."""
    with patch("pathlib.Path.glob") as mock_glob:
        # Create mock files for testing
        mock_file1 = MagicMock()
        mock_file1.name = "inia-droushia_20220101_120000.json"
        mock_file1.stat.return_value.st_size = 1024 * 10  # 10 KB
        mock_file1.stat.return_value.st_ctime = 1640995200  # 2022-01-01
        mock_file1.stat.return_value.st_mtime = 1640995200  # 2022-01-01
        mock_file1.__str__.return_value = (
            "data/scraped/inia-droushia_20220101_120000.json")

        mock_file2 = MagicMock()
        mock_file2.name = "inia-droushia_20220102_120000.json"
        mock_file2.stat.return_value.st_size = 1024 * 15  # 15 KB
        mock_file2.stat.return_value.st_ctime = 1641081600  # 2022-01-02
        mock_file2.stat.return_value.st_mtime = 1641081600  # 2022-01-02
        mock_file2.__str__.return_value = (
            "data/scraped/inia-droushia_20220102_120000.json")

        # Set up the mock to return our mock files
        mock_glob.return_value = [mock_file2, mock_file1]  # Newer first

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            yield mock_glob


@pytest.mark.api
def test_list_files_endpoint(mock_scraped_files):
    """Test listing scraped files."""
    # For this endpoint that doesn't use Celery tasks
    response = client.get("/api/scraper/list-files",
                          params={"crag_name": "inia-droushia"})

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert "files" in result
    assert len(result["files"]) == 2
    assert result["count"] == 2
    assert result["crag_filter"] == "inia-droushia"

    # Validate file details
    files = result["files"]
    assert files[0]["file_name"] == "inia-droushia_20220102_120000.json"
    assert files[1]["file_name"] == "inia-droushia_20220101_120000.json"
    assert files[0]["size_kb"] == 15.0
    assert "created" in files[0]
    assert "modified" in files[0]


@pytest.mark.api
def test_start_scraping_endpoint(monkey_patch_scraper_task):
    """Test the start scraping endpoint."""
    response = client.post("/api/scraper/start",
                           params={"crag_name": "test-crag"})

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["message"] == "Scraping task started"
    assert result["task_id"] == "mock-task-id"
    assert result["task_type"] == "scrape"


@pytest.mark.api
def test_store_data_endpoint_with_crag_name(monkey_patch_store_task,
                                            mock_scraped_files):
    """Test storing data using crag name."""
    # Mock the sector mapping function
    with patch("utils.supabase.get_boulder_mappings") as mock_mapping:
        # Setup a mock mapping dictionary that would be returned
        mock_mapping.return_value = {
            "https://27crags.com/crags/inia-droushia/boulders/arkham":
            "123e4567-e89b-12d3-a456-426614174000"  # Mock UUID
        }

        # Mock the Path.stat() method to prevent FileNotFoundError
        with patch("pathlib.Path.stat") as mock_stat:
            # Create a mock stat result
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 1024 * 20  # 20 KB
            mock_stat_result.st_ctime = 1640995200  # 2022-01-01
            mock_stat_result.st_mtime = 1640995200  # 2022-01-01
            mock_stat.return_value = mock_stat_result

            # Make the request
            response = client.post("/api/scraper/store",
                                   params={"crag_name": "inia-droushia"})

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["message"] == "Storage task started"
    assert result["task_id"] == "mock-store-task-id"
    assert "file_path" in result
    assert result["task_type"] == "store"


@pytest.mark.api
def test_store_data_endpoint_with_file_path(monkey_patch_store_task):
    """Test storing data using specific file path."""
    file_path = "data/scraped/test_file.json"

    # Mock the sector mapping function
    with patch("utils.supabase.get_boulder_mappings") as mock_mapping:
        # Setup a mock mapping dictionary that would be returned
        mock_mapping.return_value = {
            "https://27crags.com/crags/inia-droushia/boulders/arkham":
            "123e4567-e89b-12d3-a456-426614174000"  # Mock UUID
        }

        # Mock both Path.exists() and Path.stat() methods
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            with patch("pathlib.Path.stat") as mock_stat:
                # Create a mock stat result
                mock_stat_result = MagicMock()
                mock_stat_result.st_size = 1024 * 20  # 20 KB
                mock_stat_result.st_ctime = 1640995200  # 2022-01-01
                mock_stat_result.st_mtime = 1640995200  # 2022-01-01
                mock_stat.return_value = mock_stat_result

                # Make the request
                response = client.post("/api/scraper/store",
                                       params={"file_path": file_path})

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["message"] == "Storage task started"
    assert result["task_id"] == "mock-store-task-id"
    assert result["file_path"] == file_path
    assert result["task_type"] == "store"


@pytest.mark.api
def test_task_status_endpoint():
    """
    Test checking task status without requiring Redis.
    
    Updated to use mocking rather than requiring an actual Redis
    connection.
    """
    task_id = "mock-task-id"
    task_type = "scrape"

    # Mock the Celery AsyncResult
    with patch(
            "tasks.scraper_tasks.scrape_crag_task.AsyncResult") as mock_result:
        # Configure mock for a successful task
        mock_task = MagicMock()
        mock_task.state = "SUCCESS"
        mock_task.date_done = datetime.now()
        mock_task.successful.return_value = True
        mock_task.result = {
            "status": "success",
            "scraping_data": {
                "name": "test-crag",
                "boulders_count": 15,
                "file_path": "data/scraped/test-crag_20220101_120000.json"
            }
        }
        mock_result.return_value = mock_task

        # Make API call
        response = client.get(f"/api/scraper/status/{task_id}",
                              params={"task_type": task_type})

    # Validate response
    assert response.status_code == 200
    result = response.json()

    # Verify the response structure
    assert result["status"] == "success"
    assert result["task_id"] == task_id
    assert result["state"] == "SUCCESS"
    assert "date_completed" in result
    assert "result" in result
    assert result["result"]["status"] == "success"
    assert "scraping_data" in result["result"]
    assert result["result"]["scraping_data"]["name"] == "test-crag"
    assert result["result"]["scraping_data"]["boulders_count"] == 15

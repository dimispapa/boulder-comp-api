"""Tests for media API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app

client = TestClient(app)


@pytest.fixture
def mock_upload_task():
    """Fixture to mock the upload photos task."""
    with patch("tasks.media_tasks.upload_photos_task") as mock_task:
        # Configure the mock
        task_instance = MagicMock()
        task_instance.id = "mock-upload-task-id"
        mock_task.delay.return_value = task_instance
        yield mock_task


@pytest.mark.api
def test_upload_photos_endpoint(monkey_patch_upload_task):
    """Test the upload photos endpoint."""
    crag_name = "test-crag"

    # Test the endpoint with our monkey-patched task
    response = client.post(f"/api/media/upload-photos/{crag_name}")

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "started"
    assert result["task_id"] == "mock-upload-task-id"
    assert result["crag_name"] == crag_name
    assert "message" in result


@pytest.mark.api
def test_upload_status_pending():
    """Test checking photo upload status when task is pending."""
    task_id = "pending-task-id"

    with patch(
            "tasks.media_tasks.upload_photos_task.AsyncResult") as mock_result:
        # Configure mock for pending state
        mock_task = MagicMock()
        mock_task.state = "PENDING"
        mock_result.return_value = mock_task

        # Make API call
        response = client.get(f"/api/media/upload-photos/{task_id}/status")

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "pending"
    assert result["task_id"] == task_id
    assert result["message"] == "Task is pending"


@pytest.mark.api
def test_upload_status_in_progress():
    """Test checking photo upload status when task is in progress."""
    task_id = "in-progress-task-id"

    with patch(
            "tasks.media_tasks.upload_photos_task.AsyncResult") as mock_result:
        # Configure mock for in progress state
        mock_task = MagicMock()
        mock_task.state = "PROGRESS"
        mock_task.info = {
            "progress": 50,
            "total": 100,
            "message": "Processing photos"
        }
        mock_result.return_value = mock_task

        # Make API call
        response = client.get(f"/api/media/upload-photos/{task_id}/status")

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "in_progress"
    assert result["task_id"] == task_id
    assert result["progress"] == 50
    assert result["total"] == 100
    assert result["message"] == "Processing photos"


@pytest.mark.api
def test_upload_status_success():
    """Test checking photo upload status when task is successful."""
    task_id = "success-task-id"

    with patch(
            "tasks.media_tasks.upload_photos_task.AsyncResult") as mock_result:
        # Configure mock for success state
        mock_task = MagicMock()
        mock_task.state = "SUCCESS"
        mock_task.info = {
            "status": "success",
            "crag_name": "test-crag",
            "metrics": {
                "total_photos": 10,
                "uploaded": 8,
                "skipped": 2
            },
            "failures": []
        }
        mock_result.return_value = mock_task

        # Make API call
        response = client.get(f"/api/media/upload-photos/{task_id}/status")

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["task_id"] == task_id
    assert result["crag_name"] == "test-crag"
    assert "metrics" in result
    assert result["metrics"]["total_photos"] == 10
    assert "failures" in result


@pytest.mark.api
def test_upload_status_error():
    """Test checking photo upload status when task had an error."""
    task_id = "error-task-id"

    with patch(
            "tasks.media_tasks.upload_photos_task.AsyncResult") as mock_result:
        # Configure mock for error state
        mock_task = MagicMock()
        mock_task.state = "SUCCESS"  # Task completed but with error status
        mock_task.info = {
            "status": "error",
            "error": "Failed to access storage",
            "traceback": "Traceback details..."
        }
        mock_result.return_value = mock_task

        # Make API call
        response = client.get(f"/api/media/upload-photos/{task_id}/status")

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "error"
    assert result["task_id"] == task_id
    assert result["error"] == "Failed to access storage"
    assert "traceback" in result


@pytest.mark.api
def test_upload_status_failure():
    """Test checking photo upload status when task failed."""
    task_id = "failure-task-id"

    with patch(
            "tasks.media_tasks.upload_photos_task.AsyncResult") as mock_result:
        # Configure mock for failure state
        mock_task = MagicMock()
        mock_task.state = "FAILURE"
        mock_task.result = "Task execution failed"
        mock_result.return_value = mock_task

        # Make API call
        response = client.get(f"/api/media/upload-photos/{task_id}/status")

    # Validate response
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failed"
    assert result["task_id"] == task_id
    assert result["error"] == "Task execution failed"

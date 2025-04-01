"""Pytest configuration for API tests."""
import pytest


class MockTaskResult:
    """Mock for Celery task results."""

    def __init__(self, task_id, state="SUCCESS", info=None, result=None):
        self.id = task_id
        self.state = state
        self.info = info or {}
        self.result = result

    def ready(self):
        """Check if task is ready."""
        return self.state in ["SUCCESS", "FAILURE"]


@pytest.fixture
def monkey_patch_scraper_task(monkeypatch):
    """Patch the scrape_crag_task to return a predictable task ID."""

    # Create a mock task result
    task = MockTaskResult("mock-task-id")

    # Define the mock delay function
    def mock_delay(*args, **kwargs):
        return task

    # Apply the patch
    monkeypatch.setattr("tasks.scraper_tasks.scrape_crag_task.delay",
                        mock_delay)

    return task


@pytest.fixture
def monkey_patch_store_task(monkeypatch):
    """Patch the store_crag_data_task to return a predictable task ID."""

    # Create a mock task result
    task = MockTaskResult("mock-store-task-id")

    # Define the mock delay function
    def mock_delay(*args, **kwargs):
        return task

    # Apply the patch
    monkeypatch.setattr("tasks.scraper_tasks.store_crag_data_task.delay",
                        mock_delay)

    return task


@pytest.fixture
def monkey_patch_upload_task(monkeypatch):
    """Patch the upload_photos_task to return a predictable task ID."""

    # Create a mock task result
    task = MockTaskResult("mock-upload-task-id")

    # Define the mock delay function
    def mock_delay(*args, **kwargs):
        return task

    # Apply the patch
    monkeypatch.setattr("tasks.media_tasks.upload_photos_task.delay",
                        mock_delay)

    return task


@pytest.fixture
def monkey_patch_task_status(monkeypatch):
    """Patch the task status utility functions."""

    # Mock task instance
    mock_task = MockTaskResult("test-task-id")

    # Mock get_task_instance
    def mock_get_task_instance(task_id, task_type=None):
        return mock_task, task_type or "test_type"

    # Mock prepare_basic_result
    def mock_prepare_basic_result(task_id, task, task_type):
        return {
            "status": "SUCCESS",
            "task_id": task_id,
            "task_type": task_type
        }

    # Mock handle_completed_task
    def mock_handle_completed_task(task, result):
        return {
            "status": "SUCCESS",
            "task_id": result["task_id"],
            "result": {
                "some": "data"
            }
        }

    # Apply patches
    monkeypatch.setattr("utils.task_status.get_task_instance",
                        mock_get_task_instance)
    monkeypatch.setattr("utils.task_status.prepare_basic_result",
                        mock_prepare_basic_result)
    monkeypatch.setattr("utils.task_status.handle_completed_task",
                        mock_handle_completed_task)

    return {
        "mock_task": mock_task,
        "get_task_instance": mock_get_task_instance,
        "prepare_basic_result": mock_prepare_basic_result,
        "handle_completed_task": mock_handle_completed_task
    }

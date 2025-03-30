"""
Utility functions for handling task status operations.
"""
from celery.result import AsyncResult
from typing import Dict, Any, Tuple
from utils.general_utils import format_time_from_seconds

# Task type constants
TASK_TYPE_SCRAPE = "scrape"
TASK_TYPE_STORE = "store"

# Status constants
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"

# Task-specific status mapping
SCRAPE_STATUSES = ["saving_data", "data_saved", "save_error"]
STORE_STATUSES = ["storing_data", "data_stored", "storage_error"]
ERROR_STATUSES = ["save_error", "storage_error"]


def get_task_instance(task_id: str,
                      task_type: str = None) -> Tuple[AsyncResult, str]:
    """
    Get the appropriate task instance based on task_id and task_type.

    Args:
        task_id (str): The ID of the task
        task_type (str, optional): The type of task ("scrape" or "store")

    Returns:
        Tuple[AsyncResult, str]: The task instance and determined task type
    """
    from tasks.scraper_tasks import scrape_crag_task, store_crag_data_task

    if task_type == TASK_TYPE_STORE:
        return store_crag_data_task.AsyncResult(task_id), TASK_TYPE_STORE
    elif task_type == TASK_TYPE_SCRAPE:
        return scrape_crag_task.AsyncResult(task_id), TASK_TYPE_SCRAPE
    else:
        # Try both tasks to determine the type
        scrape_task = scrape_crag_task.AsyncResult(task_id)
        store_task = store_crag_data_task.AsyncResult(task_id)

        # Use the task that exists/has state
        if scrape_task.state != 'PENDING' or store_task.state == 'PENDING':
            return scrape_task, TASK_TYPE_SCRAPE
        else:
            return store_task, TASK_TYPE_STORE


def prepare_basic_result(task_id: str, task: AsyncResult,
                         task_type: str) -> Dict[str, Any]:
    """
    Prepare the basic result dictionary with task identification.

    Args:
        task_id (str): The ID of the task
        task (AsyncResult): The Celery task instance
        task_type (str): The type of task

    Returns:
        Dict[str, Any]: Basic result dictionary
    """
    return {
        "task_id": task_id,
        "task_type": task_type,
        "state": task.state,
    }


def handle_completed_task(task: AsyncResult,
                          base_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle processing of a completed task (successful or failed).

    Args:
        task (AsyncResult): The completed Celery task
        base_result (Dict[str, Any]): The base result dictionary to update

    Returns:
        Dict[str, Any]: Updated result dictionary
    """
    result = base_result.copy()

    # Add completion timestamp
    result["date_completed"] = (task.date_done.isoformat()
                                if task.date_done else None)

    if task.successful():
        # Handle successful task
        return handle_successful_task(task, result)
    else:
        # Handle failed task
        result["status"] = STATUS_FAILED
        result["error"] = str(task.result)

        # Add limited traceback if available
        if task.traceback:
            result["traceback"] = (task.traceback[-2000:] if len(
                task.traceback) > 2000 else task.traceback)
        return result


def handle_successful_task(task: AsyncResult,
                           base_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a successfully completed task result.

    Args:
        task (AsyncResult): The successful Celery task
        base_result (Dict[str, Any]): The base result dictionary to update

    Returns:
        Dict[str, Any]: Updated result dictionary
    """
    result = base_result.copy()
    task_result = task.result

    # Check if result is a dict with status key
    if isinstance(task_result, dict) and "status" in task_result:
        # Use the application-level status
        result["status"] = task_result["status"]

        if task_result["status"] == STATUS_ERROR:
            # Handle application-level error
            result["error"] = task_result.get("detail", str(task_result))

            # Copy any other error details
            for key, value in task_result.items():
                if key not in ["status"] and key not in result:
                    result[key] = value
        else:
            # For success statuses, include full result
            result["result"] = task_result
    else:
        # Default status if none in result
        result["status"] = STATUS_COMPLETED
        result["result"] = task_result

    return result


def handle_in_progress_task(task: AsyncResult, base_result: Dict[str, Any],
                            task_type: str) -> Dict[str, Any]:
    """
    Process information for a task that is still in progress.

    Args:
        task (AsyncResult): The in-progress Celery task
        base_result (Dict[str, Any]): The base result dictionary to update
        task_type (str): The type of task

    Returns:
        Dict[str, Any]: Updated result dictionary
    """
    result = base_result.copy()
    result["status"] = STATUS_IN_PROGRESS

    # Include task info if available
    if not task.info:
        return result

    result["progress_info"] = task.info

    # Update status based on task info if available
    if "status" in task.info:
        task_status = task.info["status"]

        # Use specific status if it's a known one
        if task_status in SCRAPE_STATUSES + STORE_STATUSES:
            result["status"] = task_status

            # Handle error statuses
            if task_status in ERROR_STATUSES and "error" in task.info:
                result["error"] = task.info["error"]

    # Format elapsed time if available
    if "elapsed_seconds" in task.info:
        seconds = task.info["elapsed_seconds"]
        result["progress_info"]["elapsed_time"] = format_time_from_seconds(
            seconds)

    # Calculate completion percentage and estimated time for scraping tasks
    if task_type == TASK_TYPE_SCRAPE:
        add_scraping_progress_info(task, result)

    return result


def add_scraping_progress_info(task: AsyncResult, result: Dict[str,
                                                               Any]) -> None:
    """
    Add scraping-specific progress information to the result, including
    completion percentage and estimated time remaining.

    Args:
        task (AsyncResult): The Celery task
        result (Dict[str, Any]): The result dictionary to update
    """
    # Check if we have the necessary boulder count information
    has_boulder_counts = ("total_boulders" in task.info
                          and "completed_boulders" in task.info
                          and task.info["total_boulders"] > 0)

    if not has_boulder_counts:
        return

    # Get the counts for calculations
    completed = task.info["completed_boulders"]
    total = task.info["total_boulders"]

    # Calculate completion percentage
    completion_percent = (completed / total) * 100
    result["progress_info"][
        "completion_percent"] = f"{completion_percent:.1f}%"

    # Calculate estimated time remaining if we have elapsed time
    if completed > 0 and "elapsed_seconds" in task.info:
        elapsed = task.info["elapsed_seconds"]

        # Calculate seconds per boulder
        sec_per_boulder = elapsed / completed

        # Estimate remaining seconds
        remaining_boulders = total - completed
        remaining_seconds = int(remaining_boulders * sec_per_boulder)

        # Format and add the remaining time
        remaining_time = format_time_from_seconds(remaining_seconds)
        result["progress_info"]["estimated_time_remaining"] = remaining_time

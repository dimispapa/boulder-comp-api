"""
Utility functions for handling task status operations.
"""
from celery.result import AsyncResult
from typing import Dict, Any, Tuple
from utils.general_utils import format_time_from_seconds

# Task type constants
TASK_TYPE_SCRAPE = "scrape"

# Status constants
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"

# Task-specific status mapping
SCRAPE_STATUSES = ["saving_data", "data_saved", "save_error"]
ERROR_STATUSES = ["save_error"]


def get_task_instance(task_id: str,
                      task_type: str = None) -> Tuple[AsyncResult, str]:
    """
    Get the appropriate task instance based on task_id and task_type.

    Args:
        task_id (str): The ID of the task
        task_type (str, optional): The type of task ("scrape")

    Returns:
        Tuple[AsyncResult, str]: The task instance and determined task type
    """
    from tasks.scraper_tasks import scrape_crag_task

    if task_type == TASK_TYPE_SCRAPE:
        return scrape_crag_task.AsyncResult(task_id), TASK_TYPE_SCRAPE
    else:
        # Only scrape task type is now supported
        return scrape_crag_task.AsyncResult(task_id), TASK_TYPE_SCRAPE


def prepare_basic_result(state: str, info: Dict,
                         task_type: str) -> Dict[str, Any]:
    """
    Prepare the basic result dictionary with task identification.

    Args:
        state (str): The state of the task
        info (Dict): Task info dictionary
        task_type (str): The type of task

    Returns:
        Dict[str, Any]: Basic result dictionary
    """
    return {"state": state, "task_type": task_type, "info": info}


def handle_completed_task(task: AsyncResult, task_type: str) -> Dict[str, Any]:
    """
    Handle processing of a completed task (successful or failed).

    Args:
        task (AsyncResult): The completed Celery task
        task_type (str): The type of task

    Returns:
        Dict[str, Any]: Updated result dictionary
    """
    result = {
        "state": task.state,
        "task_type": task_type,
        "date_completed":
        (task.date_done.isoformat() if task.date_done else None)
    }

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
                           result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a successfully completed task result.

    Args:
        task (AsyncResult): The successful Celery task
        result (Dict[str, Any]): The base result dictionary to update

    Returns:
        Dict[str, Any]: Updated result dictionary
    """
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

            # Add crag name if available
            if "crag_name" in task_result:
                result["crag_name"] = task_result["crag_name"]
    else:
        # Default status if none in result
        result["status"] = STATUS_COMPLETED
        result["result"] = task_result

    return result


def handle_in_progress_task(task: AsyncResult,
                            task_type: str) -> Dict[str, Any]:
    """
    Process information for a task that is still in progress.

    Args:
        task (AsyncResult): The in-progress Celery task
        task_type (str): The type of task

    Returns:
        Dict[str, Any]: Updated result dictionary
    """
    result = {
        "state": task.state,
        "task_type": task_type,
        "status": STATUS_IN_PROGRESS
    }

    # If the task has info
    if hasattr(task, 'info') and task.info:
        # Copy relevant info to the result
        info = task.info

        # Add progress status and message
        if 'status' in info:
            result['progress_status'] = info['status']
        if 'message' in info:
            result['message'] = info['message']

        # Add current/total progress counters
        if 'current' in info and 'total' in info:
            current = info['current']
            total = info['total']
            result['current'] = current
            result['total'] = total

            # Calculate and add percentage
            if total > 0:
                percentage = int(current / total * 100)
                result['percentage'] = percentage

            # Estimate time remaining if available
            if 'elapsed' in info and current > 0:
                elapsed = info['elapsed']
                result['elapsed'] = elapsed

                # Format elapsed time
                result['elapsed_formatted'] = format_time_from_seconds(elapsed)

                # Estimate remaining time
                if total > current:
                    remaining_items = total - current
                    avg_time_per_item = elapsed / current
                    estimated_remaining = remaining_items * avg_time_per_item
                    result['estimated_remaining'] = estimated_remaining
                    result['estimated_remaining_formatted'] = \
                        format_time_from_seconds(estimated_remaining)

        # Add more detailed progress info for scraping tasks
        if task_type == TASK_TYPE_SCRAPE:
            add_scraping_progress_info(task, result)

    return result


def add_scraping_progress_info(task: AsyncResult, result: Dict[str,
                                                               Any]) -> None:
    """
    Add detailed progress information specific to scraping tasks.

    Args:
        task (AsyncResult): The scraping Celery task
        result (Dict[str, Any]): The result dictionary to update
    """
    info = task.info or {}

    # Add boulder-specific info if available
    if 'boulder_name' in info:
        result['current_boulder'] = info['boulder_name']

    # Add sector info if available
    if 'sector_name' in info:
        result['current_sector'] = info['sector_name']

    # Add crag info if available
    if 'crag_name' in info:
        result['crag_name'] = info['crag_name']

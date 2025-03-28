"""
FastAPI router for the scraping endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from supabase import create_client
import os
from urllib.parse import urljoin
from dotenv import load_dotenv
import traceback

from utils.loggers import logger
from utils.time_utils import format_time_from_seconds
from tasks.scraper_tasks import scrape_crag_task

# Load environment variables
load_dotenv()
BASE_URL = os.getenv("CRAGS_BASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize router
router = APIRouter()

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@router.post("/start")
async def start_scraping(background_tasks: BackgroundTasks,
                         crag_name: str = "inia-droushia"):
    """
    Start scraping a crag from 27crags.com.

    Args:
        crag_name (str): Name of the crag to scrape.
        Defaults to 'inia-droushia'.

    Returns:
        dict: Status of the scraping task
    """
    try:
        crag_url = urljoin(BASE_URL, crag_name)
        logger.debug(f"API route started scraping crag: {crag_url}")

        # Use the proper registered task with the selected user agent
        task = scrape_crag_task.delay(crag_url)

        return {
            "status": "success",
            "message": "Scraping task started",
            "task_id": task.id
        }
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Failed to start scraping: {str(e)}")


@router.get("/status/{task_id}")
async def get_scraping_status(task_id: str):
    """
    Get the status of a scraping task.

    Args:
        task_id (str): ID of the task to check

    Returns:
        dict: Current status of the task
    """
    try:
        task = scrape_crag_task.AsyncResult(task_id)

        # Basic status information
        result = {
            "task_id": task_id,
            "state": task.state,
        }

        # Add more details based on task state
        if task.ready():
            result["date_completed"] = (task.date_done.isoformat()
                                        if task.date_done else None)

            if task.successful():
                # Check if result indicates an application-level error
                task_result = task.result

                # Check if result is a dict with status key
                if (isinstance(task_result, dict) and "status" in task_result):
                    # Use the application-level status
                    result["status"] = task_result["status"]

                    # Handle error status specially
                    if task_result["status"] == "error":
                        result["error"] = task_result.get(
                            "detail", str(task_result))
                        # Copy any other error details
                        for key, value in task_result.items():
                            if (key not in ["status"] and key not in result):
                                result[key] = value
                    else:
                        # For success statuses, include full result
                        result["result"] = task_result
                else:
                    # Default status if none in result
                    result["status"] = "completed"
                    result["result"] = task_result
            else:
                # Task failed at the Celery level
                result["status"] = "failed"
                result["error"] = str(task.result)

                # Add traceback if available
                if task.traceback:
                    # Limit traceback length
                    result["traceback"] = (task.traceback[-2000:] if len(
                        task.traceback) > 2000 else task.traceback)
        else:
            # For tasks in progress
            result["status"] = "in_progress"

            # Include any info the task might have published
            if task.info:
                result["progress_info"] = task.info

                # Use more specific status if available in the task info
                if "status" in task.info:
                    task_status = task.info["status"]
                    storage_statuses = [
                        "storing_data", "data_stored", "storage_error"
                    ]
                    if task_status in storage_statuses:
                        result["status"] = task_status

                        # If there was a storage error, include it as an error
                        storage_error = (task_status == "storage_error"
                                         and "error" in task.info)
                        if storage_error:
                            result["error"] = task.info["error"]

                # Format elapsed time if available
                if "elapsed_seconds" in task.info:
                    seconds = task.info["elapsed_seconds"]
                    result["progress_info"]["elapsed_time"] = (
                        format_time_from_seconds(seconds))

                # Calculate completion percentage
                has_boulder_counts = ("total_boulders" in task.info
                                      and "completed_boulders" in task.info
                                      and task.info["total_boulders"] > 0)
                if has_boulder_counts:
                    completed = task.info["completed_boulders"]
                    total = task.info["total_boulders"]
                    completion_percent = (completed / total) * 100
                    result["progress_info"]["completion_percent"] = (
                        f"{completion_percent:.1f}%")

        return result

    except Exception as e:
        # Provide detailed error about what went wrong
        error_traceback = traceback.format_exc()

        return {
            "status": "error",
            "error": f"Failed to get task status: {str(e)}",
            "traceback": error_traceback
        }

"""
FastAPI router for the scraping endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from supabase import create_client
import os
from urllib.parse import urljoin
from dotenv import load_dotenv
from utils.loggers import logger
from tasks.scraper_tasks import scrape_crag_data

# Load environment variables
load_dotenv()

# Initialize router
router = APIRouter()

# Initialize Supabase client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Default url domain and headers for 27crags
BASE_URL = os.getenv("27CRAGS_BASE_URL")
HEADERS = {'User-Agent': os.getenv("HEADERS_USER_AGENT")}


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
        # Ensure URL is properly constructed
        if not BASE_URL.endswith('/'):
            base_url = f"{BASE_URL}/"
        else:
            base_url = BASE_URL

        crag_url = urljoin(base_url, crag_name)
        logger.debug(f"API route started scraping crag: {crag_url}")

        # Use the proper registered task
        task = scrape_crag_data.delay(crag_url)

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

        task = scrape_crag_data.AsyncResult(task_id)

        # Basic status information
        result = {
            "task_id": task_id,
            "status": task.status,
            "state": task.state,
        }

        # Add more details based on task state
        if task.ready():
            result["date_completed"] = task.date_done.isoformat(
            ) if task.date_done else None

            if task.successful():
                result["result"] = task.result
                result["status"] = "completed"
            else:
                # Get more detailed error information
                result["status"] = "failed"
                result["error"] = str(task.result)

                # Add traceback if available
                if task.traceback:
                    # Limit traceback length to avoid huge responses
                    result["traceback"] = task.traceback[-2000:] if len(
                        task.traceback) > 2000 else task.traceback
        else:
            # For tasks in progress
            result["status"] = "in_progress"
            # Include any info the task might have published
            if task.info:
                result["progress_info"] = task.info

        return result

    except Exception as e:
        # Provide detailed error about what went wrong
        # in the status check itself
        import traceback
        error_traceback = traceback.format_exc()

        return {
            "status": "error",
            "error": f"Failed to get task status: {str(e)}",
            "traceback": error_traceback
        }

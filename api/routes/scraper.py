from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional
from tasks.scraper_tasks import scrape_crag_data
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()


# Request models
class ScrapeRequest(BaseModel):
    crag_url: HttpUrl
    update_db: bool = True
    crag_name: Optional[str] = None


# Response models
class ScrapeResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/scrape", response_model=ScrapeResponse)
async def start_scraping(request: ScrapeRequest,
                         background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Start a scraping task to extract boulder data from 27crags.
    
    The task runs asynchronously in the background.
    """
    try:
        # Convert HttpUrl to string for task input
        crag_url = str(request.crag_url)

        # Queue the task
        task = scrape_crag_data.delay(crag_url, request.update_db)

        logger.info(
            f"Scraping task initiated for {crag_url} with task ID: {task.id}")

        return {
            "task_id": task.id,
            "status": "initiated",
            "message": f"Scraping task for {crag_url} started successfully"
        }

    except Exception as e:
        logger.error(f"Error starting scraping task: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to start scraping task: {str(e)}")


@router.get("/task/{task_id}", response_model=Dict[str, Any])
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Check the status of a scraping task by task ID.
    """
    try:
        # Get task result
        task = scrape_crag_data.AsyncResult(task_id)

        if task.state == 'PENDING':
            response = {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is pending execution"
            }
        elif task.state == 'STARTED':
            response = {
                "task_id": task_id,
                "status": "in_progress",
                "message": "Task is currently in progress"
            }
        elif task.state == 'SUCCESS':
            response = {
                "task_id": task_id,
                "status": "completed",
                "message": "Task completed successfully",
                "result": task.result
            }
        elif task.state == 'FAILURE':
            response = {
                "task_id": task_id,
                "status": "failed",
                "message": f"Task failed: {str(task.result)}",
            }
        else:
            response = {
                "task_id": task_id,
                "status": task.state,
                "message": "Task status unknown"
            }

        return response

    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to get task status: {str(e)}")

"""
FastAPI router for the scraping endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from supabase import create_client
import os
from celery import shared_task

from scraper.core import CragScraper
from utils.loggers import logger

router = APIRouter()

# Initialize Supabase client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Default url domain and headers for 27crags
BASE_URL = os.getenv("27CRAGS_BASE_URL")
HEADERS = {'User-Agent': os.getenv("HEADERS_USER_AGENT")}


@shared_task
async def scrape_crag_task(crag_url: str):
    """Celery task to scrape a crag."""
    try:
        scraper = CragScraper(HEADERS, supabase)

        # Login with credentials from environment
        username = os.getenv("27CRAGS_USERNAME")
        password = os.getenv("27CRAGS_PASSWORD")

        if not username or not password:
            raise HTTPException(status_code=500,
                                detail="Missing 27crags credentials")

        if not await scraper.login(username, password):
            raise HTTPException(status_code=500,
                                detail="Failed to login to 27crags")

        # Start scraping
        await scraper.scrape_crag(crag_url)
        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "detail": str(e)}


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
        # Queue the scraping task
        url = f"{BASE_URL}/{crag_name}"
        logger.debug(f"API route started scraping crag: {url}")
        task = scrape_crag_task.delay(url)

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

        if task.ready():
            if task.successful():
                return {"status": "completed", "result": task.result}
            else:
                return {"status": "failed", "error": str(task.result)}
        else:
            return {"status": "in_progress"}

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Failed to get task status: {str(e)}")

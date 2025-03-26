"""
FastAPI router for the scraping endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from supabase import create_client
import os
from scraper.core import CragScraper
from celery import shared_task

router = APIRouter()

# Initialize Supabase client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Default headers for 27crags
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/126.0.0.0 Safari/537.36')
}


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
async def start_scraping(
        background_tasks: BackgroundTasks,
        crag_url: str = "https://27crags.com/crags/inia-droushia"):
    """
    Start scraping a crag from 27crags.com.
    
    Args:
        crag_url (str): URL of the crag to scrape. Defaults to Inia & Droushia.
        
    Returns:
        dict: Status of the scraping task
    """
    try:
        # Queue the scraping task
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

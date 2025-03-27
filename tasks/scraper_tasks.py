"""
Celery tasks for scraping data from 27crags.
"""
from tasks.celery_app import celery_app
from scraper.core import CragScraper
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Default headers for 27crags
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/126.0.0.0 Safari/537.36')
}


@celery_app.task(bind=True)
async def scrape_crag_data(self, crag_url: str):
    """
    Celery task to scrape data from a 27crags crag page.

    Args:
        crag_url (str): URL of the crag to scrape

    Returns:
        dict: Status and result of the scraping operation
    """
    try:
        # Initialize scraper
        scraper = CragScraper(HEADERS, supabase)

        # Login with credentials from environment
        username = os.getenv("27CRAGS_USERNAME")
        password = os.getenv("27CRAGS_PASSWORD")

        if not username or not password:
            return {"status": "error", "detail": "Missing 27crags credentials"}

        if not await scraper.login(username, password):
            return {"status": "error", "detail": "Failed to login to 27crags"}

        # Start scraping
        data = await scraper.scrape_crag(crag_url)

        return {"status": "success", "data": data}

    except Exception as e:
        return {"status": "error", "detail": str(e)}

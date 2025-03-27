"""
Celery tasks for scraping data from 27crags.
"""
from tasks.celery_app import celery_app
from scraper.core import CragScraper
from supabase import create_client
import os
from dotenv import load_dotenv
import traceback
import asyncio
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
def scrape_crag_data(self, crag_url: str):
    """
    Celery task to scrape data from a 27crags crag page.

    Args:
        crag_url (str): URL of the crag to scrape

    Returns:
        dict: Status and result of the scraping operation
    """
    try:
        # Run async code in a synchronous context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Initialize scraper
        scraper = CragScraper(HEADERS, supabase)

        # Run login asynchronously but in a synchronous wrapper
        username = os.getenv("27CRAGS_USERNAME")
        password = os.getenv("27CRAGS_PASSWORD")

        if not username or not password:
            return {"status": "error", "detail": "Missing 27crags credentials"}

        login_success = loop.run_until_complete(
            scraper.login(username, password))
        if not login_success:
            return {"status": "error", "detail": "Failed to login to 27crags"}

        # Run scraping asynchronously but in a synchronous wrapper
        data = loop.run_until_complete(scraper.scrape_crag(crag_url))

        loop.close()

        return {"status": "success", "data": data}

    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }

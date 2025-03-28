"""
Celery tasks for scraping data from 27crags.
"""
from tasks.celery_app import celery_app
from scraper.core import CragScraper
import os
from dotenv import load_dotenv
import traceback
import asyncio
import random

from scraper.models import Crag
from utils.supabase import get_supabase_client
from utils.time_utils import format_time_from_seconds

# Load environment variables
load_dotenv()

# Create a list of user agents for rotation
USER_AGENTS = [
    os.getenv("USER_AGENT_1"),
    os.getenv("USER_AGENT_2"),
    os.getenv("USER_AGENT_3"),
    os.getenv("USER_AGENT_4"),
    os.getenv("USER_AGENT_5")
]

# Remove any None values in case some weren't defined
USER_AGENTS = [ua for ua in USER_AGENTS if ua]

# Initialize Supabase client
supabase = get_supabase_client()


@celery_app.task(bind=True, name='tasks.scraper_tasks.scrape_crag_task')
def scrape_crag_task(self, crag_url: str):
    """
    Celery task to scrape data from a 27crags crag page.

    Args:
        crag_url (str): URL of the crag to scrape

    Returns:
        dict: Status and result of the scraping operation
    """
    # Create a variable to store the latest progress info
    progress_info = {}

    try:
        # Randomly select a user agent for this specific task
        selected_user_agent = random.choice(USER_AGENTS)
        headers = {'User-Agent': selected_user_agent}

        # Initialize scraper with the selected user agent
        scraper = CragScraper(headers, supabase)

        # Handle login synchronously
        username = os.getenv("CRAGS_USERNAME")
        password = os.getenv("CRAGS_PASSWORD")

        if not username or not password:
            return {"status": "error", "detail": "Missing 27crags credentials"}

        # Regular synchronous login
        login_success = scraper.login(username, password)

        if not login_success:
            return {"status": "error", "detail": "Failed to login to 27crags"}

        # Define a progress callback that also updates our local copy
        def update_progress(info):
            nonlocal progress_info
            progress_info = info  # Store the latest info locally
            self.update_state(state='PROGRESS', meta=info)

        # Create event loop for async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the async scraping with progress updates
        crag_data = loop.run_until_complete(
            scraper.scrape_crag(crag_url, progress_callback=update_progress))

        # Store the data in Supabase if it's a valid Crag object
        storage_result = None
        if isinstance(crag_data, Crag):
            update_progress({
                **progress_info, 'status': 'storing_data',
                'message': 'Scraping complete, storing data...'
            })

            # Use the utility function to store the data
            from utils.supabase import store_crag_data
            storage_result = loop.run_until_complete(
                store_crag_data(supabase, crag_data))

            # Update progress with storage result
            if storage_result["status"] == "success":
                update_progress({
                    **progress_info, 'status':
                    'data_stored',
                    'stored_boulders':
                    storage_result["stored_boulders"],
                    'stored_routes':
                    storage_result["stored_routes"]
                })
            else:
                update_progress({
                    **progress_info, 'status': 'storage_error',
                    'error': storage_result["detail"]
                })

        # Clean up the loop
        loop.close()

        # Use our local copy of progress info instead of self.info
        if (progress_info.get("total_boulders", 0) > 0
                and progress_info.get("completed_boulders", 0) > 0):

            total = progress_info["total_boulders"]
            completed = progress_info["completed_boulders"]
            elapsed = progress_info["elapsed_seconds"]

            # Only estimate if we have some progress
            if completed > 0:
                # Calculate seconds per boulder
                sec_per_boulder = elapsed / completed
                # Estimate remaining seconds
                remaining_boulders = total - completed
                remaining_seconds = int(remaining_boulders * sec_per_boulder)

                # Format remaining time
                remaining_time = format_time_from_seconds(remaining_seconds)
                progress_info["estimated_time_remaining"] = remaining_time

        # Return both scraping and storage results
        return {
            "status": "success",
            "scraping_data": {
                "name":
                crag_data.name if isinstance(crag_data, Crag) else None,
                "boulders_count":
                len(crag_data.boulders) if isinstance(crag_data, Crag) else 0
            },
            "storage_result": storage_result
        }

    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc(),
            "crag_url": crag_url
        }

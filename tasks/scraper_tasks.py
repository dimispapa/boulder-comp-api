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
import json
from pathlib import Path
from datetime import datetime

from scraper.models import Crag, Boulder, Route, BoulderPhoto, RouteLineData
from utils.supabase import get_admin_supabase_client, store_crag_data
from utils.loggers import logger

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

# Initialize Supabase client with admin privileges
supabase = get_admin_supabase_client()

# Create directory for storing scraped data
SCRAPED_DATA_DIR = Path("data/scraped")
SCRAPED_DATA_DIR.mkdir(parents=True, exist_ok=True)


@celery_app.task(bind=True, name='tasks.scraper_tasks.scrape_crag_task')
def scrape_crag_task(self, crag_name: str):
    """
    Celery task to scrape data from a 27crags crag page and
    save to a JSON file.

    Args:
        crag_name (str): Name of the crag to scrape

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
        scraper = CragScraper(headers, supabase, crag_name)

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
            scraper.scrape_crag(progress_callback=update_progress))

        # Clean up the loop
        loop.close()

        # Save data to a JSON file if it's a valid Crag object
        file_path = None
        if isinstance(crag_data, Crag):
            update_progress({
                **progress_info, 'status':
                'saving_data',
                'message':
                'Scraping complete, saving data to file...'
            })

            # Generate a unique filename
            crag_name = crag_data.name.lower().replace(' ', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = SCRAPED_DATA_DIR / f"{crag_name}_{timestamp}.json"

            # Save data to JSON file
            save_result = save_crag_to_json(crag_data, file_path)

            if save_result["status"] == "success":
                # Trigger the storage task
                store_crag_data_task.delay(str(file_path))

                update_progress({
                    **progress_info, 'status': 'data_saved',
                    'file_path': str(file_path),
                    'boulders_count': len(crag_data.boulders)
                })
            else:
                update_progress({
                    **progress_info, 'status': 'save_error',
                    'error': save_result["detail"]
                })

        # Return scraping results
        return {
            "status": "success",
            "scraping_data": {
                "name":
                crag_data.name if isinstance(crag_data, Crag) else None,
                "boulders_count":
                len(crag_data.boulders) if isinstance(crag_data, Crag) else 0,
                "file_path":
                str(file_path) if file_path else None
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc(),
            "crag_name": crag_name
        }


def save_crag_to_json(crag: Crag, file_path: Path) -> dict:
    """
    Save a Crag object to a JSON file.

    Args:
        crag (Crag): The crag object to save
        file_path (Path): Path where to save the JSON file

    Returns:
        dict: Status of the operation
    """
    try:
        # Log the absolute path we're trying to write to
        abs_path = file_path.absolute()
        logger.info(f"Attempting to save data to file: {abs_path}")

        # Check if directory exists and is writable
        dir_path = file_path.parent
        if not dir_path.exists():
            logger.warning(f"Directory does not exist: {dir_path}")
            logger.info(f"Creating directory: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)

        # Check write permissions
        if not os.access(str(dir_path), os.W_OK):
            logger.error(f"No write permission for directory: {dir_path}")
            return {
                "status": "error",
                "detail": f"No write permission for directory: {dir_path}"
            }

        # Add debug logging for photo data
        total_photos = sum(len(boulder.photos) for boulder in crag.boulders)
        total_lines = sum(
            len(route.line_data) for boulder in crag.boulders
            for route in boulder.routes)

        logger.info("Preparing to save crag data:")
        logger.info(f"- Total boulders: {len(crag.boulders)}")
        logger.info(f"- Total photos: {total_photos}")
        logger.info(f"- Total route lines: {total_lines}")

        # Convert Crag object to a serializable dictionary
        crag_dict = {
            "name":
            crag.name,
            "boulders": [{
                "name":
                boulder.name,
                "url":
                boulder.url,
                "gps_postgis":
                boulder.gps_postgis,
                "gps_string":
                boulder.gps_string,
                "photos": [{
                    "id": photo.id,
                    "url": photo.url,
                    "lines_data": photo.lines_data
                } for photo in boulder.photos],
                "routes": [{
                    "name":
                    route.name,
                    "url":
                    route.url,
                    "grade":
                    route.grade,
                    "rating":
                    route.rating,
                    "description":
                    route.description,
                    "line_data": [{
                        "photo_id": line.photo_id,
                        "line_points": line.line_points
                    } for line in route.line_data]
                } for route in boulder.routes]
            } for boulder in crag.boulders]
        }

        # Log sample of the data structure
        if crag.boulders:
            sample_boulder = crag.boulders[0]
            if sample_boulder.photos:
                logger.debug("Sample photo data structure:")
                logger.debug(
                    json.dumps(crag_dict["boulders"][0]["photos"][0],
                               indent=2))

        # Log file details before writing
        logger.info(
            f"Preparing to write {len(crag.boulders)} boulders to {file_path}")

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(crag_dict, f, ensure_ascii=False, indent=2)

        # Verify file was created
        if file_path.exists():
            file_size = file_path.stat().st_size
            logger.info(
                f"File successfully written: {file_path} ({file_size} bytes)")
        else:
            logger.error(f"File was not created: {file_path}")

        return {"status": "success", "file_path": str(file_path)}

    except Exception as e:
        logger.error(f"Error saving crag data to JSON: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }


@celery_app.task(bind=True, name='tasks.scraper_tasks.store_crag_data_task')
def store_crag_data_task(self, file_path: str):
    """
    Celery task to store previously scraped crag data to Supabase.

    Args:
        file_path (str): Path to the JSON file containing crag data

    Returns:
        dict: Status and result of the storage operation
    """
    try:
        # Load crag data from JSON file
        crag_data = load_crag_from_json(file_path)

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'storing_data',
                'message': 'Loading data from file and storing to database...'
            })

        # Store the data using the existing utility function
        storage_result = store_crag_data(crag_data, supabase)

        return {
            "status": "success",
            "file_path": file_path,
            "storage_result": storage_result
        }

    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc(),
            "file_path": file_path
        }


def load_crag_from_json(file_path: str) -> Crag:
    """
    Load a Crag object from a JSON file.

    Args:
        file_path (str): Path to the JSON file

    Returns:
        Crag: The reconstructed Crag object
    """
    try:
        # Read JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            crag_dict = json.load(f)

        # Recreate Boulder and Route objects
        boulders = []
        for boulder_dict in crag_dict["boulders"]:
            # Create BoulderPhoto objects
            photos = []
            if "photos" in boulder_dict:
                photos = [
                    BoulderPhoto(id=photo_dict["id"],
                                 url=photo_dict["url"],
                                 lines_data=photo_dict["lines_data"])
                    for photo_dict in boulder_dict["photos"]
                ]

            # Create Route objects with line data
            routes = []
            for route_dict in boulder_dict["routes"]:
                line_data = []
                if "line_data" in route_dict:
                    line_data = [
                        RouteLineData(photo_id=line_dict["photo_id"],
                                      line_points=line_dict["line_points"])
                        for line_dict in route_dict["line_data"]
                    ]

                route = Route(name=route_dict["name"],
                              url=route_dict["url"],
                              grade=route_dict["grade"],
                              rating=route_dict["rating"],
                              description=route_dict["description"],
                              line_data=line_data)
                routes.append(route)

            # Create Boulder object with routes and photos
            boulder = Boulder(name=boulder_dict["name"],
                              url=boulder_dict["url"],
                              gps_postgis=boulder_dict["gps_postgis"],
                              gps_string=boulder_dict["gps_string"],
                              routes=routes,
                              photos=photos)
            boulders.append(boulder)

        # Create and return Crag object
        return Crag(name=crag_dict["name"], boulders=boulders)

    except Exception as e:
        logger.error(f"Error loading crag data from JSON: {str(e)}")
        raise

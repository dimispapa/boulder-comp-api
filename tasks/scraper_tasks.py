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
from database.management.base import get_db_session
from utils.loggers import logger
from utils.cloudinary_uploader import CloudinaryUploader

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
        with get_db_session() as session:
            scraper = CragScraper(headers, session, crag_name)

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
                update_progress({
                    **progress_info, 'status':
                    'data_saved',
                    'file_path':
                    str(file_path),
                    'boulders_count':
                    len(crag_data.boulders),
                    'message':
                    'Data saved successfully. To import into the '
                    'database, use database/management/init_crag_core.py'
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
            "display_name":
            crag.display_name,
            "boulders": [{
                "name":
                boulder.name,
                "display_name":
                boulder.display_name,
                "url":
                boulder.url,
                "gps_postgis":
                boulder.gps_postgis,
                "gps_string":
                boulder.gps_string,
                "photos": [{
                    "id": photo.id,
                    "source_url": photo.source_url,
                    "order": photo.order,
                    "lines_data": photo.lines_data
                } for photo in boulder.photos],
                "routes": [{
                    "name":
                    route.name,
                    "display_name":
                    route.display_name,
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

        # Write to file with nice indentation for readability
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(crag_dict, f, indent=2, ensure_ascii=False)

        # Verify file was created
        if not file_path.exists():
            return {
                "status": "error",
                "detail": f"Failed to verify file was created: {file_path}"
            }

        # Log success
        logger.info(f"Successfully saved data to file: {file_path}")
        file_size_kb = round(file_path.stat().st_size / 1024, 2)
        logger.info(f"File size: {file_size_kb} KB")

        return {"status": "success", "file_path": str(file_path)}

    except Exception as e:
        logger.error(f"Error saving crag to JSON: {str(e)}")
        logger.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}


# For database management import
@celery_app.task(bind=True, name='tasks.scraper_tasks.store_crag_data_task')
def store_crag_data_task(self, file_path: str):
    """
    Celery task to store scraped crag data to the database.

    Note: This task is only meant to be called by the database
    management scripts, not directly through the API.

    Args:
        file_path (str): Path to the JSON file with scraped data

    Returns:
        dict: Status and result of the storage operation
    """
    from scraper.data_storage import store_crag_data

    try:
        # Validate and normalize file path
        file_path = Path(file_path)
        if not file_path.exists():
            return {
                "status": "error",
                "detail": f"File not found: {file_path}"
            }

        # Log file stats
        file_stat = file_path.stat()
        file_size_kb = round(file_stat.st_size / 1024, 2)
        logger.info(f"Loading data from file: {file_path}")
        logger.info(f"File size: {file_size_kb} KB")

        # Load data from JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check if the file has the expected structure
        if not isinstance(data, dict) or 'boulders' not in data:
            return {
                "status":
                "error",
                "detail":
                "Invalid file format. Expected a crag object with boulders."
            }

        # Convert JSON data back to Crag object
        crag = Crag(name=data.get('name', ''),
                    display_name=data.get('display_name', ''),
                    boulders=[])

        # Add boulders
        for boulder_data in data.get('boulders', []):
            boulder = Boulder(name=boulder_data.get('name', ''),
                              display_name=boulder_data.get(
                                  'display_name', ''),
                              url=boulder_data.get('url', ''),
                              gps_postgis=boulder_data.get('gps_postgis'),
                              gps_string=boulder_data.get('gps_string'),
                              photos=[],
                              routes=[])

            # Add photos
            for photo_data in boulder_data.get('photos', []):
                photo = BoulderPhoto(id=photo_data.get('id'),
                                     source_url=photo_data.get(
                                         'source_url', ''),
                                     order=photo_data.get('order', 0),
                                     lines_data=photo_data.get('lines_data'))
                boulder.photos.append(photo)

            # Add routes
            for route_data in boulder_data.get('routes', []):
                route = Route(name=route_data.get('name', ''),
                              display_name=route_data.get('display_name', ''),
                              url=route_data.get('url', ''),
                              grade=route_data.get('grade', ''),
                              rating=route_data.get('rating', 0.0),
                              description=route_data.get('description', ''),
                              line_data=[])

                # Add route line data
                for line_data in route_data.get('line_data', []):
                    line = RouteLineData(
                        photo_id=line_data.get('photo_id', ''),
                        line_points=line_data.get('line_points', []))
                    route.line_data.append(line)

                boulder.routes.append(route)

            crag.boulders.append(boulder)

        # Store to database
        with get_db_session() as session:
            # Call the store_crag_data function
            result = store_crag_data(crag, session)
            return result

    except Exception as e:
        logger.error(f"Error storing crag data: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "detail": f"Failed to store crag data: {str(e)}",
            "traceback": traceback.format_exc()
        }


@celery_app.task(bind=True,
                 name='tasks.scraper_tasks.upload_boulder_photos_task')
def upload_boulder_photos_task(self, crag_name: str):
    """
    Celery task to upload boulder photos for a crag to Cloudinary.

    This task is used by the upload_boulder_photos.py CLI script.

    Args:
        crag_name (str): Name of the crag to upload photos for

    Returns:
        dict: Status and result of the upload operation
    """
    try:
        progress_info = {}

        with get_db_session() as session:
            uploader = CloudinaryUploader(session)

            # Define a progress callback that also updates our local copy
            def update_progress(info):
                nonlocal progress_info
                progress_info = info
                self.update_state(state='PROGRESS', meta=info)

            # Upload photos with progress tracking
            result = uploader.upload_photos_for_crag(crag_name)

            logger.info(f"Photo upload complete for crag: {crag_name}")
            logger.info(f"Total: {result.get('total', 0)}, "
                        f"Uploaded: {result.get('uploaded', 0)}, "
                        f"Failed: {result.get('failed', 0)}")

            return {
                "status": "success",
                "crag_name": crag_name,
                "total_photos": result.get("total", 0),
                "uploaded_photos": result.get("uploaded", 0),
                "failed_photos": result.get("failed", 0)
            }

    except Exception as e:
        logger.error(f"Error uploading boulder photos: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "detail": f"Failed to upload boulder photos: {str(e)}",
            "traceback": traceback.format_exc()
        }

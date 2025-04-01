"""
FastAPI router for the scraping endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
import os
from dotenv import load_dotenv
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from utils.loggers import logger
from tasks.scraper_tasks import scrape_crag_task, store_crag_data_task
from utils.general_utils import extract_datetime_from_filename
from utils.task_status import (get_task_instance, prepare_basic_result,
                               handle_completed_task, handle_in_progress_task,
                               STATUS_ERROR)

# Load environment variables
load_dotenv()
BASE_URL = os.getenv("CRAGS_BASE_URL")

# Initialize router
router = APIRouter()


@router.post("/start")
async def start_scraping(background_tasks: BackgroundTasks,
                         crag_name: str = "inia-droushia") -> Dict[str, Any]:
    """
    Start scraping a crag from 27crags.com. It will scrape the crag and
    store the data in the database, while also storing the data in a JSON file
    in the data/scraped directory as a backup.

    Args:
        crag_name (str): Name of the crag to scrape.
        Defaults to 'inia-droushia'.

    Returns:
        dict: Status of the scraping task
    """
    try:
        logger.debug(f"API route started scraping crag: {crag_name}")

        # Use the proper registered task with the selected user agent
        task = scrape_crag_task.delay(crag_name)

        return {
            "status": "success",
            "message": "Scraping task started",
            "task_id": task.id,
            "task_type": "scrape"
        }
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Failed to start scraping: {str(e)}")


@router.post("/store")
async def start_storage(background_tasks: BackgroundTasks,
                        file_path: str = None,
                        crag_name: str = "inia-droushia") -> Dict[str, Any]:
    """
    Start storing previously scraped crag data to the database.

    Args:
        file_path (str, optional): Path to the JSON file to store.
        If not provided, will use the most recent file for
        the given crag name.
        crag_name (str, optional): Name of the crag to find the most
        recent file for. Only used if file_path is not provided.
        Defaults to 'inia-droushia'.

    Returns:
        dict: Status of the storage task
    """
    try:
        # If no file path is provided,
        # find the most recent one for the given crag
        if not file_path:
            if not crag_name:
                raise HTTPException(
                    status_code=400,
                    detail="Either file_path or crag_name must be provided")

            # Format crag name to match file naming pattern
            formatted_crag_name = crag_name.lower().replace(' ', '_')
            logger.info(f"Finding most recent file for crag: {crag_name}")

            # Get all matching files
            data_dir = Path("data/scraped")
            pattern = f"{formatted_crag_name}_*.json"
            matching_files = list(data_dir.glob(pattern))

            if not matching_files:
                logger.error(f"No data files found for crag: {crag_name}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No scraped data found for crag: {crag_name}")

            # Log all found files with creation date and embedded timestamp
            logger.info(f"Found {len(matching_files)} matching files:")
            for i, file in enumerate(matching_files, 1):
                embedded_date = extract_datetime_from_filename(file)
                logger.info(
                    f"  {i}. {file.name} - Created: "
                    f"{datetime.fromtimestamp(
                        file.stat().st_ctime).isoformat()} - "
                    f"Embedded timestamp: {embedded_date.isoformat()}")

            # Sort by the timestamp embedded in the filename (YYYYMMDD_HHMMSS)
            matching_files.sort(key=extract_datetime_from_filename,
                                reverse=True)
            file_path = str(matching_files[0])
            logger.info(
                f"Selected most recent file by embedded timestamp: {file_path}"
            )

        # Verify the file exists
        if not Path(file_path).exists():
            logger.error(f"Specified file does not exist: {file_path}")
            raise HTTPException(status_code=404,
                                detail=f"File not found: {file_path}")

        # Log file stats
        file_stat = Path(file_path).stat()
        file_size_kb = round(file_stat.st_size / 1024, 2)
        created_time = datetime.fromtimestamp(file_stat.st_ctime).isoformat()
        modified_time = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        embedded_timestamp = extract_datetime_from_filename(
            file_path).isoformat()

        logger.info(f"Initiating storage from file: {file_path}")
        logger.info(f"File details - Size: {file_size_kb} KB, "
                    f"Created: {created_time}, "
                    f"Modified: {modified_time}, "
                    f"Embedded timestamp: {embedded_timestamp}")

        # Start the storage task
        task = store_crag_data_task.delay(file_path)
        logger.info(f"Storage task started with ID: {task.id}")

        return {
            "status": "success",
            "message": "Storage task started",
            "task_id": task.id,
            "file_path": file_path,
            "task_type": "store"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start storage task: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500,
                            detail=f"Failed to start storage task: {str(e)}")


@router.get("/list-files")
async def list_scraped_files(
        crag_name: str = "inia-droushia") -> Dict[str, Any]:
    """
    List all scraped data files, optionally filtered by crag name.

    Args:
        crag_name (str, optional): Filter files for a specific crag
        Defaults to 'inia-droushia'.
    Returns:
        dict: List of available scraped data files
    """
    try:
        data_dir = Path("data/scraped")

        # Determine the pattern based on whether a crag name was provided
        if crag_name:
            formatted_crag_name = crag_name.lower().replace(' ', '_')
            pattern = f"{formatted_crag_name}_*.json"
        else:
            pattern = "*.json"

        # Get all matching files
        matching_files = list(data_dir.glob(pattern))
        logger.info(f"Found {len(matching_files)} matching files:")
        for i, file in enumerate(matching_files, 1):
            embedded_date = extract_datetime_from_filename(file)
            logger.info(
                f"  {i}. {file.name} - Created: "
                f"{datetime.fromtimestamp(
                    file.stat().st_ctime).isoformat()} - "
                f"Embedded timestamp: {embedded_date.isoformat()}")

        # Format the results
        files = []
        for file_path in matching_files:
            # Get file stats
            stats = file_path.stat()
            embedded_timestamp = extract_datetime_from_filename(file_path)
            files.append({
                "file_name":
                file_path.name,
                "file_path":
                str(file_path),
                "size_kb":
                round(stats.st_size / 1024, 2),
                "created":
                datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified":
                datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "embedded_timestamp":
                embedded_timestamp.isoformat(),
            })

        # Sort by embedded timestamp (newest first)
        files.sort(key=lambda x: x["embedded_timestamp"], reverse=True)

        return {
            "status": "success",
            "files": files,
            "count": len(files),
            "crag_filter": crag_name
        }
    except Exception as e:
        logger.error(f"Failed to list scraped files: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500,
                            detail=f"Failed to list scraped files: {str(e)}")


@router.get("/status/{task_id}")
async def get_task_status(task_id: str, task_type: str = None):
    """
    Get the status of a task.

    Args:
        task_id (str): ID of the task to check
        task_type (str, optional): Type of task ('scrape' or 'store')
            If not provided, will try to determine automatically

    Returns:
        dict: Current status of the task
    """
    try:
        # Get the appropriate task instance
        task, determined_task_type = get_task_instance(task_id, task_type)

        # Prepare basic result
        result = prepare_basic_result(task_id, task, determined_task_type)

        # Process based on task state
        if task.ready():
            return handle_completed_task(task, result)
        else:
            return handle_in_progress_task(task, result, determined_task_type)

    except Exception as e:
        # Provide detailed error about what went wrong
        error_traceback = traceback.format_exc()

        return {
            "status": STATUS_ERROR,
            "error": f"Failed to get task status: {str(e)}",
            "traceback": error_traceback
        }

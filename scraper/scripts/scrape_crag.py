#!/usr/bin/env python3
"""
Script to scrape a crag from 27crags.com.
This script will scrape crag data and store it in JSON format.
It can optionally upload boulder photos to Cloudinary after scraping.
"""
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import traceback

# Get project root and add to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Now we can import our project modules
from tasks.scraper_tasks import scrape_crag_task  # noqa
from utils.task_status import get_task_instance  # noqa
from utils.loggers import logger  # noqa


def monitor_task(task_id, verbose=False, timeout=3600):
    """
    Monitor a Celery task's progress until completion or timeout.

    Args:
        task_id (str): ID of the task to monitor
        verbose (bool): Whether to print verbose progress information
        timeout (int): Maximum time to wait for task completion (in seconds)

    Returns:
        dict: Task result
    """
    start_time = time.time()
    last_status = None

    while time.time() - start_time < timeout:
        # Get task instance
        task, task_type = get_task_instance(task_id)

        # Get current status
        if task.state == 'PROGRESS' and task.info:
            current_status = task.info.get('status', task.state)

            # Print progress information if verbose and status changed
            if verbose and current_status != last_status:
                if (current_status == 'scraping_boulders'
                        and 'current' in task.info and 'total' in task.info):
                    current = task.info['current']
                    total = task.info['total']
                    percentage = int(current / total * 100) if total > 0 else 0
                    logger.info(
                        f"Scraping boulders: {current}/{total} ({percentage}%)"
                    )
                elif (current_status == 'scraping_boulder_details'
                      and 'boulder_name' in task.info):
                    logger.info("Scraping details for boulder: "
                                f"{task.info['boulder_name']}")
                elif 'message' in task.info:
                    logger.info(f"{current_status}: {task.info['message']}")
                else:
                    logger.info(f"Status: {current_status}")

                last_status = current_status

        # Check if task is done
        if task.ready():
            result = task.result
            if verbose:
                if result.get('status') == 'success':
                    file_path = result.get('scraping_data',
                                           {}).get('file_path')
                    boulders_count = result.get('scraping_data',
                                                {}).get('boulders_count', 0)
                    logger.info(
                        f"Scraping completed successfully. File: {file_path}")
                    logger.info(f"Total boulders: {boulders_count}")
                else:
                    logger.info(f"Scraping failed: "
                                f"{result.get('detail', 'Unknown error')}")
            return result

        # Sleep before checking again
        time.sleep(1)

    # Timeout reached
    return {
        "status": "error",
        "message": f"Monitoring timed out after {timeout} seconds"
    }


def upload_photos(crag_name, verbose=False, timeout=1800):
    """
    Upload boulder photos for the specified crag.

    Args:
        crag_name (str): Name of the crag to upload photos for
        verbose (bool): Whether to print verbose progress information
        timeout (int): Maximum time to wait for task completion (in seconds)

    Returns:
        bool: True if upload was successful, False otherwise
    """
    script_path = Path(__file__).parent / "upload_boulder_photos.py"

    if not script_path.exists():
        logger.error(f"Error: Upload script not found at {script_path}")
        return False

    cmd = [sys.executable, str(script_path), crag_name]
    if verbose:
        cmd.append("--verbose")
    if timeout != 1800:
        cmd.extend(["--timeout", str(timeout)])

    try:
        logger.info(f"Starting photo upload for crag: {crag_name}")
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Error uploading photos: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading photos: {str(e)}")
        return False


def main():
    """Main entry point for the script."""
    # Load environment variables
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Scrape data from a 27crags crag page.')
    parser.add_argument(
        'crag_name',
        type=str,
        help='Name of the crag to scrape (e.g. "inia-droushia")')
    parser.add_argument('--verbose',
                        '-v',
                        action='store_true',
                        help='Print verbose progress information')
    parser.add_argument(
        '--timeout',
        '-t',
        type=int,
        default=3600,
        help='Maximum time to wait for task completion (in seconds)')
    parser.add_argument('--upload-photos',
                        '-u',
                        action='store_true',
                        help='Upload boulder photos after scraping')

    args = parser.parse_args()

    try:
        # Start the scrape task using the existing celery task
        if args.verbose:
            logger.info(f"Starting scraping task for crag: {args.crag_name}")

        task = scrape_crag_task.delay(args.crag_name)

        if args.verbose:
            logger.info(f"Task started with ID: {task.id}")

        # Monitor the task until completion
        result = monitor_task(task.id, args.verbose, args.timeout)

        # Print final result as JSON if not verbose
        if not args.verbose:
            print(json.dumps(result, indent=2))

        # Return error code if scraping failed
        if result.get("status") != "success":
            sys.exit(1)

        # Upload photos if requested
        if args.upload_photos:
            if args.verbose:
                logger.info("Scraping complete. Starting photo upload...")

            upload_success = upload_photos(args.crag_name,
                                           verbose=args.verbose,
                                           timeout=args.timeout)

            if not upload_success:
                logger.error("Photo upload failed")
                sys.exit(1)

            if args.verbose:
                logger.info("Photo upload completed successfully")

        sys.exit(0)

    except Exception as e:
        logger.error(f"Error executing scraping task: {str(e)}")
        logger.error(traceback.format_exc())

        if args.verbose:
            logger.error(f"Error executing scraping task: {str(e)}")
        else:
            error_result = {
                "status": "error",
                "message": f"Failed to execute scraping task: {str(e)}",
                "detail": traceback.format_exc()
            }
            print(json.dumps(error_result, indent=2))

        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script to upload boulder photos for a crag to Cloudinary.
"""
import sys
import json
import time
import argparse
from dotenv import load_dotenv
import traceback
from pathlib import Path

# Get project root and add to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from tasks.scraper_tasks import upload_boulder_photos_task  # noqa
from utils.task_status import get_task_instance  # noqa
from utils.loggers import logger  # noqa


def monitor_task(task_id, verbose=False, timeout=1800):
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
        task, _ = get_task_instance(task_id)

        # Get current status
        if task.state == 'PROGRESS' and task.info:
            current_status = task.info.get('status', task.state)

            # Print progress information if verbose and status changed
            if verbose and current_status != last_status:
                if 'current' in task.info and 'total' in task.info:
                    current = task.info['current']
                    total = task.info['total']
                    percentage = int(current / total * 100) if total > 0 else 0
                    print(
                        f"Uploading photos: {current}/{total} ({percentage}%)")
                elif 'message' in task.info:
                    print(f"{current_status}: {task.info['message']}")
                else:
                    print(f"Status: {current_status}")

                last_status = current_status

        # Check if task is done
        if task.ready():
            result = task.result
            if verbose:
                if result.get('status') == 'success':
                    total = result.get('total_photos', 0)
                    uploaded = result.get('uploaded_photos', 0)
                    failed = result.get('failed_photos', 0)
                    print("Upload completed successfully")
                    print(f"Total photos: {total}")
                    print(f"Uploaded photos: {uploaded}")
                    print(f"Failed photos: {failed}")
                else:
                    print(f"Upload failed: "
                          f"{result.get('detail', 'Unknown error')}")
            return result

        # Sleep before checking again
        time.sleep(1)

    # Timeout reached
    return {
        "status": "error",
        "message": f"Monitoring timed out after {timeout} seconds"
    }


def main():
    """Main entry point for the script."""
    # Load environment variables
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Upload boulder photos for a crag to Cloudinary.')
    parser.add_argument(
        'crag_name',
        type=str,
        help='Name of the crag to upload photos for (e.g. "inia-droushia")')
    parser.add_argument('--verbose',
                        '-v',
                        action='store_true',
                        help='Print verbose information')
    parser.add_argument(
        '--timeout',
        '-t',
        type=int,
        default=1800,
        help='Maximum time to wait for task completion (in seconds)')

    args = parser.parse_args()

    try:
        # Start the upload task using the existing celery task
        if args.verbose:
            print(f"Starting photo upload for crag: {args.crag_name}")

        task = upload_boulder_photos_task.delay(args.crag_name)

        if args.verbose:
            print(f"Task started with ID: {task.id}")

        # Monitor the task until completion
        result = monitor_task(task.id, args.verbose, args.timeout)

        # Print final result as JSON if not verbose
        if not args.verbose:
            print(json.dumps(result, indent=2))

        # Return appropriate exit code
        sys.exit(0 if result.get("status") == "success" else 1)

    except Exception as e:
        logger.error(f"Error executing upload task: {str(e)}")
        logger.error(traceback.format_exc())

        if args.verbose:
            print(f"Error executing upload task: {str(e)}")
        else:
            error_result = {
                "status": "error",
                "message": f"Failed to execute upload task: {str(e)}",
                "detail": traceback.format_exc()
            }
            print(json.dumps(error_result, indent=2))

        sys.exit(1)


if __name__ == "__main__":
    main()

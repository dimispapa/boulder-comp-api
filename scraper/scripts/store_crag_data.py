#!/usr/bin/env python3
"""
Script to store scraped crag data from a JSON file to the database.

"""
import sys
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
import traceback

# Get project root and add to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from tasks.scraper_tasks import store_crag_data_task  # noqa
from utils.task_status import get_task_instance  # noqa
from utils.loggers import logger  # noqa
from utils.general_utils import get_most_recent_json_file  # noqa


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
        task, task_type = get_task_instance(task_id, "store")

        # Get current status
        if task.state == 'PROGRESS' and task.info:
            current_status = task.info.get('status', task.state)

            # Print progress information if verbose and status changed
            if verbose and current_status != last_status:
                if (current_status == 'storing_data' and 'current' in task.info
                        and 'total' in task.info):
                    current = task.info['current']
                    total = task.info['total']
                    entity = task.info.get('entity', '')
                    percentage = int(current / total * 100) if total > 0 else 0
                    print(f"Processing {entity}: {current}/{total}"
                          f" ({percentage}%)")
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
                    boulders = result.get('storage_result',
                                          {}).get('boulders_count', 0)
                    routes = result.get('storage_result',
                                        {}).get('routes_count', 0)
                    photos = result.get('storage_result',
                                        {}).get('photos_count', 0)
                    print("Storage completed successfully")
                    print(f"Boulders: {boulders}")
                    print(f"Routes: {routes}")
                    print(f"Photos: {photos}")
                else:
                    print("Storage failed: "
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
        description='Store scraped crag data to the database.')
    parser.add_argument('--file',
                        '-f',
                        type=str,
                        help='Path to the JSON file to store')
    parser.add_argument(
        '--crag',
        '-c',
        type=str,
        help='Name of the crag to find the most recent file for')
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
        # Determine file path
        file_path = args.file
        if not file_path:
            if not args.crag:
                print("Error: Either --file or --crag must be provided")
                sys.exit(1)

            # Find the most recent file for the crag
            try:
                file_path = get_most_recent_json_file(crag_name=args.crag)
                if args.verbose:
                    print(
                        f"Using most recent file for {args.crag}: {file_path}")
            except Exception as e:
                print(
                    f"Error finding most recent file for {args.crag}: {str(e)}"
                )
                sys.exit(1)

        # Verify the file exists
        path = Path(file_path)
        if not path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            print(error_msg)
            sys.exit(1)

        # Log file stats if verbose
        if args.verbose:
            file_stat = path.stat()
            file_size_kb = round(file_stat.st_size / 1024, 2)
            print(f"File: {path}")
            print(f"Size: {file_size_kb} KB")
            print("Starting storage task...")

        # Start the storage task using the existing celery task
        task = store_crag_data_task.delay(str(path))

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
        logger.error(f"Error executing storage task: {str(e)}")
        logger.error(traceback.format_exc())

        if args.verbose:
            print(f"Error executing storage task: {str(e)}")
        else:
            error_result = {
                "status": "error",
                "message": f"Failed to execute storage task: {str(e)}",
                "detail": traceback.format_exc()
            }
            print(json.dumps(error_result, indent=2))

        sys.exit(1)


if __name__ == "__main__":
    main()

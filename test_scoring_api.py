#!/usr/bin/env python
"""
Test script for scoring calculator API endpoints.
This script tests the scoring calculator with the mock competition data.
"""
import argparse
import requests
import json
import time
from typing import Dict, Any


def calculate_scores(base_url: str,
                     comp_id: str,
                     category: str = None) -> Dict[str, Any]:
    """
    Trigger score calculation for a competition.

    Args:
        base_url: Base URL of the API
        comp_id: ID of the competition
        category: Optional category to calculate
                  ('marathon' or 'boulder_beasts')

    Returns:
        Dict: Response data including task_id
    """
    url = f"{base_url}/scoring/calculate"

    # Prepare request payload
    payload = {"competition_id": comp_id, "update_leaderboard": True}

    if category:
        payload["category"] = category

    # Make API request
    print(f"Triggering score calculation for competition {comp_id}...")
    if category:
        print(f"Calculating scores for category: {category}")

    response = requests.post(url, json=payload)

    # Check response
    if response.status_code == 200:
        result = response.json()
        print(f"Score calculation started. Task ID: {result.get('task_id')}")
        return result
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {"status": "error", "message": response.text}


def check_task_status(base_url: str, task_id: str) -> Dict[str, Any]:
    """
    Check the status of a calculation task.

    Args:
        base_url: Base URL of the API
        task_id: ID of the calculation task

    Returns:
        Dict: Task status information
    """
    url = f"{base_url}/scoring/status/{task_id}"

    response = requests.get(url)

    if response.status_code == 200:
        result = response.json()
        return result
    else:
        print(
            f"Error checking task status: {response.status_code} "
            f"- {response.text}"
        )
        return {"status": "error", "message": response.text}


def get_rankings(base_url: str, comp_id: str) -> Dict[str, Any]:
    """
    Get rankings data for a competition.

    Args:
        base_url: Base URL of the API
        comp_id: ID of the competition

    Returns:
        Dict: Rankings data
    """
    url = f"{base_url}/scoring/rankings/{comp_id}"

    response = requests.get(url)

    if response.status_code == 200:
        result = response.json()
        return result
    else:
        print(
            f"Error getting rankings: {response.status_code} "
            f"- {response.text}"
        )
        return {"status": "error", "message": response.text}


def get_leaderboard(base_url: str, comp_id: str) -> Dict[str, Any]:
    """
    Get formatted leaderboard data for a competition.

    Args:
        base_url: Base URL of the API
        comp_id: ID of the competition

    Returns:
        Dict: Leaderboard data
    """
    url = f"{base_url}/scoring/leaderboard/{comp_id}"

    response = requests.get(url)

    if response.status_code == 200:
        result = response.json()
        return result
    else:
        print(
            f"Error getting leaderboard: {response.status_code} "
            f"- {response.text}"
        )
        return {"status": "error", "message": response.text}


def wait_for_task_completion(base_url: str,
                             task_id: str,
                             max_wait_seconds: int = 60) -> Dict[str, Any]:
    """
    Wait for a task to complete, with status updates.

    Args:
        base_url: Base URL of the API
        task_id: ID of the calculation task
        max_wait_seconds: Maximum time to wait in seconds

    Returns:
        Dict: Final task status
    """
    print(f"Waiting for task {task_id} to complete...")

    start_time = time.time()
    status_result = {"status": "PENDING"}

    while status_result.get("status") in ["PENDING", "STARTED"]:
        if time.time() - start_time > max_wait_seconds:
            print(
                f"Timeout waiting for task to complete after "
                f"{max_wait_seconds} seconds"
            )
            return {"status": "timeout"}

        status_result = check_task_status(base_url, task_id)
        status = status_result.get("status", "UNKNOWN")

        print(f"Task status: {status}")

        if status in ["SUCCESS", "FAILURE", "REVOKED"]:
            break

        # Wait before checking again
        time.sleep(2)

    return status_result


def display_results(data: Dict[str, Any], title: str) -> None:
    """
    Display formatted results.

    Args:
        data: Data to display
        title: Title for the data section
    """
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)
    print(json.dumps(data, indent=2))
    print("=" * 80)


def run_complete_test(base_url: str, comp_id: str) -> None:
    """
    Run a complete test of the scoring calculator API.

    Args:
        base_url: Base URL of the API
        comp_id: ID of the competition
    """
    # 1. Calculate scores for both categories
    result = calculate_scores(base_url, comp_id)

    # 2. Wait for task to complete
    if result.get("status") == "success":
        task_id = result.get("task_id")
        final_status = wait_for_task_completion(base_url, task_id)

        if final_status.get("status") == "SUCCESS":
            print("Score calculation completed successfully!")

            # 3. Get and display rankings
            rankings = get_rankings(base_url, comp_id)
            display_results(rankings, "COMPETITION RANKINGS")

            # 4. Get and display leaderboard
            leaderboard = get_leaderboard(base_url, comp_id)
            display_results(leaderboard, "COMPETITION LEADERBOARD")
        else:
            print("Score calculation did not complete successfully.")
            display_results(final_status, "FINAL TASK STATUS")


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Test the scoring calculator API")

    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000/api",
        help="Base URL of the API (default: http://localhost:8000/api)")

    parser.add_argument("--comp-id",
                        type=str,
                        default="00000000-aaaa-bbbb-cccc-000000000001",
                        help="Competition ID to use for testing")

    parser.add_argument("--category",
                        type=str,
                        choices=["marathon", "boulder_beasts"],
                        help="Calculate scores for a specific category only")

    parser.add_argument(
        "--task",
        type=str,
        choices=["calculate", "status", "rankings", "leaderboard", "all"],
        default="all",
        help="Specific API task to test (default: all)")

    parser.add_argument("--task-id",
                        type=str,
                        help="Task ID for checking status")

    args = parser.parse_args()

    # Execute based on selected task
    if args.task == "calculate":
        result = calculate_scores(args.url, args.comp_id, args.category)
        display_results(result, "CALCULATION RESULT")

    elif args.task == "status":
        if not args.task_id:
            print("Error: --task-id is required when using --task=status")
            return

        result = check_task_status(args.url, args.task_id)
        display_results(result, f"TASK STATUS: {args.task_id}")

    elif args.task == "rankings":
        result = get_rankings(args.url, args.comp_id)
        display_results(result, "COMPETITION RANKINGS")

    elif args.task == "leaderboard":
        result = get_leaderboard(args.url, args.comp_id)
        display_results(result, "COMPETITION LEADERBOARD")

    else:  # "all"
        run_complete_test(args.url, args.comp_id)


if __name__ == "__main__":
    main()

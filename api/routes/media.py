"""
API routes for media uploading and processing.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any

from tasks.media_tasks import upload_photos_task

# Initialize router
router = APIRouter()


@router.post("/upload-photos/{crag_name}")
async def upload_crag_photos(
    background_tasks: BackgroundTasks,
    crag_name: str = "inia-droushia"
) -> Dict[str, Any]:
    """
    Start a background task to upload photos for a specific crag.

    Args:
        crag_name (str): Name of the crag to process photos for.
        Defaults to 'inia-droushia'.

    Returns:
        dict: Task information
    """
    try:
        # Start the Celery task
        task = upload_photos_task.delay(crag_name)

        return {
            "status": "started",
            "task_id": task.id,
            "crag_name": crag_name,
            "message": f"Photo upload for crag '{crag_name}' started"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start photo upload task: {str(e)}")


@router.get("/upload-photos/{task_id}/status")
async def check_upload_status(task_id: str) -> Dict[str, Any]:
    """
    Check the status of a photo upload task.

    Args:
        task_id (str): Celery task ID

    Returns:
        dict: Task status information
    """
    task = upload_photos_task.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            "status": "pending",
            "task_id": task_id,
            "message": "Task is pending"
        }
    elif task.state == 'PROGRESS':
        response = {"status": "in_progress", "task_id": task_id, **task.info}
    elif task.state == 'SUCCESS':
        if task.info.get("status") == "error":
            response = {
                "status": "error",
                "task_id": task_id,
                "error": task.info.get("error"),
                "traceback": task.info.get("traceback")
            }
        else:
            response = {
                "status": "completed",
                "task_id": task_id,
                "crag_name": task.info.get("crag_name"),
                "metrics": task.info.get("metrics", {}),
                "failures": task.info.get("failures", [])
            }
    elif task.state == 'FAILURE':
        response = {
            "status": "failed",
            "task_id": task_id,
            "error": str(task.result),
        }
    else:
        response = {
            "status": task.state,
            "task_id": task_id,
        }

    return response

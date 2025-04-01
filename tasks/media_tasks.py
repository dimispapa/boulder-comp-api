"""
Celery tasks for uploading media to Supabase Storage.
"""
import traceback
from dotenv import load_dotenv
from typing import Dict, Any

from tasks.celery_app import celery_app
from utils.supabase import get_admin_supabase_client
from utils.photo_uploader import PhotoUploader
from utils.loggers import logger

# Load environment variables
load_dotenv()

# Initialize Supabase client (for use in Celery workers)
supabase = get_admin_supabase_client()


@celery_app.task(bind=True, name='tasks.media_tasks.upload_photos_task')
def upload_photos_task(self, crag_name: str) -> Dict[str, Any]:
    """
    Celery task to upload photos for a crag from scraped URLs
    to Supabase Storage.

    Args:
        crag_name (str): Name of the crag to process photos for

    Returns:
        dict: Status and result of the upload operation
    """
    try:
        # Update task state
        self.update_state(state='PROGRESS',
                          meta={
                              'status':
                              'uploading',
                              'message':
                              f'Uploading photos for crag {crag_name}...'
                          })

        # Create the photo uploader and upload photos
        uploader = PhotoUploader(supabase)
        result = uploader.upload_photos_for_crag(crag_name)

        # Add detailed metrics to the result
        metrics = {
            "crag_name": crag_name,
            "total_photos": result.get("total", 0),
            "uploaded": result.get("uploaded", 0),
            "failed": result.get("failed", 0),
        }

        # Store failure details
        failure_details = result.get("failures", [])

        # Update task state with the final result
        self.update_state(state='SUCCESS',
                          meta={
                              'status': 'completed',
                              'message': (
                                  f'Completed photo upload for crag '
                                  f'{crag_name}'
                              ),
                              'metrics': metrics,
                              'failures': failure_details
                          })

        return {
            "status": "success",
            "crag_name": crag_name,
            "metrics": metrics,
            "failures": failure_details
        }

    except Exception as e:
        logger.error(
            f"Error in upload_photos_task for crag {crag_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "crag_name": crag_name,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

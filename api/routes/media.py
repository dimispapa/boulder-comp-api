"""
API routes for media uploading and processing.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from utils.supabase import get_admin_supabase_client
from utils.cloudinary_uploader import CloudinaryUploader

# Initialize router
router = APIRouter()
# Initialize Supabase client for direct operations
supabase = get_admin_supabase_client()


@router.post("/upload-boulder-photos/{crag_name}")
async def upload_boulder_photos_to_cloudinary(
        crag_name: str = "inia-droushia") -> Dict[str, Any]:
    """
    Upload boulder photos for a crag directly to Cloudinary (synchronous).

    Args:
        crag_name (str): Name of the crag to process photos for.
                         Default is "inia-droushia".

    Returns:
        dict: Upload result information
    """
    try:
        # Create a CloudinaryUploader and upload photos
        uploader = CloudinaryUploader(supabase)
        result = uploader.upload_photos_for_crag(crag_name)

        return {
            "status": result.get("status", "error"),
            "crag_name": crag_name,
            "total_photos": result.get("total", 0),
            "uploaded_photos": result.get("uploaded", 0),
            "failed_photos": result.get("failed", 0),
            "message":
            (f"Boulder photos upload for crag '{crag_name}' completed")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload boulder photos: {str(e)}")


@router.post("/upload-competition-photos/{competition_id}")
async def upload_competition_photos_to_cloudinary(
        competition_id: str) -> Dict[str, Any]:
    """
    Upload user-submitted competition photos to Cloudinary (synchronous).

    Args:
        competition_id (str): ID of the competition.

    Returns:
        dict: Upload result information
    """
    try:
        # Create a CloudinaryUploader and upload competition photos
        uploader = CloudinaryUploader(supabase)
        result = uploader.upload_competition_photos(competition_id)

        return {
            "status":
            result.get("status", "error"),
            "competition_id":
            competition_id,
            "total_photos":
            result.get("total", 0),
            "uploaded_photos":
            result.get("uploaded", 0),
            "failed_photos":
            result.get("failed", 0),
            "message":
            (f"Competition photos upload for ID '{competition_id}' completed")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload competition photos: {str(e)}")


@router.get("/competition-photos/{competition_id}")
async def get_competition_photos(competition_id: str,
                                 approved_only: bool = True) -> Dict[str, Any]:
    """
    Get competition photos for a specific competition.

    Args:
        competition_id (str): ID of the competition.
        approved_only (bool): Whether to return only approved photos.

    Returns:
        dict: Competition photos information
    """
    try:
        # Build the query
        query = supabase.table('competition_photos') \
            .select(
                'id, cloudinary_url, description, uploader_id, featured, '
                'approved, created_at'
            ) \
            .eq('competition_id', competition_id)

        # Filter by approved status if needed
        if approved_only:
            query = query.eq('approved', True)

        # Execute the query
        response = query.execute()

        # Get the competition details
        competition = supabase.table('competitions') \
            .select('name, display_name') \
            .eq('id', competition_id) \
            .execute()

        competition_name = (competition.data[0]['display_name']
                            if competition.data else "Unknown Competition")

        return {
            "status": "success",
            "competition_id": competition_id,
            "competition_name": competition_name,
            "photo_count": len(response.data),
            "photos": response.data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve competition photos: {str(e)}")


@router.patch("/competition-photos/{photo_id}/approve")
async def approve_competition_photo(photo_id: str,
                                    approve: bool = True) -> Dict[str, Any]:
    """
    Approve or unapprove a competition photo.

    Args:
        photo_id (str): ID of the photo.
        approve (bool): Whether to approve or unapprove the photo.

    Returns:
        dict: Result information
    """
    try:
        # Update the photo approval status
        response = supabase.table('competition_photos') \
            .update({'approved': approve}) \
            .eq('id', photo_id) \
            .execute()

        if not response.data:
            raise HTTPException(status_code=404,
                                detail=f"Photo with ID {photo_id} not found")

        status = "approved" if approve else "unapproved"

        return {
            "status": "success",
            "photo_id": photo_id,
            "approved": approve,
            "message": f"Photo has been {status}"
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update photo approval status: {str(e)}")


@router.patch("/competition-photos/{photo_id}/feature")
async def feature_competition_photo(photo_id: str,
                                    feature: bool = True) -> Dict[str, Any]:
    """
    Feature or unfeature a competition photo.

    Args:
        photo_id (str): ID of the photo.
        feature (bool): Whether to feature or unfeature the photo.

    Returns:
        dict: Result information
    """
    try:
        # Update the photo feature status
        response = supabase.table('competition_photos') \
            .update({'featured': feature}) \
            .eq('id', photo_id) \
            .execute()

        if not response.data:
            raise HTTPException(status_code=404,
                                detail=f"Photo with ID {photo_id} not found")

        status = "featured" if feature else "unfeatured"

        return {
            "status": "success",
            "photo_id": photo_id,
            "featured": feature,
            "message": f"Photo has been {status}"
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update photo feature status: {str(e)}")

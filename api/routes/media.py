"""
API routes for media uploading and processing.
"""
from fastapi import (APIRouter, HTTPException, File, UploadFile, Form, Query,
                     Depends)
from sqlmodel import Session
from typing import Dict, Any, Optional
import os
import uuid

from database.management.base import get_db
from database.models.media import CompetitionPhoto
from database.crud.media import (get_photos_by_competition,
                                 create_or_update_photo, approve_photo,
                                 feature_photo)
from utils.cloudinary_uploader import CloudinaryUploader

# Initialize router
router = APIRouter()


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
        with get_db() as session:
            uploader = CloudinaryUploader(session)
            result = uploader.upload_photos_for_crag(crag_name)

            return {
                "status":
                result.get("status", "error"),
                "crag_name":
                crag_name,
                "total_photos":
                result.get("total", 0),
                "uploaded_photos":
                result.get("uploaded", 0),
                "failed_photos":
                result.get("failed", 0),
                "message":
                (f"Boulder photos upload for crag '{crag_name}' completed")
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload boulder photos: {str(e)}")


@router.post("/upload-competition-photos/{competition_id}")
async def upload_user_photo(
    competition_id: str,
    photo: UploadFile = File(...),
    user_id: str = Query(...),
    description: str = Form(""),
    session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Handle direct photo uploads from competition participants.

    Args:
        competition_id (str): ID of the competition
        photo (UploadFile): The uploaded photo file
        user_id (str): ID of the participant uploading
        description (str): Optional photo description
        session (Session): Database session

    Returns:
        dict: Upload result information
    """
    try:
        # Verify user is a participant of this competition
        from database.crud.competitions import (
            get_participant_by_user_and_competition)

        participant = get_participant_by_user_and_competition(
            session, uuid.UUID(user_id), uuid.UUID(competition_id))

        if not participant:
            raise HTTPException(
                status_code=403,
                detail="User is not a participant in this competition")

        # Save the temporary file
        temp_file_path = f"/tmp/{uuid.uuid4()}.jpg"
        with open(temp_file_path, "wb") as temp_file:
            content = await photo.read()
            temp_file.write(content)

        # Create competition photo record
        new_photo = CompetitionPhoto(competition_id=uuid.UUID(competition_id),
                                     uploader_id=participant.id,
                                     description=description)
        created_photo = create_or_update_photo(session, new_photo)

        # Upload to Cloudinary
        uploader = CloudinaryUploader(session)
        upload_result = uploader._upload_competition_photo({
            "id":
            str(created_photo.id),
            "source_url":
            temp_file_path,
            "competition_id":
            competition_id,
            "uploader_id":
            str(participant.id)
        })

        # Clean up temp file
        os.remove(temp_file_path)

        if not upload_result.get("success"):
            return {
                "status": "error",
                "competition_id": competition_id,
                "message": upload_result.get("error", "Unknown error")
            }

        # Update the photo record with Cloudinary URL
        created_photo.cloudinary_url = upload_result["cloudinary_url"]
        create_or_update_photo(session, created_photo)

        return {
            "status": "success",
            "competition_id": competition_id,
            "photo_id": str(created_photo.id),
            "url": upload_result["cloudinary_url"],
            "message": "Photo uploaded successfully"
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload competition photo: {str(e)}")


@router.get("/competition-photos/{competition_id}")
async def get_competition_photos(
    competition_id: str,
    approved_only: bool = True,
    session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get competition photos for a specific competition.

    Args:
        competition_id (str): ID of the competition.
        approved_only (bool): Whether to return only approved photos.
        session (Session): Database session

    Returns:
        dict: Competition photos information
    """
    try:
        # Get photos for the competition
        photos = get_photos_by_competition(session, uuid.UUID(competition_id),
                                           approved_only)

        # Get competition info from database using SQLModel
        from database.crud.competitions import (get_competition_by_id)
        competition = get_competition_by_id(session, uuid.UUID(competition_id))

        competition_name = (competition.display_name
                            if competition else "Unknown Competition")

        # Convert SQLModel objects to dictionaries
        photos_data = []
        for photo in photos:
            photos_data.append({
                "id": str(photo.id),
                "cloudinary_url": photo.cloudinary_url,
                "description": photo.description,
                "uploader_id": str(photo.uploader_id),
                "featured": photo.featured,
                "approved": photo.approved,
                "inserted_at": photo.inserted_at.isoformat()
            })

        return {
            "status": "success",
            "competition_id": competition_id,
            "competition_name": competition_name,
            "photo_count": len(photos_data),
            "photos": photos_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve competition photos: {str(e)}")


@router.patch("/competition-photos/{photo_id}/approve")
async def approve_competition_photo(
    photo_id: str,
    approve_status: bool = True,
    session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Approve or unapprove a competition photo.

    Args:
        photo_id (str): ID of the photo.
        approve_status (bool): Whether to approve or unapprove the photo.
        session (Session): Database session

    Returns:
        dict: Result information
    """
    try:
        # Update the photo approval status
        photo = approve_photo(session, uuid.UUID(photo_id), approve_status)

        if not photo:
            raise HTTPException(status_code=404,
                                detail=f"Photo with ID {photo_id} not found")

        status = "approved" if approve_status else "unapproved"

        return {
            "status": "success",
            "photo_id": photo_id,
            "approved": approve_status,
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
async def feature_competition_photo(
    photo_id: str,
    feature_status: bool = True,
    session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Feature or unfeature a competition photo.

    Args:
        photo_id (str): ID of the photo.
        feature_status (bool): Whether to feature or unfeature the photo.
        session (Session): Database session

    Returns:
        dict: Result information
    """
    try:
        # Update the photo feature status
        photo = feature_photo(session, uuid.UUID(photo_id), feature_status)

        if not photo:
            raise HTTPException(status_code=404,
                                detail=f"Photo with ID {photo_id} not found")

        status = "featured" if feature_status else "unfeatured"

        return {
            "status": "success",
            "photo_id": photo_id,
            "featured": feature_status,
            "message": f"Photo has been {status}"
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update photo feature status: {str(e)}")


@router.post("/upload")
async def upload_media(file: UploadFile = File(...),
                       competition_id: str = Form(...),
                       type: str = Form(...),
                       session: Session = Depends(get_db)):
    # Implementation of the new route
    pass


@router.get("/competition/{competition_id}")
async def get_competition_media(competition_id: str,
                                type: Optional[str] = None,
                                session: Session = Depends(get_db)):
    # Implementation of the new route
    pass


@router.delete("/{media_id}")
async def delete_media(media_id: str, session: Session = Depends(get_db)):
    # Implementation of the new route
    pass


@router.get("/download/{media_id}")
async def download_media(media_id: str, session: Session = Depends(get_db)):
    # Implementation of the new route
    pass

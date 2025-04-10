"""
CRUD operations for media-related models.
"""
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select
from datetime import datetime, UTC

from database.models.media import CompetitionPhoto


# CompetitionPhoto operations
def get_photo_by_id(session: Session,
                    photo_id: UUID) -> Optional[CompetitionPhoto]:
    """Get a competition photo by its ID."""
    return session.get(CompetitionPhoto, photo_id)


def get_photos_by_competition(
        session: Session,
        competition_id: UUID,
        approved_only: bool = False) -> List[CompetitionPhoto]:
    """Get all photos for a specific competition."""
    statement = select(CompetitionPhoto).where(
        CompetitionPhoto.competition_id == competition_id)

    if approved_only:
        statement = statement.where(CompetitionPhoto.approved)

    return session.exec(statement).all()


def create_photo(session: Session,
                 photo: CompetitionPhoto) -> CompetitionPhoto:
    """Create a new competition photo record."""
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def update_photo(session: Session,
                 photo: CompetitionPhoto) -> CompetitionPhoto:
    """Update an existing competition photo."""
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def approve_photo(session: Session,
                  photo_id: UUID,
                  approve: bool = True) -> Optional[CompetitionPhoto]:
    """Approve or unapprove a competition photo."""
    photo = session.get(CompetitionPhoto, photo_id)
    if photo:
        photo.approved = approve
        session.add(photo)
        session.commit()
        session.refresh(photo)
        return photo
    return None


def feature_photo(session: Session,
                  photo_id: UUID,
                  feature: bool = True) -> Optional[CompetitionPhoto]:
    """Feature or unfeature a competition photo."""
    photo = session.get(CompetitionPhoto, photo_id)
    if photo:
        photo.featured = feature
        session.add(photo)
        session.commit()
        session.refresh(photo)
        return photo
    return None


def delete_photo(session: Session, photo_id: UUID) -> bool:
    """Delete a competition photo by ID."""
    photo = session.get(CompetitionPhoto, photo_id)
    if photo:
        session.delete(photo)
        session.commit()
        return True
    return False


# Upsert operations (Create or Update)


def get_photo_by_filename(session: Session,
                          filename: str) -> Optional[CompetitionPhoto]:
    """Get a competition photo by its filename."""
    statement = select(CompetitionPhoto).where(
        CompetitionPhoto.filename == filename)
    return session.exec(statement).first()


def create_or_update_photo(session: Session,
                           photo: CompetitionPhoto) -> CompetitionPhoto:
    """Create a new competition photo or update if it already exists."""
    # First try to find by ID if available
    existing_photo = None
    if photo.id:
        existing_photo = get_photo_by_id(session, photo.id)

    # If not found by ID, try to find by filename (assuming filename is unique)
    if not existing_photo and photo.filename:
        existing_photo = get_photo_by_filename(session, photo.filename)

    if existing_photo:
        # Update fields from the new photo
        existing_photo.competition_id = photo.competition_id
        existing_photo.participant_id = photo.participant_id
        existing_photo.filename = photo.filename
        existing_photo.storage_url = photo.storage_url
        existing_photo.caption = photo.caption
        existing_photo.approved = photo.approved
        existing_photo.featured = photo.featured
        existing_photo.updated_at = datetime.now(UTC)

        session.add(existing_photo)
        session.commit()
        session.refresh(existing_photo)
        return existing_photo
    else:
        # Create new photo
        session.add(photo)
        session.commit()
        session.refresh(photo)
        return photo

"""
SQLModel models related to media and photo management.
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4


class CompetitionPhoto(SQLModel, table=True):
    """Photos from competitions."""
    __tablename__ = "competition_photos"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    uploader_id: UUID = Field(foreign_key="participants.id")
    cloudinary_url: Optional[str] = None
    description: Optional[str] = None
    approved: bool = Field(default=False)
    featured: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

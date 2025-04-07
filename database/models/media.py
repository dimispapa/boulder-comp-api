"""
SQLModel models related to media and photo management.
"""
from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Relationship
from datetime import UTC
import json

from database.models.crags import Boulder


class BoulderPhoto(SQLModel, table=True):
    """Photos of boulders."""
    __tablename__ = "boulder_photos"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    boulder_id: UUID = Field(foreign_key="boulders.id")
    source_url: str
    order: int = 1
    photo_id: str  # External ID of the photo
    storage_url: Optional[str] = None  # URL to stored image
    lines_data: Optional[str] = Field(default=None, sa_type=JSONB)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    boulder: Boulder = Relationship(back_populates="photos")

    # SQLModel doesn't handle JSON/JSONB fields directly, so we need to convert
    # between Python dicts and JSON strings
    @property
    def lines_data_dict(self) -> Dict[str, Any]:
        """Get lines_data as a Python dictionary."""
        if not self.lines_data:
            return {}
        return json.loads(self.lines_data)

    @lines_data_dict.setter
    def lines_data_dict(self, value: Dict[str, Any]):
        """Set lines_data from a Python dictionary."""
        if not value:
            self.lines_data = None
        else:
            self.lines_data = json.dumps(value)


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

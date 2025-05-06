"""
SQLModel models related to workshops and workshop participants.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, UTC
from uuid import UUID, uuid4

from database.models.enums import EventStatus


class Workshop(SQLModel, table=True):
    """Workshop model."""
    __tablename__ = "workshops"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    payment_link_id: str = Field(unique=True)
    payment_link: str = Field(unique=True)
    name: str = Field(unique=True)
    display_name: str = Field(unique=True)
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = Field(default=EventStatus.upcoming)
    description: Optional[str] = None
    venue: Optional[str] = None
    max_participants: int = Field(default=20)
    fee: Optional[float] = None  # Optional workshop fee
    instructor: Optional[str] = None  # Name of the workshop instructor
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    participants: List["WorkshopParticipant"] = Relationship(
        back_populates="workshop")


class WorkshopParticipant(SQLModel, table=True):
    """Workshop participant model."""
    __tablename__ = "workshop_participants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workshop_name: str = Field(foreign_key="workshops.name",
                               ondelete="CASCADE")
    full_name: str
    email: str = Field(index=True)
    phone: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=12, lt=99)
    notes: Optional[
        str] = None  # Any additional information about the participant
    signed_waiver: bool = Field(default=False)
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    workshop: Workshop = Relationship(back_populates="participants")

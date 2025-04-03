"""
SQLModel models related to competitions, teams, participants, and ascents.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, UTC
from uuid import UUID, uuid4
from enum import Enum

from database.models.routes import Route


class CompetitionStatus(str, Enum):
    """Competition status enum."""
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"


class CompetitionCategory(str, Enum):
    """Competition category enum."""
    MARATHON = "marathon"
    BOULDER_BEASTS = "boulder_beasts"


class Competition(SQLModel, table=True):
    """Climbing competition model."""
    __tablename__ = "competitions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True)
    crag_id: UUID = Field(foreign_key="crags.id")
    display_name: str = Field(unique=True)
    # We'll store categories as a comma-separated string since
    # SQLModel doesn't directly support array types
    categories: str  # Comma-separated string of CompetitionCategory values
    start_date: datetime
    end_date: datetime
    status: str = Field(default=CompetitionStatus.ONGOING.value)
    description: Optional[str] = None
    venue: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    teams: List["Team"] = Relationship(back_populates="competition")
    participants: List["Participant"] = Relationship(
        back_populates="competition")

    # Helper methods for categories
    @property
    def categories_list(self) -> List[str]:
        """Get categories as a list of strings."""
        return [
            cat.strip() for cat in self.categories.split(",") if cat.strip()
        ]

    @categories_list.setter
    def categories_list(self, value: List[str]):
        """Set categories from a list of strings."""
        self.categories = ",".join(value)


class Team(SQLModel, table=True):
    """Team model for team-based competitions."""
    __tablename__ = "teams"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    name: str
    category: str = CompetitionCategory.MARATHON.value
    paid: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: Competition = Relationship(back_populates="teams")
    participants: List["Participant"] = Relationship(back_populates="team")

    # We can't have a direct relationship to the captain as it would
    # create a circular dependency, so we'll handle it through properties
    captain_id: Optional[UUID] = None


class Participant(SQLModel, table=True):
    """Participant in a competition."""
    __tablename__ = "participants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    first_name: str
    last_name: str
    email: str
    team_id: Optional[UUID] = Field(default=None, foreign_key="teams.id")
    solo_entry: bool = False
    club_member: bool = False
    membership_number: Optional[str] = None
    paid: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: Competition = Relationship(back_populates="participants")
    team: Optional[Team] = Relationship(back_populates="participants")
    ascents: List["Ascent"] = Relationship(back_populates="participant")


class Ascent(SQLModel, table=True):
    """Recorded ascent of a route."""
    __tablename__ = "ascents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    participant_id: UUID = Field(foreign_key="participants.id")
    route_id: UUID = Field(foreign_key="routes.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submitted: bool = False

    # Relationships
    participant: Participant = Relationship(back_populates="ascents")
    route: Route = Relationship(back_populates="ascents")

    class Config:
        """SQLModel config."""
        arbitrary_types_allowed = True

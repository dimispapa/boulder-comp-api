"""
SQLModel models related to competitions, teams, participants, and ascents.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, UTC
from uuid import UUID, uuid4
from enum import Enum
import sqlalchemy.schema

from database.models.scoring import (BasePoints, VolumeBonus,
                                     UniqueAscentBonus, TeamAscentBonus,
                                     MasterGradeBonus)

# Type hints for forward references
if TYPE_CHECKING:
    from database.models.crags import Crag, Route
    from database.models.accounts import User, CompVoucher


class CompetitionStatus(str, Enum):
    """Competition status enum."""
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"


class CategoryType(str, Enum):
    """Competition category type enum."""
    MARATHON = "marathon"
    BOULDER_BEASTS = "boulder_beasts"


class Competition(SQLModel, table=True):
    """Climbing competition model."""
    __tablename__ = "competitions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True)
    crag_id: UUID = Field(foreign_key="crags.id")
    display_name: str = Field(unique=True)
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
    categories: List["CompetitionCategory"] = Relationship(
        back_populates="competition")
    ascents: List["Ascent"] = Relationship(back_populates="competition")
    base_points: Optional[List["BasePoints"]] = Relationship(
        back_populates="competition")
    volume_bonus: Optional["VolumeBonus"] = Relationship(
        back_populates="competition")
    unique_ascent_bonus: Optional["UniqueAscentBonus"] = Relationship(
        back_populates="competition")
    team_ascent_bonuses: Optional[List["TeamAscentBonus"]] = Relationship(
        back_populates="competition")
    master_grade_bonus: Optional["MasterGradeBonus"] = Relationship(
        back_populates="competition")
    comp_vouchers: List["CompVoucher"] = Relationship(
        back_populates="competition")
    crag: "Crag" = Relationship(back_populates="competitions")


class CompetitionCategory(SQLModel, table=True):
    """Competition category model."""
    __tablename__ = "competition_categories"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    category_type: str = Field(CategoryType)
    name: str = Field(...)
    description: Optional[str] = Field(default=None)
    display_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: Competition = Relationship(back_populates="categories")


class Team(SQLModel, table=True):
    """Team model for team-based competitions."""
    __tablename__ = "teams"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    name: str
    # We can't have a direct relationship to the captain as it would
    # create a circular dependency, so we'll handle it through named
    # constraints
    captain_id: UUID = Field(
        sa_column_kwargs={
            "foreign_keys": [
                sqlalchemy.schema.ForeignKey("participants.id",
                                             name="fk_team_captain_id")
            ]
        })
    category: str = CategoryType.MARATHON.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: Competition = Relationship(back_populates="teams")
    participants: List["Participant"] = Relationship(back_populates="team")
    ascents: List["Ascent"] = Relationship(back_populates="team")


class Participant(SQLModel, table=True):
    """Participant in a competition."""
    __tablename__ = "participants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    user_id: UUID = Field(foreign_key="users.id")
    first_name: str
    last_name: str
    email: str
    team_id: Optional[UUID] = Field(default=None, foreign_key="teams.id")
    solo_entry: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: Competition = Relationship(back_populates="participants")
    team: Optional[Team] = Relationship(back_populates="participants")
    ascents: List["Ascent"] = Relationship(back_populates="participant")
    user: "User" = Relationship(back_populates="participants")
    comp_voucher: Optional["CompVoucher"] = Relationship(
        back_populates="participant",
        sa_relationship_kwargs={"uselist": False})


class Ascent(SQLModel, table=True):
    """Recorded ascent of a route."""
    __tablename__ = "ascents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    participant_id: UUID = Field(foreign_key="participants.id")
    route_id: UUID = Field(foreign_key="routes.id")
    team_id: Optional[UUID] = Field(default=None, foreign_key="teams.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    participant: Participant = Relationship(back_populates="ascents")
    route: "Route" = Relationship(back_populates="ascents")
    competition: Competition = Relationship(back_populates="ascents")
    team: Optional[Team] = Relationship(back_populates="ascents")

    class Config:
        """SQLModel config."""
        arbitrary_types_allowed = True

"""
SQLModel models related to scoring configuration and results.
"""
from sqlmodel import SQLModel, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, UTC
from uuid import UUID, uuid4
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Relationship
import json

# Import Competition only for type checking
if TYPE_CHECKING:
    from database.models.competitions import Competition


class BasePoints(SQLModel, table=True):
    """Base points configuration for each grade."""
    __tablename__ = "base_points"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: Optional[UUID] = Field(default=None,
                                           foreign_key="competitions.id")
    grade: str = Field(index=True)
    points: int
    increment_factor: Optional[float] = None

    # Relationships
    competition: Optional["Competition"] = Relationship(
        back_populates="base_points")


class VolumeBonus(SQLModel, table=True):
    """Volume bonus configuration."""
    __tablename__ = "volume_bonus"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: Optional[UUID] = Field(default=None,
                                           foreign_key="competitions.id")
    bonus_increment: int  # Number of ascents to trigger bonus
    points_per_increment: int  # Points awarded per increment

    # Relationships
    competition: Optional["Competition"] = Relationship(
        back_populates="volume_bonus")


class UniqueAscentBonus(SQLModel, table=True):
    """Unique ascent bonus configuration."""
    __tablename__ = "unique_ascent_bonus"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: Optional[UUID] = Field(default=None,
                                           foreign_key="competitions.id")
    bonus_factor: float  # Multiplier for unique ascents

    # Relationships
    competition: Optional["Competition"] = Relationship(
        back_populates="unique_ascent_bonus")


class TeamAscentBonus(SQLModel, table=True):
    """Team ascent bonus configuration."""
    __tablename__ = "team_ascent_bonus"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: Optional[UUID] = Field(default=None,
                                           foreign_key="competitions.id")
    team_size: int  # Size of the team
    bonus_factor: float  # Bonus multiplier (e.g., 0.18 for 18%)

    # Relationships
    competition: Optional["Competition"] = Relationship(
        back_populates="team_ascent_bonuses")


class MasterGradeBonus(SQLModel, table=True):
    """Master grade bonus configuration."""
    __tablename__ = "master_grade_bonus"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: Optional[UUID] = Field(default=None,
                                           foreign_key="competitions.id")
    bonus_factor: float  # Bonus factor for team with most ascents in a grade

    # Relationships
    competition: Optional["Competition"] = Relationship(
        back_populates="master_grade_bonus")


class MarathonRanking(SQLModel, table=True):
    """Team rankings for marathon category."""
    __tablename__ = "marathon_rankings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    team_id: UUID = Field(foreign_key="teams.id")
    team_size: int
    base_score: float
    volume_bonus: float
    unique_ascent_bonus: float
    team_ascent_bonus: float
    master_grade_bonus: float
    total_score: float
    normalized_score: float
    rank: int
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # This would normally have a relationship,
    # but it can create circular dependencies
    # with SQLModel if we're not careful,
    # so we'll just use the foreign key directly


class MarathonDetailedResults(SQLModel, table=True):
    """Detailed results for marathon team rankings."""
    __tablename__ = "marathon_detailed_results"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    team_id: UUID = Field(foreign_key="teams.id")
    team_name: str
    team_size: int
    routes: dict = Field(sa_type=JSONB)  # Detailed routes information
    total_ascents: int
    volume_bonus: float
    team_completed_routes: int
    team_unique_routes: int
    master_grades: dict = Field(sa_type=JSONB)  # Master grades information
    master_grade_bonus: float
    base_score: float
    team_ascent_bonus: float
    unique_ascent_bonus: float
    total_score: float
    normalized_score: float
    rank: int
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Properties for JSON serialization/deserialization
    @property
    def routes_data(self) -> dict:
        """Get routes data as Python dictionary."""
        if isinstance(self.routes, dict):
            return self.routes
        elif isinstance(self.routes, str):
            return json.loads(self.routes)
        return {}

    @routes_data.setter
    def routes_data(self, value: dict) -> None:
        """Set routes data from Python dictionary."""
        self.routes = value

    @property
    def master_grades_data(self) -> dict:
        """Get master grades data as Python dictionary."""
        if isinstance(self.master_grades, dict):
            return self.master_grades
        elif isinstance(self.master_grades, str):
            return json.loads(self.master_grades)
        return {}

    @master_grades_data.setter
    def master_grades_data(self, value: dict) -> None:
        """Set master grades data from Python dictionary."""
        self.master_grades = value


class BoulderBeastsRanking(SQLModel, table=True):
    """Individual rankings for boulder beasts category."""
    __tablename__ = "boulder_beasts_rankings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id")
    participant_id: UUID = Field(foreign_key="participants.id")
    total_score: float
    top_5_routes: Optional[List[str]] = Field(default=None,
                                              sa_type=ARRAY(String))
    top_5_routes_score: float
    rank: int
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

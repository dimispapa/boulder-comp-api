"""
SQLModel models related to scoring configuration and results.
"""
from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import json


class BasePoints(SQLModel, table=True):
    """Base points configuration for each grade."""
    __tablename__ = "base_points"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    grade: str = Field(unique=True)
    points: int
    increment_factor: Optional[float] = None


class VolumeBonus(SQLModel, table=True):
    """Volume bonus configuration."""
    __tablename__ = "volume_bonus"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bonus_increment: int  # Number of ascents to trigger bonus
    points_per_increment: int  # Points awarded per increment


class UniqueAscentBonus(SQLModel, table=True):
    """Unique ascent bonus configuration."""
    __tablename__ = "unique_ascent_bonus"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bonus_factor: float  # Multiplier for unique ascents


class TeamAscentBonus(SQLModel, table=True):
    """Team ascent bonus configuration."""
    __tablename__ = "team_ascent_bonus"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    team_size: int  # Size of the team
    bonus_factor: float  # Bonus multiplier


class MasterGradeBonus(SQLModel, table=True):
    """Master grade bonus configuration."""
    __tablename__ = "master_grade_bonus"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bonus_factor: float  # Bonus factor for team with most ascents in a grade


class ScoredAscent(SQLModel, table=True):
    """Individual scored ascent."""
    __tablename__ = "scored_ascents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ascent_id: UUID = Field(foreign_key="ascents.id")
    participant_id: UUID = Field(foreign_key="participants.id")
    route_id: UUID = Field(foreign_key="routes.id")
    base_points: float
    volume_bonus: float
    unique_bonus: float
    total_points: float
    timestamp: datetime


class MarathonRanking(SQLModel, table=True):
    """Team rankings for marathon category."""
    __tablename__ = "marathon_rankings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    team_id: UUID = Field(foreign_key="teams.id")
    base_score: float
    volume_score: float
    unique_ascent_score: float
    team_ascent_bonus: float
    master_grade_bonus: float
    total_score: float
    rank: int

    # This would normally have a relationship,
    # but it can create circular dependencies
    # with SQLModel if we're not careful,
    # so we'll just use the foreign key directly


class BoulderBeastsRanking(SQLModel, table=True):
    """Individual rankings for boulder beasts category."""
    __tablename__ = "boulder_beasts_rankings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    participant_id: UUID = Field(foreign_key="participants.id")
    top_grades: Dict[str, Any] = Field(sa_column_kwargs={"type": "JSONB"})
    total_score: float
    rank: int

    # Helper methods for JSON fields
    @property
    def top_grades_dict(self) -> Dict[str, Any]:
        """Get top_grades as a Python dictionary."""
        if isinstance(self.top_grades, str):
            return json.loads(self.top_grades or "{}")
        return self.top_grades or {}

    @top_grades_dict.setter
    def top_grades_dict(self, value: Dict[str, Any]):
        """Set top_grades from a Python dictionary."""
        if value is None:
            self.top_grades = None
        else:
            self.top_grades = value

"""
SQLModel models related to competitions, teams, participants, and ascents.
"""
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from sqlalchemy import Column, Computed
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, UTC
from uuid import UUID, uuid4
from sqlalchemy import Boolean, event, DDL
import os

from database.models.enums import (CompetitionStatus, CategoryType,
                                   MarathonSubCategory)
from database.models.scoring import (BasePoints, VolumeBonus,
                                     UniqueAscentBonus, TeamAscentBonus,
                                     MasterGradeBonus)
from utils.general_utils import load_sql_file

MIN_TEAM_SIZE = int(os.environ.get("MIN_TEAM_SIZE", 2))
MAX_TEAM_SIZE = int(os.environ.get("MAX_TEAM_SIZE", 4))

# Type hints for forward references
if TYPE_CHECKING:
    from database.models.crags import Crag, Route
    from database.models.accounts import User


class Competition(SQLModel, table=True):
    """Climbing competition model."""
    __tablename__ = "competitions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True)
    display_name: str = Field(unique=True)
    crag_id: UUID = Field(foreign_key="crags.id")
    start_date: datetime
    end_date: datetime
    status: str = Field(default=CompetitionStatus.ongoing)
    description: Optional[str] = None
    venue: Optional[str] = None
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
    name: str = Field(unique=True)
    description: Optional[str] = Field(default=None)
    display_order: int = 0
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: Competition = Relationship(back_populates="categories")


class Team(SQLModel, table=True):
    """Team model for team-based competitions."""
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint(
        'name', 'competition_id', name='unique_team_name_per_competition'), )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    team_code: str = Field(unique=True)
    # Spots available are set based on MAX_TEAM_SIZE env var
    spots: int = Field(default=MAX_TEAM_SIZE - 1, ge=0, lt=MAX_TEAM_SIZE)
    is_full: bool = False
    # Computed field: team is valid when it has at least 2 members
    # (MAX_TEAM_SIZE - MIN_TEAM_SIZE)
    is_valid: bool = Field(sa_column=Column(
        Boolean,
        Computed(f"spots <= {MAX_TEAM_SIZE - MIN_TEAM_SIZE}", persisted=True)))
    captain_id: UUID = Field(foreign_key="users.id",
                             ondelete="SET NULL",
                             nullable=True)
    competition_id: UUID = Field(foreign_key="competitions.id",
                                 ondelete="SET NULL",
                                 nullable=True)
    marathon_subcategory: Optional[MarathonSubCategory] = Field(default=None)
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: "Competition" = Relationship(back_populates="teams")
    participants: List["Participant"] = Relationship(back_populates="team")
    ascents: List["Ascent"] = Relationship(back_populates="team")


class Participant(SQLModel, table=True):
    """Participant in a competition."""
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint('user_id',
                                       'competition_id',
                                       name='unique_participant'), )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    competition_id: UUID = Field(foreign_key="competitions.id",
                                 ondelete="CASCADE")
    user_id: Optional[UUID] = Field(foreign_key="users.id",
                                    ondelete="SET NULL",
                                    nullable=True)
    team_id: Optional[UUID] = Field(foreign_key="teams.id",
                                    ondelete="SET NULL",
                                    nullable=True)
    # Denormalized field to store team validity
    team_is_valid: Optional[bool] = Field(default=None)
    # Computed field: participant is solo when they have no team
    # or their team is invalid
    is_solo: bool = Field(sa_column=Column(
        Boolean,
        Computed("team_id IS NULL OR team_is_valid IS NOT TRUE",
                 persisted=True)))
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: Competition = Relationship(back_populates="participants")
    team: Optional[Team] = Relationship(back_populates="participants")
    ascents: List["Ascent"] = Relationship(back_populates="participant")
    user: Optional["User"] = Relationship(back_populates="participants")
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
    status: bool = Field(default=True)
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    participant: Participant = Relationship(back_populates="ascents")
    route: "Route" = Relationship(back_populates="ascents")
    competition: Competition = Relationship(back_populates="ascents")
    team: Optional[Team] = Relationship(back_populates="ascents")

    class Config:
        """SQLModel config."""
        arbitrary_types_allowed = True


class CompVoucher(SQLModel, table=True):
    """Competition voucher model."""
    __tablename__ = "comp_vouchers"
    __table_args__ = (UniqueConstraint(
        'email',
        'competition_id',
        name='unique_comp_voucher_email_per_competition'), )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str
    code: int = Field(unique=True)
    code_used_at: Optional[datetime] = None
    competition_id: UUID = Field(foreign_key="competitions.id",
                                 ondelete="CASCADE")
    participant_id: Optional[UUID] = Field(default=None,
                                           foreign_key="participants.id",
                                           ondelete="CASCADE")
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: "Competition" = Relationship(back_populates="comp_vouchers")
    participant: Optional["Participant"] = Relationship(
        back_populates="comp_voucher")


# Trigger functions
# 1. Trigger to update participants when a team's validity changes
update_participants_team_validity_trigger = DDL(
    load_sql_file("update_participants_team_validity.sql"))

# 2. Trigger to set a participant's team_is_valid when they join a team
set_participant_team_validity_trigger = DDL(
    load_sql_file("set_participant_team_validity.sql"))

# Bind triggers to their respective tables
event.listen(Team.__table__, 'after_create',
             update_participants_team_validity_trigger)
event.listen(Participant.__table__, 'after_create',
             set_participant_team_validity_trigger)

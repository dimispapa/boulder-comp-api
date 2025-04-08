from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import UTC

if TYPE_CHECKING:
    from database.models.competitions import Participant, Competition


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


# Base User model used for database table definition - NO password fields
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    first_name: str
    last_name: str
    email: str
    hashed_password: str
    confirmed_at: Optional[datetime] = None
    role: UserRole = Field(default=UserRole.USER)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    participants: List["Participant"] = Relationship(back_populates="user")


class CompVoucher(SQLModel, table=True):
    __tablename__ = "comp_vouchers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str
    code: int
    code_used_at: Optional[datetime] = None
    competition_id: UUID = Field(foreign_key="competitions.id")
    participant_id: Optional[UUID] = Field(default=None,
                                           foreign_key="participants.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    competition: "Competition" = Relationship(back_populates="comp_vouchers")
    participant: Optional["Participant"] = Relationship(
        back_populates="comp_voucher")

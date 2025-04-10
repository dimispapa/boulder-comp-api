from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import UTC

if TYPE_CHECKING:
    from database.models.competitions import Participant


class UserRole(str, Enum):
    user = "user"
    admin = "admin"
    moderator = "moderator"


# Base User model used for database table definition - NO password fields
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    first_name: str
    last_name: str
    email: str = Field(unique=True)
    hashed_password: str
    confirmed_at: Optional[datetime] = None
    role: UserRole = Field(default=UserRole.user)
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    participants: List["Participant"] = Relationship(back_populates="user")
    otps: List["UserOtp"] = Relationship(back_populates="user")


class UserOtp(SQLModel, table=True):
    __tablename__ = "user_otps"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_code: bytes
    context: str = Field(index=True)
    sent_to: str
    user_id: UUID = Field(foreign_key="users.id", index=True)
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    user: "User" = Relationship(back_populates="otps")

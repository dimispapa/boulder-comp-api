"""
SQLModel models related to crags, sectors, boulders, routes and photos.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, UTC
from uuid import UUID, uuid4
import json
from sqlalchemy.dialects.postgresql import JSONB

# Type hints for forward references
if TYPE_CHECKING:
    from database.models.competitions import Ascent, Competition
    from database.models.media import BoulderPhoto
    from database.models.scoring import RemoteBoulderBonus


class Crag(SQLModel, table=True):
    """Climbing crag model."""
    __tablename__ = "crags"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True)
    display_name: str = Field(unique=True)
    description: Optional[str] = None
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    sectors: List["Sector"] = Relationship(back_populates="crag")
    competitions: List["Competition"] = Relationship(back_populates="crag")


class Sector(SQLModel, table=True):
    """Sector within a climbing crag."""
    __tablename__ = "sectors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True)
    display_name: str = Field(unique=True)
    crag_id: UUID = Field(foreign_key="crags.id")
    description: Optional[str] = None
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    crag: Crag = Relationship(back_populates="sectors")
    boulders: List["Boulder"] = Relationship(back_populates="sector")
    boulder_mappings: List["BoulderSectorMapping"] = Relationship(
        back_populates="sector")


class Boulder(SQLModel, table=True):
    """Boulder model with routes and photos."""
    __tablename__ = "boulders"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sector_id: UUID = Field(foreign_key="sectors.id")
    name: str
    display_name: str
    url: str = Field(unique=True)
    gps_postgis: Optional[str] = None  # PostGIS formatted point as string
    gps_string: Optional[str] = None  # Raw GPS coordinates
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    sector: Sector = Relationship(back_populates="boulders")
    routes: List["Route"] = Relationship(back_populates="boulder")
    photos: List["BoulderPhoto"] = Relationship(back_populates="boulder")
    remote_config: Optional["RemoteBoulderBonus"] = Relationship(
        sa_relationship_kwargs={"uselist": False})


class Route(SQLModel, table=True):
    """Climbing route on a boulder."""
    __tablename__ = "routes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    boulder_id: UUID = Field(foreign_key="boulders.id")
    name: str
    display_name: str
    url: str = Field(unique=True)
    grade: str
    rating: Optional[float] = None
    description: Optional[str] = None
    line_data: Optional[str] = Field(default=None, sa_type=JSONB)
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    boulder: Boulder = Relationship(back_populates="routes")
    ascents: List["Ascent"] = Relationship(back_populates="route")

    # SQLModel doesn't handle JSON/JSONB fields directly
    @property
    def line_data_dict(self) -> Dict[str, Any]:
        """Get line_data as a Python dictionary."""
        if not self.line_data:
            return {}
        return json.loads(self.line_data)

    @line_data_dict.setter
    def line_data_dict(self, value: Dict[str, Any]):
        """Set line_data from a Python dictionary."""
        if not value:
            self.line_data = None
        else:
            self.line_data = json.dumps(value)


class BoulderSectorMapping(SQLModel, table=True):
    """Mapping between boulder URLs and sectors."""
    __tablename__ = "boulder_sector_mappings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    boulder_url: str = Field(unique=True)
    sector_name: str
    sector_id: UUID = Field(foreign_key="sectors.id")
    inserted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    sector: Sector = Relationship(back_populates="boulder_mappings")

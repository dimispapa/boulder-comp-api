from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class RouteLineData:
    photo_id: str  # Reference to the specific photo this line appears on
    line_points: List[Dict[str, float]]  # The actual line coordinates

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {'photo_id': self.photo_id, 'line_points': self.line_points}


@dataclass
class Route:
    """Class representing a climbing route."""
    name: str
    url: str
    grade: str
    rating: float
    description: str
    line_data: List[RouteLineData] = field(default_factory=list)
    display_name: str = None  # Will use name if not provided explicitly

    def __post_init__(self):
        # If display_name is not provided, use name
        if self.display_name is None:
            self.display_name = self.name

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'url': self.url,
            'grade': self.grade,
            'rating': self.rating,
            'description': self.description,
            'line_data': [ld.to_dict() for ld in self.line_data]
        }

    def __repr__(self) -> str:
        """String representation for debugging and serialization."""
        return (f"Route(name='{self.name}', url='{self.url}', "
                f"grade='{self.grade}', rating='{self.rating}', "
                f"description='{self.description}')")


@dataclass
class BoulderPhoto:
    id: str  # Unique identifier for the photo
    source_url: str
    lines_data: Dict[str, Any] = field(default_factory=dict)
    order: int = 1

    def __init__(self,
                 id: str,
                 source_url: str,
                 order: int,
                 lines_data: dict = None):
        self.id = id
        self.source_url = source_url
        self.order = order
        self.lines_data = lines_data or {}  # Default to empty dict if None

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'source_url': self.source_url,
            'order': self.order,
            'lines_data': self.lines_data
        }


@dataclass
class Boulder:
    name: str
    url: str
    gps_postgis: str
    gps_string: str
    routes: List[Route]
    photos: List[BoulderPhoto] = field(default_factory=list)
    display_name: str = None  # Will use name if not provided explicitly

    def __post_init__(self):
        # If display_name is not provided, use name
        if self.display_name is None:
            self.display_name = self.name

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'url': self.url,
            'gps_postgis': self.gps_postgis,
            'gps_string': self.gps_string,
            'routes': [route.to_dict() for route in self.routes],
            'photos': [photo.to_dict() for photo in self.photos]
        }

    def __repr__(self) -> str:
        """String representation for debugging and serialization."""
        return (f"Boulder(name='{self.name}', url='{self.url}', "
                f"gps_postgis='{self.gps_postgis}', "
                f"gps_string='{self.gps_string}')")


@dataclass
class Crag:
    name: str
    display_name: str
    boulders: List[Boulder]

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'boulders': [boulder.to_dict() for boulder in self.boulders]
        }

    def __repr__(self) -> str:
        """String representation for debugging and serialization."""
        return (f"Crag(name='{self.name}', "
                f"display_name='{self.display_name}', "
                f"boulders_count={len(self.boulders)})")

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

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
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
    url: str
    lines_data: Dict[str,
                     Any]  # Raw lines data from the page (includes all routes)

    def __init__(self, id: str, url: str, lines_data: dict = None):
        self.id = id
        self.url = url
        self.lines_data = lines_data or {}  # Default to empty dict if None

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {'id': self.id, 'url': self.url, 'lines_data': self.lines_data}


@dataclass
class Boulder:
    name: str
    url: str
    gps_postgis: str
    gps_string: str
    routes: List[Route]
    photos: List[BoulderPhoto] = field(default_factory=list)

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
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
    boulders: List[Boulder]

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'boulders': [boulder.to_dict() for boulder in self.boulders]
        }

    def __repr__(self) -> str:
        """String representation for debugging and serialization."""
        return f"Crag(name='{self.name}', boulders_count={len(self.boulders)})"

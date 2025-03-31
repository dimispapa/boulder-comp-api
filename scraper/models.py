from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class RouteLineData:
    photo_id: str  # Reference to the specific photo this line appears on
    line_points: List[Dict[str, float]]  # The actual line coordinates


@dataclass
class Route:
    """Class representing a climbing route."""
    name: str
    url: str
    grade: str
    rating: float
    description: str
    line_data: List[RouteLineData] = field(default_factory=list)

    def to_supabase_dict(self):
        return {
            'name': self.name,
            'url': self.url,
            'grade': self.grade,
            'rating': self.rating,
            'description': self.description,
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

    def to_supabase_dict(self):
        return {
            'id': self.id,  # This is our photo_id field in the database
            'url': self.url,
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

    def to_supabase_dict(self):
        return {
            'name': self.name,
            'url': self.url,
            'gps_postgis': self.gps_postgis,
            'gps_string': self.gps_string,
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

    def to_supabase_dict(self):
        return {
            'name': self.name,
        }

    def __repr__(self) -> str:
        """String representation for debugging and serialization."""
        return f"Crag(name='{self.name}', boulders_count={len(self.boulders)})"

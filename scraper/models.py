from dataclasses import dataclass
from typing import List


@dataclass
class Route:
    name: str
    url: str
    grade: str
    rating: str
    description: str

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
class Boulder:
    name: str
    url: str
    gps_postgis: str
    gps_string: str
    routes: List[Route]

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

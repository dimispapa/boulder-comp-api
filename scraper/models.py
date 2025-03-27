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


@dataclass
class Boulder:
    name: str
    url: str
    gps_coords: str
    routes: List[Route]

    def to_supabase_dict(self):
        return {
            'name': self.name,
            'url': self.url,
            'gps_coords': self.gps_coords,
        }


@dataclass
class Crag:
    name: str
    boulders: List[Boulder]

    def to_supabase_dict(self):
        return {
            'name': self.name,
        }

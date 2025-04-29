"""
Enum definitions for the database models.
"""
from enum import Enum


class CompetitionStatus(str, Enum):
    """Competition status enum."""
    upcoming = "upcoming"
    ongoing = "ongoing"
    completed = "completed"


class CategoryType(str, Enum):
    """Competition category type enum."""
    marathon = "marathon"
    boulder_beasts = "boulder_beasts"


class MarathonSubCategory(str, Enum):
    """Marathon sub-category enum."""
    lt_6B = "6A+ and under"
    gte_6B = "6B and above"


class UserRole(str, Enum):
    """User role enum."""
    user = "user"
    moderator = "moderator"
    admin = "admin"

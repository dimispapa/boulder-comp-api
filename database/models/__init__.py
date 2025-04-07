"""
SQLModel models for the Boulder Competition API database.

Import all models here for easy access and to ensure they are registered with
SQLModel.
"""

from database.models.crags import (  # noqa: F401
    Crag, Sector, Boulder, Route, BoulderSectorMapping)
from database.models.competitions import (  # noqa: F401
    Competition, Team, Participant, Ascent, CompetitionCategory, CategoryType,
    CompetitionStatus)
from database.models.scoring import (  # noqa: F401
    BasePoints, VolumeBonus, UniqueAscentBonus, TeamAscentBonus,
    MasterGradeBonus, MarathonRanking, MarathonDetailedResults,
    BoulderBeastsRanking,
)
from database.models.media import CompetitionPhoto, BoulderPhoto  # noqa: F401

# This allows imports like: from database.models import Crag, Sector, etc.

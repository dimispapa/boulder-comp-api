"""
SQLModel models for the Boulder Competition API database.
"""
# Import all models here for easy access and to ensure they are registered with SQLModel
from database.models.crags import Crag, Sector, Boulder, BoulderPhoto, Route, BoulderSectorMapping
from database.models.competitions import Competition, Team, Participant, Ascent
from database.models.scoring import (BasePoints, VolumeBonus,
                                     UniqueAscentBonus, TeamAscentBonus,
                                     MasterGradeBonus, ScoredAscent,
                                     MarathonRanking, BoulderBeastsRanking)

# This allows imports like: from database.models import Crag, Sector, etc.

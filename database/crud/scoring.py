"""
CRUD operations for scoring-related models.
"""
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select

from database.models.scoring import (BasePoints, VolumeBonus,
                                     UniqueAscentBonus, TeamAscentBonus,
                                     MasterGradeBonus, ScoredAscent,
                                     MarathonRanking, BoulderBeastsRanking)


# BasePoints operations
def get_base_points_by_id(session: Session, id: UUID) -> Optional[BasePoints]:
    """Get base points configuration by ID."""
    return session.get(BasePoints, id)


def get_base_points_by_grade(session: Session,
                             grade: str) -> Optional[BasePoints]:
    """Get base points configuration by grade."""
    statement = select(BasePoints).where(BasePoints.grade == grade)
    return session.exec(statement).first()


def get_all_base_points(session: Session) -> List[BasePoints]:
    """Get all base points configurations."""
    statement = select(BasePoints)
    return session.exec(statement).all()


def create_base_points(session: Session,
                       base_points: BasePoints) -> BasePoints:
    """Create a new base points configuration."""
    session.add(base_points)
    session.commit()
    session.refresh(base_points)
    return base_points


def update_base_points(session: Session,
                       base_points: BasePoints) -> BasePoints:
    """Update an existing base points configuration."""
    session.add(base_points)
    session.commit()
    session.refresh(base_points)
    return base_points


def delete_base_points(session: Session, id: UUID) -> bool:
    """Delete a base points configuration by ID."""
    base_points = session.get(BasePoints, id)
    if base_points:
        session.delete(base_points)
        session.commit()
        return True
    return False


# VolumeBonus operations
def get_volume_bonus_by_id(session: Session,
                           id: UUID) -> Optional[VolumeBonus]:
    """Get volume bonus configuration by ID."""
    return session.get(VolumeBonus, id)


def get_all_volume_bonuses(session: Session) -> List[VolumeBonus]:
    """Get all volume bonus configurations."""
    statement = select(VolumeBonus)
    return session.exec(statement).all()


def create_volume_bonus(session: Session,
                        volume_bonus: VolumeBonus) -> VolumeBonus:
    """Create a new volume bonus configuration."""
    session.add(volume_bonus)
    session.commit()
    session.refresh(volume_bonus)
    return volume_bonus


def update_volume_bonus(session: Session,
                        volume_bonus: VolumeBonus) -> VolumeBonus:
    """Update an existing volume bonus configuration."""
    session.add(volume_bonus)
    session.commit()
    session.refresh(volume_bonus)
    return volume_bonus


def delete_volume_bonus(session: Session, id: UUID) -> bool:
    """Delete a volume bonus configuration by ID."""
    volume_bonus = session.get(VolumeBonus, id)
    if volume_bonus:
        session.delete(volume_bonus)
        session.commit()
        return True
    return False


# UniqueAscentBonus operations
def get_unique_bonus_by_id(session: Session,
                           id: UUID) -> Optional[UniqueAscentBonus]:
    """Get unique ascent bonus configuration by ID."""
    return session.get(UniqueAscentBonus, id)


def get_all_unique_bonuses(session: Session) -> List[UniqueAscentBonus]:
    """Get all unique ascent bonus configurations."""
    statement = select(UniqueAscentBonus)
    return session.exec(statement).all()


def create_unique_bonus(session: Session,
                        unique_bonus: UniqueAscentBonus) -> UniqueAscentBonus:
    """Create a new unique ascent bonus configuration."""
    session.add(unique_bonus)
    session.commit()
    session.refresh(unique_bonus)
    return unique_bonus


def update_unique_bonus(session: Session,
                        unique_bonus: UniqueAscentBonus) -> UniqueAscentBonus:
    """Update an existing unique ascent bonus configuration."""
    session.add(unique_bonus)
    session.commit()
    session.refresh(unique_bonus)
    return unique_bonus


def delete_unique_bonus(session: Session, id: UUID) -> bool:
    """Delete a unique ascent bonus configuration by ID."""
    unique_bonus = session.get(UniqueAscentBonus, id)
    if unique_bonus:
        session.delete(unique_bonus)
        session.commit()
        return True
    return False


# TeamAscentBonus operations
def get_team_bonus_by_id(session: Session,
                         id: UUID) -> Optional[TeamAscentBonus]:
    """Get team ascent bonus configuration by ID."""
    return session.get(TeamAscentBonus, id)


def get_team_bonus_by_size(session: Session,
                           team_size: int) -> Optional[TeamAscentBonus]:
    """Get team ascent bonus configuration by team size."""
    statement = select(TeamAscentBonus).where(
        TeamAscentBonus.team_size == team_size)
    return session.exec(statement).first()


def get_all_team_bonuses(session: Session) -> List[TeamAscentBonus]:
    """Get all team ascent bonus configurations."""
    statement = select(TeamAscentBonus)
    return session.exec(statement).all()


def create_team_bonus(session: Session,
                      team_bonus: TeamAscentBonus) -> TeamAscentBonus:
    """Create a new team ascent bonus configuration."""
    session.add(team_bonus)
    session.commit()
    session.refresh(team_bonus)
    return team_bonus


def update_team_bonus(session: Session,
                      team_bonus: TeamAscentBonus) -> TeamAscentBonus:
    """Update an existing team ascent bonus configuration."""
    session.add(team_bonus)
    session.commit()
    session.refresh(team_bonus)
    return team_bonus


def delete_team_bonus(session: Session, id: UUID) -> bool:
    """Delete a team ascent bonus configuration by ID."""
    team_bonus = session.get(TeamAscentBonus, id)
    if team_bonus:
        session.delete(team_bonus)
        session.commit()
        return True
    return False


# MasterGradeBonus operations
def get_master_grade_bonus_by_id(session: Session,
                                 id: UUID) -> Optional[MasterGradeBonus]:
    """Get master grade bonus configuration by ID."""
    return session.get(MasterGradeBonus, id)


def get_all_master_grade_bonuses(session: Session) -> List[MasterGradeBonus]:
    """Get all master grade bonus configurations."""
    statement = select(MasterGradeBonus)
    return session.exec(statement).all()


def create_master_grade_bonus(session: Session,
                              bonus: MasterGradeBonus) -> MasterGradeBonus:
    """Create a new master grade bonus configuration."""
    session.add(bonus)
    session.commit()
    session.refresh(bonus)
    return bonus


def update_master_grade_bonus(session: Session,
                              bonus: MasterGradeBonus) -> MasterGradeBonus:
    """Update an existing master grade bonus configuration."""
    session.add(bonus)
    session.commit()
    session.refresh(bonus)
    return bonus


def delete_master_grade_bonus(session: Session, id: UUID) -> bool:
    """Delete a master grade bonus configuration by ID."""
    bonus = session.get(MasterGradeBonus, id)
    if bonus:
        session.delete(bonus)
        session.commit()
        return True
    return False


# ScoredAscent operations
def get_scored_ascent_by_id(session: Session,
                            id: UUID) -> Optional[ScoredAscent]:
    """Get a scored ascent by ID."""
    return session.get(ScoredAscent, id)


def get_scored_ascents_by_ascent_id(session: Session,
                                    ascent_id: UUID) -> List[ScoredAscent]:
    """Get scored ascents by original ascent ID."""
    statement = select(ScoredAscent).where(ScoredAscent.ascent_id == ascent_id)
    return session.exec(statement).all()


def get_scored_ascents_by_participant(
        session: Session, participant_id: UUID) -> List[ScoredAscent]:
    """Get all scored ascents for a participant."""
    statement = select(ScoredAscent).where(
        ScoredAscent.participant_id == participant_id)
    return session.exec(statement).all()


def create_scored_ascent(session: Session,
                         scored_ascent: ScoredAscent) -> ScoredAscent:
    """Create a new scored ascent."""
    session.add(scored_ascent)
    session.commit()
    session.refresh(scored_ascent)
    return scored_ascent


def update_scored_ascent(session: Session,
                         scored_ascent: ScoredAscent) -> ScoredAscent:
    """Update an existing scored ascent."""
    session.add(scored_ascent)
    session.commit()
    session.refresh(scored_ascent)
    return scored_ascent


def delete_scored_ascent(session: Session, id: UUID) -> bool:
    """Delete a scored ascent by ID."""
    scored_ascent = session.get(ScoredAscent, id)
    if scored_ascent:
        session.delete(scored_ascent)
        session.commit()
        return True
    return False


# MarathonRanking operations
def get_marathon_ranking_by_id(session: Session,
                               id: UUID) -> Optional[MarathonRanking]:
    """Get a marathon ranking by ID."""
    return session.get(MarathonRanking, id)


def get_marathon_ranking_by_team(session: Session,
                                 team_id: UUID) -> Optional[MarathonRanking]:
    """Get a marathon ranking by team ID."""
    statement = select(MarathonRanking).where(
        MarathonRanking.team_id == team_id)
    return session.exec(statement).first()


def get_all_marathon_rankings(session: Session) -> List[MarathonRanking]:
    """Get all marathon rankings."""
    statement = select(MarathonRanking).order_by(MarathonRanking.rank)
    return session.exec(statement).all()


def create_marathon_ranking(session: Session,
                            ranking: MarathonRanking) -> MarathonRanking:
    """Create a new marathon ranking."""
    session.add(ranking)
    session.commit()
    session.refresh(ranking)
    return ranking


def update_marathon_ranking(session: Session,
                            ranking: MarathonRanking) -> MarathonRanking:
    """Update an existing marathon ranking."""
    session.add(ranking)
    session.commit()
    session.refresh(ranking)
    return ranking


def delete_marathon_ranking(session: Session, id: UUID) -> bool:
    """Delete a marathon ranking by ID."""
    ranking = session.get(MarathonRanking, id)
    if ranking:
        session.delete(ranking)
        session.commit()
        return True
    return False


# BoulderBeastsRanking operations
def get_boulder_beasts_ranking_by_id(
        session: Session, id: UUID) -> Optional[BoulderBeastsRanking]:
    """Get a boulder beasts ranking by ID."""
    return session.get(BoulderBeastsRanking, id)


def get_boulder_beasts_by_participant(
        session: Session,
        participant_id: UUID) -> Optional[BoulderBeastsRanking]:
    """Get a boulder beasts ranking by participant ID."""
    statement = select(BoulderBeastsRanking).where(
        BoulderBeastsRanking.participant_id == participant_id)
    return session.exec(statement).first()


def get_all_boulder_beasts_rankings(
        session: Session) -> List[BoulderBeastsRanking]:
    """Get all boulder beasts rankings."""
    statement = select(BoulderBeastsRanking).order_by(
        BoulderBeastsRanking.rank)
    return session.exec(statement).all()


def create_boulder_beasts_ranking(
        session: Session,
        ranking: BoulderBeastsRanking) -> BoulderBeastsRanking:
    """Create a new boulder beasts ranking."""
    session.add(ranking)
    session.commit()
    session.refresh(ranking)
    return ranking


def update_boulder_beasts_ranking(
        session: Session,
        ranking: BoulderBeastsRanking) -> BoulderBeastsRanking:
    """Update an existing boulder beasts ranking."""
    session.add(ranking)
    session.commit()
    session.refresh(ranking)
    return ranking


def delete_boulder_beasts_ranking(session: Session, id: UUID) -> bool:
    """Delete a boulder beasts ranking by ID."""
    ranking = session.get(BoulderBeastsRanking, id)
    if ranking:
        session.delete(ranking)
        session.commit()
        return True
    return False

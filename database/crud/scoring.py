"""
CRUD operations for scoring-related models.
"""
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select
from datetime import datetime, UTC

from database.models.scoring import (BasePoints, VolumeBonus,
                                     UniqueAscentBonus, TeamAscentBonus,
                                     MasterGradeBonus, MarathonRanking,
                                     BoulderBeastsRanking,
                                     MarathonDetailedResults)


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


def get_marathon_detailed_results_by_id(
        session: Session, id: UUID) -> Optional[MarathonDetailedResults]:
    """Get a marathon detailed results by ID."""
    return session.get(MarathonDetailedResults, id)


def get_marathon_detailed_results_by_team(
        session: Session, competition_id: UUID,
        team_id: UUID) -> Optional[MarathonDetailedResults]:
    """Get a marathon detailed results by team ID and competition ID."""
    statement = select(MarathonDetailedResults).where(
        MarathonDetailedResults.competition_id == competition_id,
        MarathonDetailedResults.team_id == team_id)
    return session.exec(statement).first()


def get_all_marathon_detailed_results(
        session: Session,
        competition_id: UUID) -> List[MarathonDetailedResults]:
    """Get all marathon detailed results for a competition."""
    statement = select(MarathonDetailedResults).where(
        MarathonDetailedResults.competition_id == competition_id)
    return session.exec(statement).all()


def create_marathon_detailed_results(
        session: Session,
        results: MarathonDetailedResults) -> MarathonDetailedResults:
    """Create a new marathon detailed results."""
    session.add(results)
    session.commit()
    session.refresh(results)
    return results


def update_marathon_detailed_results(
        session: Session,
        results: MarathonDetailedResults) -> MarathonDetailedResults:
    """Update an existing marathon detailed results."""
    session.add(results)
    session.commit()
    session.refresh(results)
    return results


def delete_marathon_detailed_results(session: Session, id: UUID) -> bool:
    """Delete a marathon detailed results by ID."""
    results = session.get(MarathonDetailedResults, id)
    if results:
        session.delete(results)
        session.commit()
        return True
    return False


# Upsert operations (Create or Update)
def create_or_update_marathon_ranking(
        session: Session, ranking: MarathonRanking) -> MarathonRanking:
    """Create or update a marathon ranking."""
    # Try to find by team_id which should be unique
    existing = get_marathon_ranking_by_team(session, ranking.team_id)

    if existing:
        # Update fields
        existing.competition_id = ranking.competition_id
        existing.team_id = ranking.team_id
        existing.team_size = ranking.team_size
        existing.base_score = ranking.base_score
        existing.volume_bonus = ranking.volume_bonus
        existing.unique_ascent_bonus = ranking.unique_ascent_bonus
        existing.master_grade_bonus = ranking.master_grade_bonus
        existing.team_ascent_bonus = ranking.team_ascent_bonus
        existing.total_score = ranking.total_score
        existing.rank = ranking.rank
        existing.updated_at = datetime.now(UTC)

        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    else:
        # Create new record
        session.add(ranking)
        session.commit()
        session.refresh(ranking)
        return ranking


def create_or_update_boulder_beasts_ranking(
        session: Session,
        ranking: BoulderBeastsRanking) -> BoulderBeastsRanking:
    """Create or update a boulder beasts ranking."""
    # Try to find by participant_id which should be unique per competition
    existing = get_boulder_beasts_by_participant(session,
                                                 ranking.participant_id)

    if existing:
        # Update fields
        existing.competition_id = ranking.competition_id
        existing.participant_id = ranking.participant_id
        existing.total_score = ranking.total_score
        existing.top_5_routes = ranking.top_5_routes
        existing.top_5_routes_score = ranking.top_5_routes_score
        existing.rank = ranking.rank
        existing.updated_at = datetime.now(UTC)

        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    else:
        # Create new record
        session.add(ranking)
        session.commit()
        session.refresh(ranking)
        return ranking


def create_or_update_marathon_detailed_results(
        session: Session,
        results: MarathonDetailedResults) -> MarathonDetailedResults:
    """Create or update a marathon detailed results."""
    # Try to find by team_id which should be unique per competition
    existing = get_marathon_detailed_results_by_team(session,
                                                     results.competition_id,
                                                     results.team_id)

    if existing:
        # Update fields
        existing.team_name = results.team_name
        existing.team_size = results.team_size
        existing.routes = results.routes
        existing.total_ascents = results.total_ascents
        existing.volume_bonus = results.volume_bonus
        existing.team_completed_routes = results.team_completed_routes
        existing.team_unique_routes = results.team_unique_routes
        existing.master_grades = results.master_grades
        existing.master_grade_bonus = results.master_grade_bonus
        existing.base_score = results.base_score
        existing.team_ascent_bonus = results.team_ascent_bonus
        existing.unique_ascent_bonus = results.unique_ascent_bonus
        existing.total_score = results.total_score
        existing.normalized_score = results.normalized_score
        existing.updated_at = datetime.now(UTC)

        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    else:
        # Create new record
        session.add(results)
        session.commit()
        session.refresh(results)
        return results

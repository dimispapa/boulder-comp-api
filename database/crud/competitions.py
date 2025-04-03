"""
CRUD operations for competition-related models.
"""
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select

from database.models.competitions import (Competition, Team, Participant,
                                          Ascent, CompetitionStatus)
from database.models.media import CompetitionPhoto


# Competition operations
def get_competition_by_id(session: Session,
                          comp_id: UUID) -> Optional[Competition]:
    """Get a competition by its ID."""
    return session.get(Competition, comp_id)


def get_competition_by_name(session: Session,
                            name: str) -> Optional[Competition]:
    """Get a competition by its name."""
    statement = select(Competition).where(Competition.name == name)
    return session.exec(statement).first()


def get_all_competitions(session: Session) -> List[Competition]:
    """Get all competitions."""
    statement = select(Competition)
    return session.exec(statement).all()


def get_competitions_by_status(session: Session,
                               status: CompetitionStatus) -> List[Competition]:
    """Get competitions by their status."""
    statement = select(Competition).where(Competition.status == status.value)
    return session.exec(statement).all()


def create_competition(session: Session,
                       competition: Competition) -> Competition:
    """Create a new competition."""
    session.add(competition)
    session.commit()
    session.refresh(competition)
    return competition


def update_competition(session: Session,
                       competition: Competition) -> Competition:
    """Update an existing competition."""
    session.add(competition)
    session.commit()
    session.refresh(competition)
    return competition


def delete_competition(session: Session, comp_id: UUID) -> bool:
    """Delete a competition by ID."""
    competition = session.get(Competition, comp_id)
    if competition:
        session.delete(competition)
        session.commit()
        return True
    return False


# Team operations
def get_team_by_id(session: Session, team_id: UUID) -> Optional[Team]:
    """Get a team by its ID."""
    return session.get(Team, team_id)


def get_teams_by_competition_id(session: Session, comp_id: UUID) -> List[Team]:
    """Get all teams for a specific competition."""
    statement = select(Team).where(Team.competition_id == comp_id)
    return session.exec(statement).all()


def create_team(session: Session, team: Team) -> Team:
    """Create a new team."""
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


def update_team(session: Session, team: Team) -> Team:
    """Update an existing team."""
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


def delete_team(session: Session, team_id: UUID) -> bool:
    """Delete a team by ID."""
    team = session.get(Team, team_id)
    if team:
        session.delete(team)
        session.commit()
        return True
    return False


# Participant operations
def get_participant_by_id(session: Session,
                          participant_id: UUID) -> Optional[Participant]:
    """Get a participant by its ID."""
    return session.get(Participant, participant_id)


def get_participants_by_competition_id(session: Session,
                                       comp_id: UUID) -> List[Participant]:
    """Get all participants for a specific competition."""
    statement = select(Participant).where(
        Participant.competition_id == comp_id)
    return session.exec(statement).all()


def get_participants_by_team_id(session: Session,
                                team_id: UUID) -> List[Participant]:
    """Get all participants for a specific team."""
    statement = select(Participant).where(Participant.team_id == team_id)
    return session.exec(statement).all()


def get_participant_by_user_and_competition(
        session: Session, user_id: UUID,
        competition_id: UUID) -> Optional[Participant]:
    """Get a participant by user ID and competition ID."""
    statement = select(Participant).where(
        Participant.user_id == user_id,
        Participant.competition_id == competition_id)
    return session.exec(statement).first()


def get_solo_participants(session: Session,
                          comp_id: UUID) -> List[Participant]:
    """Get all solo participants (boulder beasts) for a competition."""
    statement = select(Participant).where(
        Participant.competition_id == comp_id,
        Participant.solo_entry == True  # noqa: E712
    )
    return session.exec(statement).all()


def create_participant(session: Session,
                       participant: Participant) -> Participant:
    """Create a new participant."""
    session.add(participant)
    session.commit()
    session.refresh(participant)
    return participant


def update_participant(session: Session,
                       participant: Participant) -> Participant:
    """Update an existing participant."""
    session.add(participant)
    session.commit()
    session.refresh(participant)
    return participant


def delete_participant(session: Session, participant_id: UUID) -> bool:
    """Delete a participant by ID."""
    participant = session.get(Participant, participant_id)
    if participant:
        session.delete(participant)
        session.commit()
        return True
    return False


# Ascent operations
def get_ascent_by_id(session: Session, ascent_id: UUID) -> Optional[Ascent]:
    """Get an ascent by its ID."""
    return session.get(Ascent, ascent_id)


def get_ascents_by_participant_id(session: Session,
                                  participant_id: UUID) -> List[Ascent]:
    """Get all ascents for a specific participant."""
    statement = select(Ascent).where(Ascent.participant_id == participant_id)
    return session.exec(statement).all()


def get_ascents_by_competition_id(session: Session,
                                  comp_id: UUID) -> List[Ascent]:
    """Get all ascents for a specific competition."""
    statement = select(Ascent).where(Ascent.competition_id == comp_id)
    return session.exec(statement).all()


def get_ascents_by_route_id(session: Session, route_id: UUID) -> List[Ascent]:
    """Get all ascents for a specific route."""
    statement = select(Ascent).where(Ascent.route_id == route_id)
    return session.exec(statement).all()


def create_ascent(session: Session, ascent: Ascent) -> Ascent:
    """Create a new ascent."""
    session.add(ascent)
    session.commit()
    session.refresh(ascent)
    return ascent


def update_ascent(session: Session, ascent: Ascent) -> Ascent:
    """Update an existing ascent."""
    session.add(ascent)
    session.commit()
    session.refresh(ascent)
    return ascent


def delete_ascent(session: Session, ascent_id: UUID) -> bool:
    """Delete an ascent by ID."""
    ascent = session.get(Ascent, ascent_id)
    if ascent:
        session.delete(ascent)
        session.commit()
        return True
    return False


# Competition Photo operations
def get_competition_photo_by_id(session: Session,
                                photo_id: UUID) -> Optional[CompetitionPhoto]:
    """Get a competition photo by its ID."""
    return session.get(CompetitionPhoto, photo_id)


def get_competition_photos_by_competition_id(
        session: Session, comp_id: UUID) -> List[CompetitionPhoto]:
    """Get all photos for a specific competition."""
    statement = select(CompetitionPhoto).where(
        CompetitionPhoto.competition_id == comp_id)
    return session.exec(statement).all()


def get_competition_photos_without_cloudinary_url(
        session: Session, comp_id: UUID) -> List[CompetitionPhoto]:
    """Get all photos that need to be uploaded
    to Cloudinary for a competition."""
    statement = select(CompetitionPhoto).where(
        CompetitionPhoto.competition_id == comp_id,
        CompetitionPhoto.cloudinary_url == None  # noqa: E711
    )
    return session.exec(statement).all()


def get_competition_photos_by_uploader_id(
        session: Session, uploader_id: UUID) -> List[CompetitionPhoto]:
    """Get all photos uploaded by a specific participant."""
    statement = select(CompetitionPhoto).where(
        CompetitionPhoto.uploader_id == uploader_id)
    return session.exec(statement).all()


def create_competition_photo(session: Session,
                             photo: CompetitionPhoto) -> CompetitionPhoto:
    """Create a new competition photo record."""
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def update_competition_photo(session: Session,
                             photo: CompetitionPhoto) -> CompetitionPhoto:
    """Update an existing competition photo record."""
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def delete_competition_photo(session: Session, photo_id: UUID) -> bool:
    """Delete a competition photo by ID."""
    photo = session.get(CompetitionPhoto, photo_id)
    if photo:
        session.delete(photo)
        session.commit()
        return True
    return False


def get_participants_by_ids(session: Session,
                            participant_ids: List[UUID]) -> List[Participant]:
    """Get multiple participants by their IDs."""
    if not participant_ids:
        return []
    statement = select(Participant).where(Participant.id.in_(participant_ids))
    return session.exec(statement).all()

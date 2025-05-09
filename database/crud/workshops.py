"""
CRUD operations for workshops and workshop participants.
"""
from sqlmodel import Session, select
from typing import List, Optional, Dict

from database.models.workshops import Workshop, WorkshopParticipant


def get_workshop_by_name(session: Session, name: str) -> Optional[Workshop]:
    """Get a workshop by its name."""
    statement = select(Workshop).where(Workshop.name == name)
    return session.exec(statement).first()


def get_all_workshops(session: Session) -> List[Workshop]:
    """Get all workshops."""
    statement = select(Workshop)
    return session.exec(statement).all()


def get_workshop_participants(session: Session,
                              workshop_name: str) -> List[WorkshopParticipant]:
    """Get all participants for a specific workshop."""
    statement = select(WorkshopParticipant).where(
        WorkshopParticipant.workshop_name == workshop_name)
    return session.exec(statement).all()


def get_all_workshop_participants(
        session: Session) -> List[WorkshopParticipant]:
    """Get all workshop participants."""
    statement = select(WorkshopParticipant)
    return session.exec(statement).all()


def get_participants_by_workshop(
        session: Session) -> Dict[str, List[WorkshopParticipant]]:
    """Get all workshop participants grouped by workshop name."""
    # Get all workshops
    workshops = get_all_workshops(session)

    # Group participants by workshop
    participants_by_workshop = {}
    for workshop in workshops:
        participants = get_workshop_participants(session, workshop.name)
        participants_by_workshop[workshop.name] = participants

    return participants_by_workshop

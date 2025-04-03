"""
CRUD operations for crag-related models.
"""
from typing import List, Optional, Dict
from uuid import UUID
from sqlmodel import Session, select

from database.models.crags import (Crag, Sector, Boulder, BoulderPhoto, Route,
                                   BoulderSectorMapping)


# Crag operations
def get_crag_by_id(session: Session, crag_id: UUID) -> Optional[Crag]:
    """Get a crag by its ID."""
    return session.get(Crag, crag_id)


def get_crag_by_name(session: Session, name: str) -> Optional[Crag]:
    """Get a crag by its name."""
    statement = select(Crag).where(Crag.name == name)
    return session.exec(statement).first()


def get_all_crags(session: Session) -> List[Crag]:
    """Get all crags."""
    statement = select(Crag)
    return session.exec(statement).all()


def create_crag(session: Session, crag: Crag) -> Crag:
    """Create a new crag."""
    session.add(crag)
    session.commit()
    session.refresh(crag)
    return crag


def update_crag(session: Session, crag: Crag) -> Crag:
    """Update an existing crag."""
    session.add(crag)
    session.commit()
    session.refresh(crag)
    return crag


def delete_crag(session: Session, crag_id: UUID) -> bool:
    """Delete a crag by ID."""
    crag = session.get(Crag, crag_id)
    if crag:
        session.delete(crag)
        session.commit()
        return True
    return False


# Sector operations
def get_sector_by_id(session: Session, sector_id: UUID) -> Optional[Sector]:
    """Get a sector by its ID."""
    return session.get(Sector, sector_id)


def get_sector_by_name(session: Session, name: str) -> Optional[Sector]:
    """Get a sector by its name."""
    statement = select(Sector).where(Sector.name == name)
    return session.exec(statement).first()


def get_sectors_by_crag_id(session: Session, crag_id: UUID) -> List[Sector]:
    """Get all sectors for a specific crag."""
    statement = select(Sector).where(Sector.crag_id == crag_id)
    return session.exec(statement).all()


def create_sector(session: Session, sector: Sector) -> Sector:
    """Create a new sector."""
    session.add(sector)
    session.commit()
    session.refresh(sector)
    return sector


def update_sector(session: Session, sector: Sector) -> Sector:
    """Update an existing sector."""
    session.add(sector)
    session.commit()
    session.refresh(sector)
    return sector


def delete_sector(session: Session, sector_id: UUID) -> bool:
    """Delete a sector by ID."""
    sector = session.get(Sector, sector_id)
    if sector:
        session.delete(sector)
        session.commit()
        return True
    return False


# Boulder operations
def get_boulder_by_id(session: Session, boulder_id: UUID) -> Optional[Boulder]:
    """Get a boulder by its ID."""
    return session.get(Boulder, boulder_id)


def get_boulder_by_url(session: Session, url: str) -> Optional[Boulder]:
    """Get a boulder by its URL."""
    statement = select(Boulder).where(Boulder.url == url)
    return session.exec(statement).first()


def get_boulders_by_sector_id(session: Session,
                              sector_id: UUID) -> List[Boulder]:
    """Get all boulders for a specific sector."""
    statement = select(Boulder).where(Boulder.sector_id == sector_id)
    return session.exec(statement).all()


def create_boulder(session: Session, boulder: Boulder) -> Boulder:
    """Create a new boulder."""
    session.add(boulder)
    session.commit()
    session.refresh(boulder)
    return boulder


def update_boulder(session: Session, boulder: Boulder) -> Boulder:
    """Update an existing boulder."""
    session.add(boulder)
    session.commit()
    session.refresh(boulder)
    return boulder


def delete_boulder(session: Session, boulder_id: UUID) -> bool:
    """Delete a boulder by ID."""
    boulder = session.get(Boulder, boulder_id)
    if boulder:
        session.delete(boulder)
        session.commit()
        return True
    return False


# Route operations
def get_route_by_id(session: Session, route_id: UUID) -> Optional[Route]:
    """Get a route by its ID."""
    return session.get(Route, route_id)


def get_route_by_url(session: Session, url: str) -> Optional[Route]:
    """Get a route by its URL."""
    statement = select(Route).where(Route.url == url)
    return session.exec(statement).first()


def get_routes_by_boulder_id(session: Session,
                             boulder_id: UUID) -> List[Route]:
    """Get all routes for a specific boulder."""
    statement = select(Route).where(Route.boulder_id == boulder_id)
    return session.exec(statement).all()


def create_route(session: Session, route: Route) -> Route:
    """Create a new route."""
    session.add(route)
    session.commit()
    session.refresh(route)
    return route


def update_route(session: Session, route: Route) -> Route:
    """Update an existing route."""
    session.add(route)
    session.commit()
    session.refresh(route)
    return route


def delete_route(session: Session, route_id: UUID) -> bool:
    """Delete a route by ID."""
    route = session.get(Route, route_id)
    if route:
        session.delete(route)
        session.commit()
        return True
    return False


# BoulderPhoto operations
def get_photo_by_id(session: Session,
                    photo_id: UUID) -> Optional[BoulderPhoto]:
    """Get a photo by its ID."""
    return session.get(BoulderPhoto, photo_id)


def get_photos_by_boulder_id(session: Session,
                             boulder_id: UUID) -> List[BoulderPhoto]:
    """Get all photos for a specific boulder."""
    statement = select(BoulderPhoto).where(
        BoulderPhoto.boulder_id == boulder_id)
    return session.exec(statement).all()


def create_photo(session: Session, photo: BoulderPhoto) -> BoulderPhoto:
    """Create a new photo."""
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def update_photo(session: Session, photo: BoulderPhoto) -> BoulderPhoto:
    """Update an existing photo."""
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def delete_photo(session: Session, photo_id: UUID) -> bool:
    """Delete a photo by ID."""
    photo = session.get(BoulderPhoto, photo_id)
    if photo:
        session.delete(photo)
        session.commit()
        return True
    return False


# Boulder-Sector Mapping operations
def get_mapping_by_boulder_url(
        session: Session, boulder_url: str) -> Optional[BoulderSectorMapping]:
    """Get a mapping by boulder URL."""
    statement = select(BoulderSectorMapping).where(
        BoulderSectorMapping.boulder_url == boulder_url)
    return session.exec(statement).first()


def get_all_boulder_mappings(session: Session) -> Dict[str, UUID]:
    """
    Get all boulder-sector mappings as a dictionary.

    Returns:
        Dict[str, UUID]: Mapping of boulder URLs to sector IDs
    """
    statement = select(BoulderSectorMapping)
    mappings = session.exec(statement).all()
    return {mapping.boulder_url: mapping.sector_id for mapping in mappings}


def create_boulder_mapping(
        session: Session,
        mapping: BoulderSectorMapping) -> BoulderSectorMapping:
    """Create a new boulder-sector mapping."""
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    return mapping


def delete_boulder_mapping(session: Session, mapping_id: UUID) -> bool:
    """Delete a boulder-sector mapping by ID."""
    mapping = session.get(BoulderSectorMapping, mapping_id)
    if mapping:
        session.delete(mapping)
        session.commit()
        return True
    return False

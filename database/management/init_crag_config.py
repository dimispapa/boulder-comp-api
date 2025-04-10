#!/usr/bin/env python
"""
Database initialization and initial data import functions.
Can be run as a standalone script or imported as a module.
"""
import json
import argparse
from pathlib import Path
from sqlmodel import Session, select

from utils.loggers import logger
from database.management.base import get_db_session


def import_boulder_sector_mappings(session: Session):
    """Import boulder sector mappings from JSON file."""
    # Import here to avoid circular imports
    from database.models.crags import BoulderSectorMapping, Sector

    json_path = Path('data/initial/boulder_sector_mappings.json')
    if not json_path.exists():
        logger.error(
            f"Boulder sector mappings JSON file not found at {json_path}")
        return

    # Check if mappings already exist
    existing_count = session.exec(select(BoulderSectorMapping)).first()
    if existing_count:
        logger.info("Boulder sector mappings already exist in database, "
                    "skipping import")
        return

    try:
        # First, get all sectors by name for reference
        sectors = {}
        sector_results = session.exec(select(Sector))
        for sector in sector_results:
            sectors[sector.name.lower()] = sector.id

        if not sectors:
            logger.info("No sectors found in database. "
                        "Make sure sectors are created first.")
            return

        # Now read and import mappings
        with open(json_path, 'r') as f:
            mappings_data = json.load(f)
            mappings = []
            skipped = 0

            for item in mappings_data:
                sector_name = item['sector_name'].lower()
                if sector_name in sectors:
                    mapping = BoulderSectorMapping(
                        boulder_url=item['boulder_url'],
                        sector_name=item['sector_name'],
                        sector_id=sectors[sector_name])
                    mappings.append(mapping)
                else:
                    skipped += 1

            # Add all mappings in bulk
            if mappings:
                session.add_all(mappings)
                session.commit()
                logger.info(
                    f"Imported {len(mappings)} boulder sector mappings")
                if skipped > 0:
                    logger.info(
                        f"Skipped {skipped} mappings with unknown sectors")
            else:
                logger.info("No valid mappings found in JSON file")
    except Exception as e:
        session.rollback()
        logger.error(f"Error importing boulder sector mappings: {str(e)}")
        raise


def import_crags(session: Session):
    """Import initial crag data."""
    from database.models.crags import Crag

    # Check if crags already exist
    existing_count = session.exec(select(Crag)).first()
    if existing_count:
        logger.info("Crags already exist in database, skipping import")
        return

    json_path = Path('data/initial/crags.json')
    if not json_path.exists():
        logger.error(f"Crags JSON file not found at {json_path}")
        return

    # Import crags from JSON
    try:
        with open(json_path, 'r') as f:
            crags_data = json.load(f)
            crags = []

            for item in crags_data:
                crag = Crag(name=item['name'],
                            display_name=item['display_name'],
                            description=item.get('description'))
                crags.append(crag)

            if crags:
                session.add_all(crags)
                session.commit()
                logger.info(f"Imported {len(crags)} crags")
            else:
                logger.info("No crags found in JSON file")
    except Exception as e:
        session.rollback()
        logger.error(f"Error importing crags: {str(e)}")
        raise


def import_sectors(session: Session):
    """Import initial sector data."""
    from database.models.crags import Sector, Crag

    # Check if sectors already exist
    existing_count = session.exec(select(Sector)).first()
    if existing_count:
        logger.info("Sectors already exist in database, skipping import")
        return

    json_path = Path('data/initial/sectors.json')
    if not json_path.exists():
        logger.error(f"Sectors JSON file not found at {json_path}")
        return

    # Get crags by name for reference
    crags = {}
    crag_results = session.exec(select(Crag))
    for crag in crag_results:
        crags[crag.name.lower()] = crag.id

    if not crags:
        logger.info(
            "No crags found in database. Make sure crags are created first.")
        return

    # Import sectors from JSON
    try:
        with open(json_path, 'r') as f:
            sectors_data = json.load(f)
            sectors = []
            skipped = 0

            for item in sectors_data:
                crag_name = item['crag_name'].lower()
                if crag_name in crags:
                    sector = Sector(name=item['name'],
                                    display_name=item['display_name'],
                                    crag_id=crags[crag_name],
                                    description=item.get('description'))
                    sectors.append(sector)
                else:
                    skipped += 1

            if sectors:
                session.add_all(sectors)
                session.commit()
                logger.info(f"Imported {len(sectors)} sectors")
                if skipped > 0:
                    logger.info(
                        f"Skipped {skipped} sectors with unknown crags")
            else:
                logger.info("No valid sectors found in JSON file")
    except Exception as e:
        session.rollback()
        logger.error(f"Error importing sectors: {str(e)}")
        raise


def import_scoring_configuration(session: Session):
    """Import scoring configuration for competitions."""
    from database.models.scoring import (BasePoints, VolumeBonus,
                                         UniqueAscentBonus, TeamAscentBonus,
                                         MasterGradeBonus)

    # Base Points
    base_points_json = Path('data/initial/base_points.json')
    if not base_points_json.exists():
        logger.error(f"Base points JSON file not found at {base_points_json}")
        return

    # Import base points if they don't exist yet
    existing_base_points = session.exec(select(BasePoints)).first()
    if not existing_base_points:
        try:
            with open(base_points_json, 'r') as f:
                base_points_data = json.load(f)
                base_points = []

                for item in base_points_data:
                    bp = BasePoints(grade=item['grade'],
                                    points=int(item['points']),
                                    increment_factor=float(
                                        item['increment_factor']))
                    base_points.append(bp)

                if base_points:
                    session.add_all(base_points)
                    session.commit()
                    logger.info(
                        f"Imported {len(base_points)} base points configs")
        except Exception as e:
            session.rollback()
            logger.error(f"Error importing base points: {str(e)}")
            raise
    else:
        logger.info("Base points already exist in database, skipping import")

    # Volume Bonus
    volume_bonus_json = Path('data/initial/volume_bonus.json')
    if not volume_bonus_json.exists():
        logger.error(
            f"Volume bonus JSON file not found at {volume_bonus_json}")
        return

    # Import volume bonus if it doesn't exist yet
    existing_volume_bonus = session.exec(select(VolumeBonus)).first()
    if not existing_volume_bonus:
        try:
            with open(volume_bonus_json, 'r') as f:
                volume_bonus_data = json.load(f)
                volume_bonuses = []

                for item in volume_bonus_data:
                    vb = VolumeBonus(
                        bonus_increment=int(item['bonus_increment']),
                        points_per_increment=int(item['points_per_increment']))
                    volume_bonuses.append(vb)

                if volume_bonuses:
                    session.add_all(volume_bonuses)
                    session.commit()
                    logger.info(
                        f"Imported {len(volume_bonuses)} volume bonus configs")
        except Exception as e:
            session.rollback()
            logger.error(f"Error importing volume bonus: {str(e)}")
            raise
    else:
        logger.info("Volume bonus already exists in database, skipping import")

    # Unique Ascent Bonus
    unique_bonus_json = Path('data/initial/unique_ascent_bonus.json')
    if not unique_bonus_json.exists():
        logger.error(
            f"Unique ascent bonus JSON file not found at {unique_bonus_json}")
        return

    # Import unique ascent bonus if it doesn't exist yet
    existing_unique_bonus = session.exec(select(UniqueAscentBonus)).first()
    if not existing_unique_bonus:
        try:
            with open(unique_bonus_json, 'r') as f:
                unique_bonus_data = json.load(f)
                unique_bonuses = []

                for item in unique_bonus_data:
                    ub = UniqueAscentBonus(
                        bonus_factor=float(item['bonus_factor']))
                    unique_bonuses.append(ub)

                if unique_bonuses:
                    session.add_all(unique_bonuses)
                    session.commit()
                    logger.info(f"Imported {len(unique_bonuses)} "
                                f"unique ascent bonus configs")
        except Exception as e:
            session.rollback()
            logger.error(f"Error importing unique ascent bonus: {str(e)}")
            raise
    else:
        logger.info(
            "Unique ascent bonus already exists in database, skipping import")

    # Team Ascent Bonus
    team_bonus_json = Path('data/initial/team_ascent_bonus.json')
    if not team_bonus_json.exists():
        logger.error(
            f"Team ascent bonus JSON file not found at {team_bonus_json}")
        return

    # Import team ascent bonus if it doesn't exist yet
    existing_team_bonus = session.exec(select(TeamAscentBonus)).first()
    if not existing_team_bonus:
        try:
            with open(team_bonus_json, 'r') as f:
                team_bonus_data = json.load(f)
                team_bonuses = []

                for item in team_bonus_data:
                    tb = TeamAscentBonus(team_size=int(item['team_size']),
                                         bonus_factor=float(
                                             item['bonus_factor']))
                    team_bonuses.append(tb)

                if team_bonuses:
                    session.add_all(team_bonuses)
                    session.commit()
                    logger.info(f"Imported {len(team_bonuses)} "
                                f"team ascent bonus configs")
        except Exception as e:
            session.rollback()
            logger.error(f"Error importing team ascent bonus: {str(e)}")
            raise
    else:
        logger.info(
            "Team ascent bonus already exists in database, skipping import")

    # Master Grade Bonus
    master_bonus_json = Path('data/initial/master_grade_bonus.json')
    if not master_bonus_json.exists():
        logger.error(
            f"Master grade bonus JSON file not found at {master_bonus_json}")
        return

    # Import master grade bonus if it doesn't exist yet
    existing_master_bonus = session.exec(select(MasterGradeBonus)).first()
    if not existing_master_bonus:
        try:
            with open(master_bonus_json, 'r') as f:
                master_bonus_data = json.load(f)
                master_bonuses = []

                for item in master_bonus_data:
                    mb = MasterGradeBonus(
                        bonus_factor=float(item['bonus_factor']))
                    master_bonuses.append(mb)

                if master_bonuses:
                    session.add_all(master_bonuses)
                    session.commit()
                    logger.info(f"Imported {len(master_bonuses)} "
                                f"master grade bonus configs")
        except Exception as e:
            session.rollback()
            logger.error(f"Error importing master grade bonus: {str(e)}")
            raise
    else:
        logger.info(
            "Master grade bonus already exists in database, skipping import")


def initialize_crag_data(session: Session):
    """Initialize the database with all required data."""

    # Import crags first (top-level entities)
    import_crags(session)

    # Import sectors (depend on crags)
    import_sectors(session)

    # Import boulder-sector mappings (depend on sectors)
    import_boulder_sector_mappings(session)
    # Import scoring configuration
    import_scoring_configuration(session)
    logger.info("Database initialization complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize crag data in the database.")
    parser.add_argument("--skip-crags",
                        action="store_true",
                        help="Skip importing crag data")
    parser.add_argument("--skip-sectors",
                        action="store_true",
                        help="Skip importing sector data")
    parser.add_argument("--skip-mappings",
                        action="store_true",
                        help="Skip importing boulder-sector mappings")
    parser.add_argument("--skip-scoring",
                        action="store_true",
                        help="Skip importing scoring configuration")
    args = parser.parse_args()

    with get_db_session() as session:
        if not args.skip_crags:
            import_crags(session)
        if not args.skip_sectors:
            import_sectors(session)
        if not args.skip_mappings:
            import_boulder_sector_mappings(session)
        if not args.skip_scoring:
            import_scoring_configuration(session)

        logger.info("Data import complete")

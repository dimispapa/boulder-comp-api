#!/usr/bin/env python
"""
Script to update competition boulders in the database based on JSON file.
This script will check if boulders from the JSON file exist in the database
and add any missing ones.
"""
import json
import sys
from pathlib import Path
from sqlmodel import select
from uuid import UUID
import gc

from database.models.crags import Boulder, Sector
from database.models.competitions import CompetitionBoulder
from database.management.base import get_db_session
from utils.loggers import logger


def update_competition_boulders(competition_id: str):
    """
    Update competition boulders based on JSON file.

    Args:
        competition_id (str): The ID of the competition to update
    """
    logger.info(
        f"Updating competition boulders for competition {competition_id}")

    json_path = Path('data/initial/competition_boulders.json')
    if not json_path.exists():
        logger.error(
            f"Competition boulders JSON file not found at {json_path}")
        return

    try:
        # Parse the JSON file
        with open(json_path, 'r') as f:
            boulders_data = json.load(f)

        logger.info(f"Loaded {len(boulders_data)} boulders from JSON file")

        # Get database session
        with get_db_session() as session:
            # Validate competition ID
            try:
                comp_id = UUID(competition_id)
            except ValueError:
                logger.error(f"Invalid competition ID: {competition_id}")
                return

            # Get existing competition boulders
            existing_statement = select(CompetitionBoulder).where(
                CompetitionBoulder.competition_id == comp_id)
            existing_boulders = session.exec(existing_statement).all()
            existing_boulder_names = {
                b.boulder_name
                for b in existing_boulders
            }

            logger.info(
                f"Found {len(existing_boulders)} existing competition boulders"
            )

            # Process boulders from JSON
            new_boulders = []
            skipped_count = 0
            not_found_count = 0
            added_count = 0

            for item in boulders_data:
                boulder_name = item.get('boulder_name')
                sector_name = item.get('sector_name')

                if not boulder_name or not sector_name:
                    logger.warning(f"Skipping entry with missing data: {item}")
                    skipped_count += 1
                    continue

                # Skip if boulder already exists in competition
                if boulder_name in existing_boulder_names:
                    logger.debug(
                        f"Boulder '{boulder_name}' already in competition,"
                        " skipping")
                    skipped_count += 1
                    continue

                # Find the sector
                sector_statement = select(Sector).where(
                    Sector.name == sector_name)
                sector = session.exec(sector_statement).first()

                if not sector:
                    logger.warning(
                        f"Sector '{sector_name}' not found in database,"
                        " skipping")
                    not_found_count += 1
                    continue

                # Find the boulder in this sector
                boulder_statement = select(Boulder).where(
                    (Boulder.name == boulder_name)
                    & (Boulder.sector_id == sector.id))
                boulder = session.exec(boulder_statement).first()

                if not boulder:
                    logger.warning(
                        f"Boulder '{boulder_name}' not found in sector "
                        f"'{sector_name}', skipping")
                    not_found_count += 1
                    continue

                # Create new competition boulder
                comp_boulder = CompetitionBoulder(competition_id=comp_id,
                                                  boulder_id=boulder.id,
                                                  boulder_name=boulder_name,
                                                  sector_name=sector_name,
                                                  is_active=True)

                new_boulders.append(comp_boulder)
                added_count += 1

                # Collect garbage periodically to avoid memory issues
                if len(new_boulders) % 10 == 0:
                    gc.collect()

            # Add new boulders to database
            if new_boulders:
                session.add_all(new_boulders)
                session.commit()
                logger.info(f"Added {added_count} new competition boulders")
            else:
                logger.info("No new competition boulders to add")

            logger.info(f"Summary: {skipped_count} skipped, {not_found_count} "
                        f"not found, {added_count} added")

    except Exception as e:
        logger.error(f"Error updating competition boulders: {str(e)}",
                     exc_info=True)
        return


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_competition_boulders.py <competition_id>")
        sys.exit(1)

    competition_id = sys.argv[1]
    update_competition_boulders(competition_id)

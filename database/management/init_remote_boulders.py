"""
Script to import remote boulder data from JSON file.
"""
import json
import sys
from pathlib import Path
from sqlmodel import select
from uuid import UUID

# Add parent directory to path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from database.management.base import get_db  # noqa: E402
from database.models.crags import Boulder, Sector  # noqa: E402
from database.models.scoring import RemoteBoulderBonus  # noqa: E402
from database.models.competitions import Competition  # noqa: E402
from utils.loggers import logger  # noqa: E402


def import_remote_boulders(competition_id: str):
    """
    Import remote boulder data from JSON file.

    Args:
        competition_id: UUID string of the competition to assign
        remote boulders to
    """
    session = next(get_db())

    # Validate competition exists
    competition = session.get(Competition, UUID(competition_id))
    if not competition:
        logger.error(f"Competition {competition_id} not found")
        return

    # Load remote_boulders.json
    json_path = Path("data/initial/remote_boulders.json")
    if not json_path.exists():
        logger.error(f"Remote boulders file not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        remote_data = json.load(f)

    logger.info(f"Loaded {len(remote_data)} remote boulder entries from JSON")

    # Process each entry
    added_count = 0
    for entry in remote_data:
        # Find the boulder by name and sector
        boulder_name = entry['boulder_name']
        sector_name = entry['sector_name']

        # First get the sector
        statement = select(Sector).where(Sector.name == sector_name)
        sector = session.exec(statement).first()

        if sector:
            # Get the boulder in this sector
            statement = select(Boulder).where((Boulder.name == boulder_name) &
                                              (Boulder.sector_id == sector.id))
            boulder = session.exec(statement).first()

            if boulder:
                # Check if an entry already exists
                statement = select(RemoteBoulderBonus).where(
                    (RemoteBoulderBonus.boulder_id == boulder.id)
                    & (RemoteBoulderBonus.competition_id == UUID(
                        competition_id)))
                existing = session.exec(statement).first()

                if not existing:
                    # Create new remote boulder entry
                    remote = RemoteBoulderBonus(
                        competition_id=UUID(competition_id),
                        boulder_id=boulder.id,
                        bonus_factor=entry['remote_bonus'])
                    session.add(remote)
                    added_count += 1
                    logger.info(
                        f"Added remote boulder: {boulder_name} with bonus "
                        f"{entry['remote_bonus']}")
                else:
                    logger.info(
                        f"Remote boulder already exists for this competition: "
                        f"{boulder_name}")
            else:
                logger.warning(f"Boulder not found: {boulder_name} in sector"
                               f" {sector_name}")
        else:
            logger.warning(f"Sector not found: {sector_name}")

    session.commit()
    logger.info(
        f"Remote boulder import complete. Added {added_count} entries.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_remote_boulders.py <competition_id>")
        sys.exit(1)

    competition_id = sys.argv[1]
    import_remote_boulders(competition_id)

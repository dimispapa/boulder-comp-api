"""
Database initialization for default competition data.
"""
from sqlmodel import Session, select
import json
import random
from pathlib import Path
from uuid import UUID
from datetime import datetime, UTC
import pytz
from utils.loggers import logger
from database.models.enums import (EventStatus, CategoryType)
from database.models.competitions import (Competition, CompetitionCategory,
                                          CompetitionBoulder, CompVoucher)
from database.models.crags import Boulder
from database.crud.crags import get_crag_by_name
from database.models.scoring import (BasePoints, VolumeBonus,
                                     UniqueAscentBonus, TeamAscentBonus,
                                     MasterGradeBonus, RemoteBoulderBonus)

# Constants
DEFAULT_COMP_NAME = "spring_bouldering_festival_comp"
DEFAULT_COMP_DISPLAY_NAME = "Spring Bouldering Festival - Competition"
DEFAULT_CRAG_NAME = "inia-droushia"
DEFAULT_COMP_VENUE = "Inia-Droushia Bouldering Area"
DEFAULT_COMP_DESCRIPTION = "Join us for the annual Spring Bouldering " \
    "Festival at Inia & Droushia! " \
    "Compete in a team or solo and test your skills while having fun on " \
    "Cyprus's finest sandstone boulders."
DEFAULT_CLIMBATHON_DESCRIPTION = "🏃‍♂️ The ultimate team endurance " \
    "challenge! " \
    "Teams work together to climb as many boulders as possible " \
    "within the event timeframe. " \
    "Climbathon is divided into two grade subcategories: " \
    "6A+ and below (Only boulders graded 6A+ (V3) and lower are valid) " \
    "and 6B and above (Only boulders graded 6B (V4) " \
    "and higher are valid). "
DEFAULT_BOULDER_TITANS_DESCRIPTION = "🦍 A true test of individual " \
    "strength and skill! " \
    "Every participant in the Climbathon is automatically entered " \
    "into Boulder Titans. Your five hardest sends determine your ranking. " \
    "In case of a tie, your sixth, seventh, and so on hardest climbs " \
    "will be used to break it. " \
    "Solo participants without a team can also enter Boulder Titans!"

# Competition dates
local_tz = pytz.timezone('Europe/Nicosia')
DEFAULT_COMP_START_DATE = datetime(2025, 5, 17, 11, 0)
DEFAULT_COMP_END_DATE = datetime(2025, 5, 17, 19, 0)
# Make them timezone aware (in local timezone)
aware_start = local_tz.localize(DEFAULT_COMP_START_DATE)
aware_end = local_tz.localize(DEFAULT_COMP_END_DATE)
utc_start_date = aware_start.astimezone(UTC)
utc_end_date = aware_end.astimezone(UTC)


def import_default_competition(session: Session):
    """Import default competition data."""
    # Check if competitions already exist
    existing_count = session.exec(select(Competition)).first()
    if existing_count:
        logger.info("Competitions already exist in database, skipping import")
        return

    # Get the Inia-Droushia crag to associate with the competition
    crag = get_crag_by_name(session, DEFAULT_CRAG_NAME)
    if not crag:
        logger.error(f"Crag '{DEFAULT_CRAG_NAME}' not found in database. "
                     "Cannot create competition.")
        return

    # Create the default competition
    comp = Competition(name=DEFAULT_COMP_NAME,
                       display_name=DEFAULT_COMP_DISPLAY_NAME,
                       crag_id=crag.id,
                       start_date=utc_start_date,
                       end_date=utc_end_date,
                       status=EventStatus.upcoming,
                       description=DEFAULT_COMP_DESCRIPTION,
                       venue=DEFAULT_COMP_VENUE)

    session.add(comp)
    # Flush to get the competition ID
    session.flush()

    # Add categories for the competition
    climbathon_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.marathon,
        name="Climbathon",
        description=DEFAULT_CLIMBATHON_DESCRIPTION,
        display_order=1)

    boulder_titans_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.boulder_beasts,
        name="Boulder Titans",
        description=DEFAULT_BOULDER_TITANS_DESCRIPTION,
        display_order=2)

    session.add(climbathon_category)
    session.add(boulder_titans_category)

    # Commit to save the competition and categories
    session.commit()
    logger.info(f"Created default competition: {comp.display_name}")

    # Set up scoring configuration
    import_scoring_config(session, comp.id)

    # Import competition boulders
    import_competition_boulders(session, comp.id)

    logger.info("Default competition initialization complete")


def import_competition_boulders(session: Session, competition_id: UUID):
    """Import competition boulders from JSON file."""
    json_path = Path('data/initial/competition_boulders.json')
    if not json_path.exists():
        logger.error(
            f"Competition boulders JSON file not found at {json_path}")
        return

    # Check if competition boulders already exist for this competition
    existing_boulders = session.exec(
        select(CompetitionBoulder).where(
            CompetitionBoulder.competition_id == competition_id)).first()

    if existing_boulders:
        logger.info("Competition boulders already exist, skipping import")
        return

    # Import boulders from JSON
    try:
        with open(json_path, 'r') as f:
            boulders_data = json.load(f)

            # Create competition boulders directly from names
            competition_boulders = []

            for item in boulders_data:
                boulder_name = item.get('boulder_name')
                sector_name = item.get('sector_name')

                if not boulder_name or not sector_name:
                    logger.warning(f"Skipping entry with missing data: {item}")
                    continue

                # Find boulder ID from the name
                boulder_query = select(Boulder).where(
                    Boulder.name == boulder_name)
                boulder = session.exec(boulder_query).first()

                if not boulder:
                    logger.warning(
                        f"Boulder '{boulder_name}' not found in database, "
                        "skipping")
                    continue

                comp_boulder = CompetitionBoulder(
                    competition_id=competition_id,
                    boulder_id=boulder.id,
                    boulder_name=boulder_name,
                    sector_name=sector_name,
                    is_active=True)
                competition_boulders.append(comp_boulder)

            if competition_boulders:
                session.add_all(competition_boulders)
                session.commit()
                logger.info(f"Added {len(competition_boulders)} boulders to "
                            f"competition {competition_id}")
            else:
                logger.warning(
                    "No valid competition boulders found in JSON file")

    except Exception as e:
        session.rollback()
        logger.error(f"Error importing competition boulders: {str(e)}")


def import_scoring_config(session: Session, comp_id: str):
    """Import scoring configuration for the default competition."""
    # Get the competition
    comp = session.get(Competition, comp_id)
    if not comp:
        logger.error(
            "Default competition not found. Cannot create scoring config.")
        return

    # Check if scoring config already exists for this competition
    existing_config = session.exec(
        select(BasePoints).where(
            BasePoints.competition_id == comp.id)).first()
    if existing_config:
        logger.info(
            "Scoring configuration already exists for this competition,"
            " skipping import")
        return

    # Get global/default base points to copy values
    global_base_points = session.exec(
        select(BasePoints).where(BasePoints.competition_id.is_(None))).all()

    # Create competition-specific base points
    comp_base_points = []
    for bp in global_base_points:
        comp_bp = BasePoints(competition_id=comp.id,
                             grade=bp.grade,
                             points=bp.points,
                             increment_factor=bp.increment_factor)
        comp_base_points.append(comp_bp)

    if comp_base_points:
        session.add_all(comp_base_points)
        session.commit()
        logger.info(f"Created {len(comp_base_points)} base points configs for "
                    f"competition {comp.name}")

    # Get global/default volume bonus
    global_volume_bonus = session.exec(
        select(VolumeBonus).where(VolumeBonus.competition_id.is_(None))).all()

    # Create competition-specific volume bonus
    for vb in global_volume_bonus:
        comp_vb = VolumeBonus(competition_id=comp.id,
                              bonus_increment=vb.bonus_increment,
                              points_per_increment=vb.points_per_increment)
        session.add(comp_vb)

    # Get global/default unique ascent bonus
    global_unique_bonus = session.exec(
        select(UniqueAscentBonus).where(
            UniqueAscentBonus.competition_id.is_(None))).all()

    # Create competition-specific unique ascent bonus
    for ub in global_unique_bonus:
        comp_ub = UniqueAscentBonus(competition_id=comp.id,
                                    bonus_factor=ub.bonus_factor)
        session.add(comp_ub)

    # Get global team ascent bonus
    global_team_bonus = session.exec(
        select(TeamAscentBonus).where(
            TeamAscentBonus.competition_id.is_(None))).all()

    # Create competition-specific team ascent bonus
    comp_team_bonuses = []
    for tb in global_team_bonus:
        comp_tb = TeamAscentBonus(competition_id=comp.id,
                                  team_size=tb.team_size,
                                  bonus_factor=tb.bonus_factor)
        comp_team_bonuses.append(comp_tb)

    if comp_team_bonuses:
        session.add_all(comp_team_bonuses)
        session.commit()
        logger.info(
            f"Created {len(comp_team_bonuses)} team ascent bonus configs for "
            f"competition {comp.name}")

    # Get global master grade bonus
    global_master_bonus = session.exec(
        select(MasterGradeBonus).where(
            MasterGradeBonus.competition_id.is_(None))).all()

    # Create competition-specific master grade bonus
    for mb in global_master_bonus:
        comp_mb = MasterGradeBonus(competition_id=comp.id,
                                   bonus_factor=mb.bonus_factor)
        session.add(comp_mb)

    # Get global remote boulder bonus
    global_remote_bonus = session.exec(
        select(RemoteBoulderBonus).where(
            RemoteBoulderBonus.competition_id.is_(None))).all()

    # Create competition-specific remote boulder bonus
    for rb in global_remote_bonus:
        comp_rb = RemoteBoulderBonus(competition_id=comp.id,
                                     bonus_factor=rb.bonus_factor)
        session.add(comp_rb)

    session.commit()
    logger.info(
        f"Created all scoring configurations for competition {comp.name}")


def import_comp_vouchers(session: Session, competition_id: UUID):
    """Import competition vouchers with hardcoded member data."""
    # Check if vouchers already exist for this competition
    existing_vouchers = session.exec(
        select(CompVoucher).where(
            CompVoucher.competition_id == competition_id)).first()

    if existing_vouchers:
        logger.info("Competition vouchers already exist, skipping import")
        return

    try:
        # Generate a set of unique 6-digit codes
        used_codes = set()
        vouchers = []

        # Hardcoded member data from member_list.csv
        member_data = [{
            "Name": "Marios",
            "Surname": "Apseros",
            "Email": "mariosapseros@icloud.com",
            "Mobile Phone": "96770673"
        }, {
            "Name": "Demetris",
            "Surname": "Papakyriacou",
            "Email": "dpapakyriacou14@gmail.com",
            "Mobile Phone": "99756356"
        }, {
            "Name": "Thomas",
            "Surname": "Georgiou",
            "Email": "thomascgeorgiou@gmail.com",
            "Mobile Phone": "94046600"
        }, {
            "Name": "Anna",
            "Surname": "Michael",
            "Email": "michaelanna777@gmail.com",
            "Mobile Phone": "99295550"
        }, {
            "Name": "Tasos",
            "Surname": "Michael",
            "Email": "tasgsx@hotmail.com",
            "Mobile Phone": "99462808"
        }, {
            "Name": "Andreas",
            "Surname": "Parparinos",
            "Email": "and_par@hotmail.com",
            "Mobile Phone": "99472232"
        }, {
            "Name": "Andreas",
            "Surname": "Rossidis",
            "Email": "antreasrossidess@gmail.com",
            "Mobile Phone": "99270137"
        }, {
            "Name": "Kimberley",
            "Surname": "Reid",
            "Email": "kimberley.reid@hotmail.co.uk",
            "Mobile Phone": "94044655"
        }, {
            "Name": "Maria",
            "Surname": "Antronicou",
            "Email": "",
            "Mobile Phone": ""
        }, {
            "Name": "Panayiotis",
            "Surname": "Loizou",
            "Email": "",
            "Mobile Phone": ""
        }, {
            "Name": "Charalambos",
            "Surname": "Theodorou",
            "Email": "",
            "Mobile Phone": ""
        }, {
            "Name": "Elli",
            "Surname": "Kadi",
            "Email": "",
            "Mobile Phone": "99399756"
        }, {
            "Name": "Panayiotis",
            "Surname": "Panayiotou",
            "Email": "",
            "Mobile Phone": "97762472"
        }, {
            "Name": "Grigoris",
            "Surname": "Kyriakou",
            "Email": "",
            "Mobile Phone": "99239525"
        }, {
            "Name": "Nefeli",
            "Surname": "Tsingi",
            "Email": "",
            "Mobile Phone": "97425372"
        }, {
            "Name": "Chrystalla",
            "Surname": "Antoniou",
            "Email": "",
            "Mobile Phone": "99035045"
        }, {
            "Name": "Eleftheria",
            "Surname": "Contopoullou",
            "Email": "",
            "Mobile Phone": "99942728"
        }, {
            "Name": "Roy",
            "Surname": "Shartouni",
            "Email": "",
            "Mobile Phone": "97640624"
        }, {
            "Name": "Demetris",
            "Surname": "Demetriou",
            "Email": "",
            "Mobile Phone": "99979041"
        }, {
            "Name": "Stavri",
            "Surname": "Mama",
            "Email": "",
            "Mobile Phone": "96600765"
        }, {
            "Name": "Anna",
            "Surname": "Fotiadou",
            "Email": "",
            "Mobile Phone": "99684549"
        }]

        for member in member_data:
            # Generate a unique 6-digit code
            while True:
                code = random.randint(100000, 999999)
                if code not in used_codes:
                    used_codes.add(code)
                    break

            # Combine first and last name
            full_name = f"{member['Name'].strip()} {member['Surname'].strip()}"

            # Create voucher with available data
            voucher = CompVoucher(
                full_name=full_name,
                email=member['Email'].strip() if member['Email'] else None,
                phone=member['Mobile Phone'].strip()
                if member['Mobile Phone'] else None,
                code=code,
                competition_id=competition_id)
            vouchers.append(voucher)

        if vouchers:
            session.add_all(vouchers)
            session.commit()
            logger.info(f"Added {len(vouchers)} vouchers for competition "
                        f"{competition_id}")
        else:
            logger.warning(
                "No valid voucher data found in hardcoded member list")

    except Exception as e:
        session.rollback()
        logger.error(f"Error importing competition vouchers: {str(e)}")


def initialize_default_competition(session: Session):
    """Initialize the database with default competition data."""
    import_default_competition(session)

    # Get the default competition ID to use for vouchers
    default_comp = session.exec(
        select(Competition).where(
            Competition.name == DEFAULT_COMP_NAME)).first()

    if default_comp:
        # Import vouchers for the default competition
        import_comp_vouchers(session, default_comp.id)

    logger.info("Default competition data initialization complete")

"""
Database initialization for a test competition with specific team structures
to test volume bonus configurations.

This script creates:
- 3 teams (Team A: 4 participants, Team B: 3 participants,
Team C: 2 participants)
- Each team completes the same 50 boulder problems
- Every participant in each team sends the same 50 problems
"""
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import bcrypt
import os
from sqlalchemy import text
from sqlmodel import Session, select

from utils.loggers import logger
from database.models.enums import (EventStatus, CategoryType,
                                   MarathonSubCategory, UserRole)
from database.models.competitions import (Competition, CompetitionCategory,
                                          Team, Participant, Ascent)
from database.models.crags import Route
from database.models.accounts import User
from database.crud.crags import get_crag_by_name
from database.models.scoring import (BasePoints, VolumeBonus,
                                     UniqueAscentBonus, TeamAscentBonus,
                                     MasterGradeBonus)

# Constants
UTC = ZoneInfo("UTC")
TEST_COMP_NAME = "test_scoring_comp"
TEST_COMP_DISPLAY_NAME = "Test Scoring Competition"
TEST_COMP_START_DATE = datetime.now().date()
TEST_COMP_END_DATE = datetime.now().date()
DEFAULT_CRAG_NAME = "inia-droushia"
NUM_PROBLEMS = 50
MAX_TEAM_SIZE = int(os.environ.get("MAX_TEAM_SIZE", 4))

TEAM_CONFIGS = [{
    "name": "Team A",
    "size": 4,
    "subcategory": MarathonSubCategory.gte_6B
}, {
    "name": "Team B",
    "size": 3,
    "subcategory": MarathonSubCategory.gte_6B
}, {
    "name": "Team C",
    "size": 2,
    "subcategory": MarathonSubCategory.gte_6B
}]


def create_test_competition(session: Session):
    """Create a test competition or use existing one."""
    # Check if competition already exists
    existing_comp = session.exec(
        select(Competition).where(Competition.name == TEST_COMP_NAME)).first()
    if existing_comp:
        logger.info(
            f"Competition {TEST_COMP_NAME} already exists, using existing one")
        return existing_comp

    # Get an existing crag to associate with the competition
    crag = get_crag_by_name(session, DEFAULT_CRAG_NAME)
    if not crag:
        logger.error(f"Crag '{DEFAULT_CRAG_NAME}' not found in database. "
                     "Please create it first.")
        return None

    # Create the test competition
    comp = Competition(
        name=TEST_COMP_NAME,
        display_name=TEST_COMP_DISPLAY_NAME,
        crag_id=crag.id,
        start_date=TEST_COMP_START_DATE,
        end_date=TEST_COMP_END_DATE,
        status=EventStatus.ongoing,
        description="Test competition for scoring configuration testing",
        venue="Test Venue")

    session.add(comp)
    session.flush()

    # Add marathon category for the competition
    marathon_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.marathon,
        name="Test Marathon",
        description="Test category for scoring",
        display_order=1)

    session.add(marathon_category)
    session.commit()

    logger.info(f"Created test competition: {comp.display_name}")
    return comp


def create_test_users(session: Session, num_users_needed: int):
    """Create test users."""
    # Get existing users
    existing_users = session.exec(select(User)).all()

    if len(existing_users) >= num_users_needed:
        logger.info(f"Found {len(existing_users)} existing users, using them")
        return existing_users[:num_users_needed]

    # Create additional users if needed
    new_users = []
    for i in range(len(existing_users), num_users_needed):
        new_user = User(first_name=f"TestUser{i}",
                        last_name=f"Scoring{i}",
                        email=f"test_user_{i}@example.com",
                        hashed_password=bcrypt.hashpw(
                            "password123".encode(), bcrypt.gensalt()).decode(),
                        role=UserRole.user,
                        confirmed_at=datetime.now())
        new_users.append(new_user)

    session.add_all(new_users)
    session.commit()

    logger.info(f"Created {len(new_users)} new test users")

    # Return all users needed
    return existing_users + new_users


def create_test_teams(session: Session, comp_id: int, users: list):
    """Create test teams with specific sizes."""
    teams = []
    user_index = 0

    # First check if teams already exist for this competition
    existing_teams = {}
    for team_config in TEAM_CONFIGS:
        existing_team = session.exec(
            select(Team).where(Team.competition_id == comp_id,
                               Team.name == team_config["name"])).first()

        if existing_team:
            logger.info(f"Found existing team: {team_config['name']}")
            teams.append(existing_team)
            existing_teams[team_config["name"]] = existing_team

    # If we found all teams, return them
    if len(teams) == len(TEAM_CONFIGS):
        logger.info(f"Using {len(teams)} existing teams")
        return teams

    # If not all teams exist, we need to clear the found teams and create all
    # from scratch to ensure consistency with participants
    if teams:
        logger.info(
            "Found some teams but not all, creating all teams from scratch")
        teams = []

    # Create teams
    for team_config in TEAM_CONFIGS:
        # Skip if this team already exists
        if team_config["name"] in existing_teams:
            continue

        team = Team(competition_id=comp_id,
                    name=team_config["name"],
                    captain_id=users[user_index].id,
                    team_code=f"TEST{team_config['name'][-1]}",
                    marathon_subcategory=team_config["subcategory"],
                    spots=MAX_TEAM_SIZE - team_config["size"],
                    is_full=(team_config["size"] >= MAX_TEAM_SIZE))
        session.add(team)
        session.flush()
        teams.append(team)

        # Create participants for this team
        participants = []
        for i in range(team_config["size"]):
            if user_index < len(users):
                participant = Participant(competition_id=comp_id,
                                          user_id=users[user_index].id,
                                          team_id=team.id,
                                          signed_waiver=True)
                participants.append(participant)
                user_index += 1

        session.add_all(participants)

    session.commit()
    logger.info(f"Created/reused {len(teams)} teams with specific sizes")
    return teams


def get_existing_routes(session: Session, num_routes: int):
    """Get existing routes from database."""
    # Get routes from existing boulders
    routes = session.exec(select(Route).limit(num_routes)).all()

    if len(routes) < num_routes:
        logger.error(
            f"Not enough routes found in the database. Found {len(routes)}, "
            f"needed {num_routes}")
        return routes

    return routes[:num_routes]


def create_test_ascents(session: Session, comp_id: int, routes: list):
    """Create ascents where all participants send the same problems."""
    # Check if ascents already exist for this competition
    try:
        existing_ascents = session.exec(
            select(Ascent.id, Ascent.competition_id, Ascent.participant_id,
                   Ascent.route_id, Ascent.team_id, Ascent.status,
                   Ascent.inserted_at, Ascent.updated_at).where(
                       Ascent.competition_id == comp_id)).all()

        if existing_ascents:
            logger.info(
                f"Found {len(existing_ascents)} existing ascents for this "
                f"competition")

            # Count how many unique routes and participants are covered
            existing_route_ids = set(a.route_id for a in existing_ascents)
            existing_participant_ids = set(a.participant_id
                                           for a in existing_ascents)

            logger.info(
                f"Existing ascents cover {len(existing_route_ids)} routes and "
                f"{len(existing_participant_ids)} participants")

            # If we already have a good amount of ascents, we can reuse them
            if len(existing_route_ids) >= len(routes) * 0.8:  # 80% coverage
                logger.info("Sufficient existing ascents found, using them")
                return existing_ascents
    except Exception as e:
        logger.error(f"Error querying existing ascents: {e}")
        existing_ascents = []

    # Get all participants for this competition
    participants = session.exec(
        select(Participant).where(
            Participant.competition_id == comp_id)).all()

    if not participants:
        logger.error("No participants found. Cannot create ascents.")
        return []

    logger.info(
        f"Found {len(participants)} participants and {len(routes)} routes")

    # Track which ascents we need to create
    existing_ascent_keys = set()

    # Build a set of existing (participant_id, route_id) combinations
    if existing_ascents:
        for ascent in existing_ascents:
            existing_ascent_keys.add((ascent.participant_id, ascent.route_id))

    # For each participant, create ascents for each route if they don't already
    # exist
    for participant in participants:
        for route in routes:
            # Only create the ascent if it doesn't already exist
            if (participant.id, route.id) not in existing_ascent_keys:
                # Use explicit SQL insert to avoid updated_at field issues
                session.execute(
                    text("""
                    INSERT INTO ascents
                    (id, competition_id, participant_id, route_id, team_id,
                    status, inserted_at, updated_at)
                    VALUES
                    (:id, :competition_id, :participant_id, :route_id,
                    :team_id, :status, :inserted_at, :updated_at)
                    """),
                    {
                        "id": uuid.uuid4(),
                        "competition_id": comp_id,
                        "participant_id": participant.id,
                        "route_id": route.id,
                        "team_id": participant.team_id,
                        "status": True,  # All ascents are approved
                        "inserted_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC)
                    })

    try:
        session.commit()
        logger.info("Created new ascents")
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating ascents: {e}")
        return []

    # Get all ascents for this competition after creation
    try:
        all_ascents = session.exec(
            select(Ascent.id, Ascent.competition_id, Ascent.participant_id,
                   Ascent.route_id, Ascent.team_id, Ascent.status,
                   Ascent.inserted_at, Ascent.updated_at).where(
                       Ascent.competition_id == comp_id)).all()

        logger.info(f"Total ascents: {len(all_ascents)}")
        return all_ascents
    except Exception as e:
        logger.error(f"Error retrieving created ascents: {e}")
        return []


def create_test_scoring_config(session: Session, comp_id: uuid.UUID):
    """
    Create scoring configuration for the test competition.

    Copies the global default configurations (with null competition_id)
    to competition-specific entries.

    Args:
        session: Database session
        comp_id: Competition ID to associate with the scoring config
    """
    logger.info(
        f"Creating scoring configuration for test competition {comp_id}")

    # Check if scoring config already exists for this competition
    existing_config = session.exec(
        select(BasePoints).where(
            BasePoints.competition_id == comp_id)).first()

    if existing_config:
        logger.info(
            "Scoring configuration already exists for this competition, "
            "skipping creation")
        return

    # 1. Copy BasePoints
    global_base_points = session.exec(
        select(BasePoints).where(BasePoints.competition_id.is_(None))).all()

    comp_base_points = []
    for bp in global_base_points:
        comp_bp = BasePoints(competition_id=comp_id,
                             grade=bp.grade,
                             points=bp.points,
                             increment_factor=bp.increment_factor)
        comp_base_points.append(comp_bp)

    if comp_base_points:
        session.add_all(comp_base_points)
        session.commit()
        logger.info(f"Created {len(comp_base_points)} base points configs for "
                    f"competition {comp_id}")

    # 2. Copy VolumeBonus
    global_volume_bonus = session.exec(
        select(VolumeBonus).where(VolumeBonus.competition_id.is_(None))).all()

    for vb in global_volume_bonus:
        comp_vb = VolumeBonus(competition_id=comp_id,
                              bonus_increment=vb.bonus_increment,
                              points_per_increment=vb.points_per_increment)
        session.add(comp_vb)

    if global_volume_bonus:
        session.commit()
        logger.info(f"Created volume bonus config for competition {comp_id}")

    # 3. Copy UniqueAscentBonus
    global_unique_bonus = session.exec(
        select(UniqueAscentBonus).where(
            UniqueAscentBonus.competition_id.is_(None))).all()

    for ub in global_unique_bonus:
        comp_ub = UniqueAscentBonus(competition_id=comp_id,
                                    bonus_factor=ub.bonus_factor)
        session.add(comp_ub)

    if global_unique_bonus:
        session.commit()
        logger.info(
            f"Created unique ascent bonus config for competition {comp_id}")

    # 4. Copy TeamAscentBonus
    global_team_bonus = session.exec(
        select(TeamAscentBonus).where(
            TeamAscentBonus.competition_id.is_(None))).all()

    for tb in global_team_bonus:
        comp_tb = TeamAscentBonus(competition_id=comp_id,
                                  team_size=tb.team_size,
                                  bonus_factor=tb.bonus_factor)
        session.add(comp_tb)

    if global_team_bonus:
        session.commit()
        logger.info(
            f"Created team ascent bonus configs for competition {comp_id}")

    # 5. Copy MasterGradeBonus
    global_master_bonus = session.exec(
        select(MasterGradeBonus).where(
            MasterGradeBonus.competition_id.is_(None))).all()

    for mb in global_master_bonus:
        comp_mb = MasterGradeBonus(competition_id=comp_id,
                                   bonus_factor=mb.bonus_factor)
        session.add(comp_mb)

    if global_master_bonus:
        session.commit()
        logger.info(
            f"Created master grade bonus config for competition {comp_id}")

    logger.info(
        f"Complete scoring configuration created for competition {comp_id}")


def initialize_test_scoring_data(session: Session):
    """Initialize test competition with specific team sizes
       and ascents for scoring tests."""
    logger.info("Starting test scoring data initialization...")

    # Create a test competition or use existing one
    comp = create_test_competition(session)
    if not comp:
        logger.error("Failed to get or create competition. Exiting.")
        return

    # Create scoring configuration for the test competition
    create_test_scoring_config(session, comp.id)

    # Calculate total number of users needed
    total_users_needed = sum(tc["size"] for tc in TEAM_CONFIGS)

    # Get or create users for the competition
    users = create_test_users(session, total_users_needed)

    # Create teams for the competition
    teams = create_test_teams(session, comp.id, users)

    # Get existing routes for the competition
    routes = get_existing_routes(session, NUM_PROBLEMS)
    if not routes:
        logger.error("No routes found. Cannot create ascents.")
        return

    # Create ascents where all participants send the same problems
    create_test_ascents(session, comp.id, routes)

    logger.info(f"Test scoring competition '{comp.name}' initialized with:")
    logger.info(f"- {len(teams)} teams: {', '.join([t.name for t in teams])}")
    logger.info(f"- {NUM_PROBLEMS} boulders, each with 1 route")
    logger.info("- Ascents for all participants on all routes")
    logger.info("- Complete scoring configuration")


if __name__ == "__main__":
    from database.management.base import get_db

    session = next(get_db())
    logger.info("Starting test scoring data initialization...")
    initialize_test_scoring_data(session)
    logger.info("Script execution completed.")

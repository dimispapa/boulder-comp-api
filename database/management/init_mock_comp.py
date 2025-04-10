"""
Database initialization for mock competition data.
"""
from datetime import datetime, timedelta
from sqlmodel import Session, select
import bcrypt
import os

from utils.loggers import logger
from database.models.competitions import (Competition, CompetitionCategory,
                                          Team, Participant, Ascent,
                                          CompetitionStatus, CategoryType,
                                          CompVoucher)
from database.models.crags import Crag, Route
from database.models.accounts import User, UserRole


# Debug function to verify participant is_solo status
def debug_participants_is_solo(session: Session, comp_id, label=""):
    """Debug function to log the is_solo status of all participants."""
    participants = session.exec(
        select(Participant).where(
            Participant.competition_id == comp_id)).all()

    solo_count = 0
    team_count = 0

    logger.info(f"--- PARTICIPANT STATUS CHECK [{label}] ---")
    for p in participants:
        status = "SOLO" if p.is_solo else "TEAM"
        has_team = "with team" if p.team_id else "no team"
        solo_count += 1 if p.is_solo else 0
        team_count += 1 if not p.is_solo else 0

        # Get user details if possible
        user = None
        try:
            user = session.exec(
                select(User).where(User.id == p.user_id)).first()
            name = (f"{user.first_name} {user.last_name}"
                    if user else f"User {p.user_id}")
        except Exception:
            name = f"User {p.user_id}"

        logger.info(f"Participant {p.id} ({name}): {status}, {has_team}")

    logger.info(f"Summary: {solo_count} solo participants, "
                f"{team_count} team participants")
    logger.info("-----------------------------------")


# Constants
MOCK_COMP_NAME = "mock_comp_2025"
MOCK_COMP_DISPLAY_NAME = "Mock Comp 2025"
MOCK_COMP_START_DATE = datetime.now().date() - timedelta(days=7)
MOCK_COMP_END_DATE = datetime.now().date() + timedelta(days=7)
MAX_ROUTE_LIMIT = 200
MIN_ROUTE_LIMIT = 50
NO_OF_BEGINNER_ROUTES = 100
NO_OF_INTERMEDIATE_ROUTES = 70
NO_OF_ADVANCED_ROUTES = 30
MIN_ASCENTS_PER_CLIMBER = 7
MAX_ASCENTS_PER_CLIMBER = 50
MAX_TEAM_SIZE = int(os.environ.get("MAX_TEAM_SIZE", 4))


def update_team_status(session: Session, team_id):
    """Update team spots and is_full status based on participant count.

    As participants join a team, available spots decrease.
    When a team reaches MAX_TEAM_SIZE participants, it's marked as full.
    """
    # Get current participant count for the team
    team_size_query = select(Participant).where(Participant.team_id == team_id)
    current_team_size = len(session.exec(team_size_query).all())

    # Get the team
    team_query = select(Team).where(Team.id == team_id)
    team = session.exec(team_query).first()

    if team:
        # Calculate remaining spots (MAX_TEAM_SIZE minus current participants)
        remaining_spots = max(0, MAX_TEAM_SIZE - current_team_size)
        team.spots = remaining_spots

        # Update is_full status
        team.is_full = (current_team_size >= MAX_TEAM_SIZE)

        session.add(team)
        logger.info(f"Updated team {team.name}: spots={team.spots},"
                    f" is_full={team.is_full}")


def import_mock_competitions(session: Session):
    """Import mock competition data."""
    # Check if competitions already exist
    existing_count = session.exec(select(Competition)).first()
    if existing_count:
        logger.info("Competitions already exist in database, skipping import")
        return

    # Get a crag to associate with the competition
    crag = session.exec(select(Crag).limit(1)).first()
    if not crag:
        logger.error("No crags found in database. Cannot create competitions.")
        return

    # Create a mock competition
    comp = Competition(
        name=MOCK_COMP_NAME,
        display_name=MOCK_COMP_DISPLAY_NAME,
        crag_id=crag.id,
        start_date=MOCK_COMP_START_DATE,
        end_date=MOCK_COMP_END_DATE,
        status=CompetitionStatus.ongoing,
        description="An exciting bouldering competition at our favorite crag!",
        venue="Outdoor Bouldering Area")

    session.add(comp)
    # Flush to get the competition ID
    session.flush()

    # Add categories for the competition
    marathon_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.marathon,
        name="Marathon",
        description="Team-based endurance climbing competition",
        display_order=1)

    boulder_beasts_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.boulder_beasts,
        name="Boulder Beasts",
        description="Individual bouldering category awarding top "
        "5 hard ascents",
        display_order=2)

    session.add(marathon_category)
    session.add(boulder_beasts_category)

    # Commit to save the competition and categories
    session.commit()
    logger.info(f"Created mock competition: {comp.display_name}")


def import_mock_teams(session: Session):
    """Import mock team data with captains assigned."""
    # Check if teams already exist
    existing_count = session.exec(select(Team)).first()
    if existing_count:
        logger.info("Teams already exist in database, skipping import")
        return

    # Get the competition
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if not comp:
        logger.error("Mock competition not found. Cannot create teams.")
        return

    # Get captain participants
    captain_emails = {
        "Rock Stars": "john.smith@example.com",
        "Boulderers": "sarah.d@example.com",
        "Flash Force": "robert.t@example.com",
        "Grip Masters": "thomas.w@example.com",
        "The Climbers": "jessica.l@example.com",
        "Ramblers": "lucas.p@example.com"
    }

    # Get captains' user IDs directly (not participant IDs)
    captains = {}
    for team_name, captain_email in captain_emails.items():
        # Get user ID for the captain
        user = session.exec(
            select(User).where(User.email == captain_email)).first()
        if user:
            captains[team_name] = user.id

    # Create teams with captains
    teams = []
    for team_name, captain_id in captains.items():
        # Generate a unique team code
        team_code = f"TEAM{len(teams) + 1:03d}"

        team = Team(competition_id=comp.id,
                    name=team_name,
                    captain_id=captain_id,
                    team_code=team_code
                    # Using default spots=3 from the model
                    )
        teams.append(team)

    session.add_all(teams)
    session.commit()
    logger.info(f"Created {len(teams)} teams with captains")

    # Now update the participants with their team IDs
    teams_by_name = {}
    for team in session.exec(select(Team)):
        teams_by_name[team.name] = team.id

    # Get participants for the captains
    for team_name, captain_email in captain_emails.items():
        if team_name in teams_by_name:
            # Get the user id
            user = session.exec(
                select(User).where(User.email == captain_email)).first()
            if user:
                # Get the participant record for this user
                participant = session.exec(
                    select(Participant).where(
                        Participant.user_id == user.id)).first()
                if participant:
                    participant.team_id = teams_by_name[team_name]
                    session.add(participant)

    session.commit()
    logger.info("Updated captain participants with their team IDs")


def import_mock_users(session: Session):
    """Import mock user data."""
    # Check if users already exist
    existing_count = session.exec(select(User)).first()
    if existing_count:
        logger.info("Users already exist in database, skipping import")
        return

    # Create mock users
    users = [
        # Regular users (linked to participants later)
        User(first_name="John",
             last_name="Smith",
             email="john.smith@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Emily",
             last_name="Johnson",
             email="emily.j@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Michael",
             last_name="Brown",
             email="michael.b@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Sarah",
             last_name="Davis",
             email="sarah.d@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="David",
             last_name="Wilson",
             email="david.w@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user),
        User(first_name="Jessica",
             last_name="Lee",
             email="jessica.l@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Robert",
             last_name="Taylor",
             email="robert.t@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Jennifer",
             last_name="Garcia",
             email="jennifer.g@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Daniel",
             last_name="Martinez",
             email="daniel.m@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user),
        User(first_name="Thomas",
             last_name="Wright",
             email="thomas.w@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Rebecca",
             last_name="Chen",
             email="rebecca.c@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Lucas",
             last_name="Park",
             email="lucas.p@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user),
        User(first_name="Jane",
             last_name="Doe",
             email="jane.doe@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Alex",
             last_name="Turner",
             email="alex.t@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user),
        User(first_name="Sarah",
             last_name="Connor",
             email="sarah.c@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        # New users for solo participants
        User(first_name="Chris",
             last_name="Evans",
             email="chris.e@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Maria",
             last_name="Rodriguez",
             email="maria.r@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        User(first_name="Kevin",
             last_name="Liu",
             email="kevin.l@example.com",
             hashed_password=bcrypt.hashpw("password123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.user,
             confirmed_at=datetime.now()),
        # Admin user
        User(first_name="Admin",
             last_name="User",
             email="admin@example.com",
             hashed_password=bcrypt.hashpw("admin123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.admin,
             confirmed_at=datetime.now()),
        # Moderator user
        User(first_name="Mod",
             last_name="User",
             email="moderator@example.com",
             hashed_password=bcrypt.hashpw("mod123".encode(),
                                           bcrypt.gensalt()).decode(),
             role=UserRole.moderator,
             confirmed_at=datetime.now())
    ]

    session.add_all(users)
    session.commit()
    logger.info(f"Created {len(users)} mock users")

    return {user.email: user.id for user in users}


def import_mock_comp_vouchers(session: Session):
    """Import mock competition vouchers."""
    # Check if vouchers already exist
    existing_count = session.exec(select(CompVoucher)).first()
    if existing_count:
        logger.info(
            "Competition vouchers already exist in database, skipping import")
        return

    # Get the competition
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if not comp:
        logger.error("Mock competition not found. Cannot create vouchers.")
        return

    # Create mock vouchers
    voucher_data = [{
        "email": "john.smith@example.com",
        "code": 1001
    }, {
        "email": "emily.j@example.com",
        "code": 1002
    }, {
        "email": "michael.b@example.com",
        "code": 1003
    }, {
        "email": "sarah.d@example.com",
        "code": 2001
    }, {
        "email": "jessica.l@example.com",
        "code": 2003
    }, {
        "email": "robert.t@example.com",
        "code": 3001
    }, {
        "email": "jennifer.g@example.com",
        "code": 3002
    }, {
        "email": "thomas.w@example.com",
        "code": 4001
    }, {
        "email": "rebecca.c@example.com",
        "code": 4002
    }, {
        "email": "jane.doe@example.com",
        "code": 5001
    }, {
        "email": "sarah.c@example.com",
        "code": 5003
    }]

    # Get user IDs
    users = {}
    for user in session.exec(select(User)):
        users[user.email] = user.id

    # Get participants by user_id to associate vouchers with participants
    participants = {}
    for participant in session.exec(select(Participant)):
        participants[participant.user_id] = participant.id

    vouchers = []
    for data in voucher_data:
        # Find the participant via the user's email and ID
        participant_id = None
        if data["email"] in users:
            user_id = users[data["email"]]
            if user_id in participants:
                participant_id = participants[user_id]

        voucher = CompVoucher(
            email=data["email"],
            code=data["code"],
            competition_id=comp.id,
            participant_id=participant_id,
            code_used_at=datetime.now()
            if participant_id else None  # Used if associated with participant
        )
        vouchers.append(voucher)

    session.add_all(vouchers)
    session.commit()
    logger.info(f"Created {len(vouchers)} mock competition vouchers")

    return {v.email: v.id for v in vouchers}


def import_mock_temp_captains(session: Session):
    """Create temporary captain participants first."""
    # Check if captains already exist
    existing_captains = session.exec(select(Participant).limit(1)).first()
    if existing_captains:
        logger.info("Participants already exist, skipping captain creation")
        return

    # Get the competition
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if not comp:
        logger.error("Mock competition not found. Cannot create captains.")
        return

    # Create just the captain participants (one for each team)
    captain_data = [{
        "email": "john.smith@example.com",
        "team_name": "Rock Stars"
    }, {
        "email": "sarah.d@example.com",
        "team_name": "Boulderers"
    }, {
        "email": "robert.t@example.com",
        "team_name": "Flash Force"
    }, {
        "email": "thomas.w@example.com",
        "team_name": "Grip Masters"
    }, {
        "email": "jessica.l@example.com",
        "team_name": "The Climbers"
    }, {
        "email": "lucas.p@example.com",
        "team_name": "Ramblers"
    }]

    # Get user IDs
    users = {}
    user_results = session.exec(select(User))
    for user in user_results:
        users[user.email] = user.id

    # Create captain participants
    captains = []
    for data in captain_data:
        if data["email"] in users:
            captain = Participant(competition_id=comp.id,
                                  user_id=users[data["email"]])
            logger.info(
                f"Creating captain for {data['email']} with is_solo=False")
            captains.append(captain)

    session.add_all(captains)
    session.commit()
    logger.info(f"Created {len(captains)} captain participants")

    # Debug check after captain creation
    debug_participants_is_solo(session, comp.id, "after captain creation")


def import_mock_remaining_participants(session: Session):
    """Import the remaining participants."""
    # Get existing participants count
    existing_count = session.exec(select(Participant)).all()
    if len(existing_count) > 6:  # We already have more than just captains
        logger.info("Additional participants already exist, skipping import")
        return

    # Get the competition
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if not comp:
        logger.error("Mock competition not found. Cannot create participants.")
        return

    # Get user IDs
    users = {}
    user_results = session.exec(select(User))
    for user in user_results:
        users[user.email] = user.id

    # Get teams
    teams = {}
    team_results = session.exec(
        select(Team).where(Team.competition_id == comp.id))
    for team in team_results:
        teams[team.name] = team.id

    # Get existing participants' user_ids to avoid duplicates
    existing_user_ids = []
    for participant in existing_count:
        existing_user_ids.append(participant.user_id)

    # Create remaining team participants
    remaining_team_members = [
        # Rock Stars team
        {
            "email": "emily.j@example.com",
            "team_name": "Rock Stars"
        },
        {
            "email": "michael.b@example.com",
            "team_name": "Rock Stars"
        },
        {
            "email": "david.w@example.com",
            "team_name": "Rock Stars"
        },

        # Boulderers team
        {
            "email":
            "jane.doe@example.com",  # Was solo, now added to Boulderers
            "team_name": "Boulderers"
        },

        # Flash Force team
        {
            "email": "jennifer.g@example.com",
            "team_name": "Flash Force"
        },
        {
            "email": "daniel.m@example.com",
            "team_name": "Flash Force"
        },

        # The Climbers team - adding members to make it valid
        {
            "email":
            "alex.t@example.com",  # Was solo, now added to The Climbers
            "team_name": "The Climbers"
        },
        {
            "email":
            "sarah.c@example.com",  # Was solo, now added to The Climbers
            "team_name": "The Climbers"
        },

        # Ramblers team
        {
            "email": "rebecca.c@example.com",
            "team_name": "Ramblers"
        }
    ]

    # Create solo participants
    solo_participants = [{
        "email": "chris.e@example.com"
    }, {
        "email": "maria.r@example.com"
    }, {
        "email": "kevin.l@example.com"
    }]

    # Add all participants
    new_participants = []

    # Add team members
    for data in remaining_team_members:
        if data["email"] in users:
            user_id = users[data["email"]]
            if user_id not in existing_user_ids and data["team_name"] in teams:
                participant = Participant(competition_id=comp.id,
                                          user_id=user_id,
                                          team_id=teams[data["team_name"]])
                logger.info(f"Creating team member {data['email']} "
                            f"for team {data['team_name']}")
                new_participants.append(participant)
                existing_user_ids.append(user_id)  # Add to prevent duplicates

    # Add solo participants
    for data in solo_participants:
        if data["email"] in users:
            user_id = users[data["email"]]
            if user_id not in existing_user_ids:
                participant = Participant(competition_id=comp.id,
                                          user_id=user_id)
                logger.info(f"Creating solo participant {data['email']}")
                new_participants.append(participant)
                existing_user_ids.append(user_id)  # Add to prevent duplicates

    session.add_all(new_participants)
    session.commit()
    logger.info(f"Created {len(new_participants)} additional participants")

    # Debug check after adding all participants
    debug_participants_is_solo(session, comp.id,
                               "after adding all participants")

    # Update team statuses after adding all participants
    for team_id in teams.values():
        update_team_status(session, team_id)
    session.commit()
    logger.info("Updated team statuses after adding participants")


def import_mock_ascents(session: Session):
    """Import mock ascent data."""
    # Check if ascents already exist
    existing_count = session.exec(select(Ascent)).first()
    if existing_count:
        logger.info("Ascents already exist in database, skipping import")
        return

    # Get the competition
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if not comp:
        logger.error("Mock competition not found. Cannot create ascents.")
        return

    # Debug check before querying participants for ascents
    debug_participants_is_solo(session, comp.id, "before ascent creation")

    # Run a quick SQL count to verify is_solo values
    solo_count_query = select(Participant).where(
        Participant.competition_id == comp.id, Participant.is_solo.is_(True))
    team_count_query = select(Participant).where(
        Participant.competition_id == comp.id, Participant.is_solo.is_(False))
    solo_count = len(session.exec(solo_count_query).all())
    team_count = len(session.exec(team_count_query).all())
    logger.info(f"SQL COUNT check: {solo_count} solo participants, "
                f"{team_count} team participants")

    # Get participants with their team information and user details
    participants_query = select(
        Participant.id, Participant.team_id, Participant.is_solo,
        Team.name.label("team_name"), User.id.label("user_id"),
        User.first_name, User.last_name).join(
            Team, Participant.team_id == Team.id, isouter=True).join(
                User, Participant.user_id == User.id,
                isouter=True).where(Participant.competition_id == comp.id)

    participant_results = session.exec(participants_query)

    # Build participants dict and group by team
    participants = {}
    participants_by_team = {}
    solo_count = 0
    team_count = 0

    for p in participant_results:
        # Handle case where user might be None
        if p.first_name and p.last_name:
            full_name = f"{p.first_name} {p.last_name}"
        else:
            full_name = f"Participant_{p.id}"

        # Track is_solo status
        is_solo = p.is_solo
        if is_solo:
            solo_count += 1
        else:
            team_count += 1

        logger.info(f"Participant {full_name} has is_solo={is_solo}, "
                    f"team_id={p.team_id}, team_name={p.team_name}")

        participants[full_name] = {
            "id": p.id,
            "team_id": p.team_id,
            "is_solo": is_solo  # Store is_solo status in the dictionary
        }

        # Group participants by team
        team_name = p.team_name if p.team_name else "Solo"
        if team_name not in participants_by_team:
            participants_by_team[team_name] = []

        participants_by_team[team_name].append(full_name)

    # Ensure all solo participants are properly included in the "Solo" group
    if "Solo" not in participants_by_team:
        participants_by_team["Solo"] = []

    # Double-check that all solo participants are in the Solo group
    for name, info in participants.items():
        if info["is_solo"] and name not in participants_by_team["Solo"]:
            participants_by_team["Solo"].append(name)
            logger.info(f"Added missed solo participant {name} to Solo group")

    logger.info(
        f"Participant query found {solo_count} solo and {team_count} team "
        f"participants")
    logger.info(
        f"Teams in participants_by_team: {list(participants_by_team.keys())}")

    if not participants:
        logger.error(
            "No participants found for the competition. Cannot create ascents."
        )
        return

    # Query existing routes from the database - limit to 200 for now
    # Get routes across all boulders, with a diverse mix of grades
    routes_query = select(Route).limit(MAX_ROUTE_LIMIT)
    routes_result = session.exec(routes_query)

    routes = []
    for r in routes_result:
        routes.append({
            "id": r.id,
            "name": r.name,
            "grade": r.grade,
            "boulder_id": r.boulder_id,
            "boulder_name": r.boulder.name,
            "sector_id": r.boulder.sector_id,
            "sector_name": r.boulder.sector.name
        })

    # If no routes found, log error and return
    if not routes:
        logger.error("No routes found in database. Cannot create ascents.")
        return

    logger.info(f"Found {len(routes)} routes in the database")

    # Group routes by grade for better distribution
    route_by_grade = {}
    for route in routes:
        grade = route["grade"]
        if grade not in route_by_grade:
            route_by_grade[grade] = []
        route_by_grade[grade].append(route)

    # Create a mix of easy, medium, and hard routes
    easy_grades = [
        g for g in route_by_grade.keys()
        if g in ['3', '3+', '4', '4+', '5', '5+', 'V0', 'V1', 'V2']
    ]
    medium_grades = [
        g for g in route_by_grade.keys()
        if g in ['6A', '6A+', '6B', '6B+', '6C', '6C+', 'V3', 'V4', 'V5']
    ]
    hard_grades = [
        g for g in route_by_grade.keys()
        if g in ['7A', '7A+', '7B', '7B+', '7C', 'V6', 'V7', 'V8', 'V9']
    ]

    # Select a diverse set of routes for our mock ascents
    selected_routes = []

    # Select some easy routes
    for grade in easy_grades:
        if grade in route_by_grade and route_by_grade[grade]:
            selected_routes.extend(
                route_by_grade[grade]
                [:min(NO_OF_BEGINNER_ROUTES, len(route_by_grade[grade]))])

    # Select some medium routes
    for grade in medium_grades:
        if grade in route_by_grade and route_by_grade[grade]:
            selected_routes.extend(
                route_by_grade[grade]
                [:min(NO_OF_INTERMEDIATE_ROUTES, len(route_by_grade[grade]))])

    # Select some hard routes
    for grade in hard_grades:
        if grade in route_by_grade and route_by_grade[grade]:
            selected_routes.extend(
                route_by_grade[grade]
                [:min(NO_OF_ADVANCED_ROUTES, len(route_by_grade[grade]))])

    # Make sure we have enough routes (at least MIN_ROUTE_LIMIT)
    if len(selected_routes) < MIN_ROUTE_LIMIT:
        # Add more routes if needed
        remaining_routes = [r for r in routes if r not in selected_routes]
        selected_routes.extend(
            remaining_routes[:min(MIN_ROUTE_LIMIT -
                                  len(selected_routes), len(remaining_routes
                                                            ))])

    # Map route names to IDs for easier reference
    route_dict = {route["name"]: route["id"] for route in selected_routes}

    # Log the routes we'll use
    logger.info(f"Using {len(selected_routes)} routes for mock ascents:")
    for i, route in enumerate(selected_routes):
        logger.info(f"{i+1}. {route['name']} ({route['grade']})"
                    f" - Boulder: {route['boulder_name']}"
                    f" - Sector: {route['sector_name']}")

    # Define which routes each climber will attempt based on skill level
    climber_routes = {}

    # Helper function to get route names by grade difficulty
    def get_routes_by_difficulty(difficulty, count=MIN_ASCENTS_PER_CLIMBER):
        count = min(count, MAX_ASCENTS_PER_CLIMBER)
        if difficulty == "beginner":
            routes = [
                r["name"] for r in selected_routes if r["grade"] in easy_grades
            ]
            # Handle case when there aren't enough routes
            if len(routes) < count:
                count = len(routes)
            return routes[:count]
        elif difficulty == "intermediate":
            routes = [
                r["name"] for r in selected_routes
                if r["grade"] in medium_grades
            ]
            if len(routes) < count:
                count = len(routes)
            return routes[:count]
        elif difficulty == "advanced":
            routes = [
                r["name"] for r in selected_routes if r["grade"] in hard_grades
            ]
            if len(routes) < count:
                count = len(routes)
            return routes[:count]
        else:  # all
            routes = [r["name"] for r in selected_routes]
            if len(routes) < count:
                count = len(routes)
            return routes[:count]

    # Assign routes to climbers based on their skill level and team
    # Using the participants fetched from the database

    # Rock Stars team - advanced climbers
    for member in participants_by_team["Rock Stars"]:
        advanced_routes = get_routes_by_difficulty("advanced", 5)
        intermediate_routes = get_routes_by_difficulty("intermediate", 4)
        easy_routes = get_routes_by_difficulty("beginner", 3)
        climber_routes[
            member] = advanced_routes + intermediate_routes + easy_routes

    # Boulderers team - intermediate climbers
    for member in participants_by_team["Boulderers"]:
        advanced_routes = get_routes_by_difficulty("advanced", 2)
        intermediate_routes = get_routes_by_difficulty("intermediate", 6)
        easy_routes = get_routes_by_difficulty("beginner", 4)
        climber_routes[
            member] = intermediate_routes + easy_routes + advanced_routes

    # Flash Force team - mixed skill levels
    for i, member in enumerate(participants_by_team["Flash Force"]):
        if i == 0:  # First member - advanced
            climber_routes[member] = get_routes_by_difficulty(
                "advanced", 6) + get_routes_by_difficulty("intermediate", 3)
        elif i == 1:  # Second member - intermediate
            climber_routes[member] = get_routes_by_difficulty(
                "intermediate", 7) + get_routes_by_difficulty("beginner", 3)
        else:  # Others - beginners
            climber_routes[member] = get_routes_by_difficulty(
                "beginner", 8) + get_routes_by_difficulty("intermediate", 2)

    # Ramblers team - mixed skill levels with focus on easier routes
    for member in participants_by_team["Ramblers"]:
        # Add a distinguishing factor for each member based on name
        if "Thomas" in member:
            # Thomas is a beginner
            climber_routes[member] = get_routes_by_difficulty("beginner", 10)
        elif "Rebecca" in member:
            # Rebecca likes a variety of routes
            climber_routes[member] = get_routes_by_difficulty(
                "beginner", 4) + get_routes_by_difficulty("intermediate", 6)
        elif "Lucas" in member:
            # Lucas attempts some harder routes
            climber_routes[member] = get_routes_by_difficulty(
                "beginner", 3) + get_routes_by_difficulty(
                    "intermediate", 3) + get_routes_by_difficulty(
                        "advanced", 3)
        else:
            # Other members with mixed routes
            climber_routes[member] = get_routes_by_difficulty(
                "beginner", 5) + get_routes_by_difficulty("intermediate", 5)

    # The Climbers team - mix of difficulties focusing on intermediate routes
    if "The Climbers" in participants_by_team:
        for i, member in enumerate(participants_by_team["The Climbers"]):
            if "Jessica" in member:
                # Jessica is an experienced climber
                climber_routes[member] = get_routes_by_difficulty(
                    "advanced", 4) + get_routes_by_difficulty(
                        "intermediate", 5) + get_routes_by_difficulty(
                            "beginner", 2)
            elif "Alex" in member:
                # Alex prefers technical routes
                climber_routes[member] = get_routes_by_difficulty(
                    "intermediate", 7) + get_routes_by_difficulty(
                        "advanced", 3) + get_routes_by_difficulty(
                            "beginner", 2)
            elif "Sarah" in member:
                # Sarah is a well-rounded climber
                climber_routes[member] = get_routes_by_difficulty(
                    "intermediate", 6) + get_routes_by_difficulty(
                        "beginner", 3) + get_routes_by_difficulty(
                            "advanced", 2)
            else:
                # Default mix for other team members
                climber_routes[member] = get_routes_by_difficulty(
                    "intermediate", 5) + get_routes_by_difficulty(
                        "beginner", 4) + get_routes_by_difficulty(
                            "advanced", 3)

    # Solo participants - various skills
    if "Solo" in participants_by_team:
        for i, member in enumerate(participants_by_team["Solo"]):
            if i % 3 == 0:  # Every 3rd solo participant
                climber_routes[member] = get_routes_by_difficulty(
                    "intermediate", 7) + get_routes_by_difficulty(
                        "beginner", 5)
            elif i % 3 == 1:  # Every 3rd+1 solo participant
                climber_routes[member] = get_routes_by_difficulty(
                    "advanced", 6) + get_routes_by_difficulty(
                        "intermediate", 4)
            else:  # Every 3rd+2 solo participant
                climber_routes[member] = get_routes_by_difficulty(
                    "advanced", 3) + get_routes_by_difficulty(
                        "intermediate", 5) + get_routes_by_difficulty(
                            "beginner", 4)

    # Create ascent objects based on the mapped routes
    all_ascents = []

    for climber_name, route_names in climber_routes.items():
        if climber_name not in participants:
            logger.warning(
                f"Participant {climber_name} not found, skipping ascents")
            continue

        participant_info = participants[climber_name]
        logger.info(f"Creating {len(route_names)} ascents for {climber_name}")

        for route_name in route_names:
            if route_name not in route_dict:
                logger.warning(
                    f"Route {route_name} not found, skipping ascent")
                continue

            ascent = Ascent(competition_id=comp.id,
                            participant_id=participant_info["id"],
                            route_id=route_dict[route_name],
                            team_id=participant_info["team_id"])
            all_ascents.append(ascent)

    # Add all ascents to the database
    session.add_all(all_ascents)
    session.commit()
    logger.info(f"Created {len(all_ascents)} mock ascents using real routes")


def import_mock_scoring_config(session: Session):
    """Import scoring configuration for the mock competition."""
    from database.models.scoring import (BasePoints, VolumeBonus,
                                         UniqueAscentBonus, TeamAscentBonus,
                                         MasterGradeBonus)

    # Get the competition
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if not comp:
        logger.error(
            "Mock competition not found. Cannot create scoring config.")
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

    session.commit()
    logger.info(
        f"Created all scoring configurations for competition {comp.name}")


def initialize_mock_competition_data(session: Session):
    """Initialize the database with mock competition data."""
    import_mock_competitions(session)
    import_mock_users(session)
    import_mock_comp_vouchers(session)

    # New approach - create temporary captains first
    import_mock_temp_captains(
        session)  # Create a minimal set of participants to be captains
    import_mock_teams(session)  # Create teams with captains assigned
    import_mock_remaining_participants(
        session)  # Create the rest of the participants

    import_mock_ascents(session)
    import_mock_scoring_config(session)

    # Final check after everything is done
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if comp:
        debug_participants_is_solo(session, comp.id,
                                   "after complete initialization")

    logger.info("Mock competition data initialization complete")

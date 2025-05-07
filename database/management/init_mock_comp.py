"""
Database initialization for mock competition data.
"""
from datetime import datetime
from sqlmodel import Session, select
import bcrypt
import os
import random

from utils.loggers import logger
from database.models.enums import (EventStatus, CategoryType,
                                   MarathonSubCategory, UserRole)
from database.models.competitions import (Competition, CompetitionCategory,
                                          Team, Participant, Ascent,
                                          CompVoucher)
from database.models.accounts import User
from database.management.init_default_comp import (
    DEFAULT_COMP_NAME, DEFAULT_COMP_DISPLAY_NAME, DEFAULT_COMP_START_DATE,
    DEFAULT_COMP_END_DATE, DEFAULT_CRAG_NAME, import_scoring_config,
    import_competition_boulders)
from database.crud.crags import get_crag_by_name


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


# Constants - Use the defaults from init_default_comp.py
MOCK_COMP_NAME = DEFAULT_COMP_NAME
MOCK_COMP_DISPLAY_NAME = DEFAULT_COMP_DISPLAY_NAME
MOCK_COMP_START_DATE = DEFAULT_COMP_START_DATE.date()
MOCK_COMP_END_DATE = DEFAULT_COMP_END_DATE.date()
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

    # Get the crag to associate with the competition
    crag = get_crag_by_name(session, DEFAULT_CRAG_NAME)
    if not crag:
        logger.error(f"Crag '{DEFAULT_CRAG_NAME}' not found in database. "
                     "Cannot create competition.")
        return

    # Create a mock competition using default values
    comp = Competition(
        name=MOCK_COMP_NAME,
        display_name=MOCK_COMP_DISPLAY_NAME,
        crag_id=crag.id,
        start_date=MOCK_COMP_START_DATE,
        end_date=MOCK_COMP_END_DATE,
        status=EventStatus.ongoing,  # Set as ongoing for mock data
        description="Join us for the annual Spring Bouldering Festival "
        "at Inia-Droushia! "
        "Compete in team or solo categories and test your skills on Cyprus's "
        "finest sandstone boulders.",
        venue="Inia-Droushia Bouldering Area")

    session.add(comp)
    # Flush to get the competition ID
    session.flush()

    # Add categories for the competition using default names but
    # with marathon/boulder_beasts types
    marathon_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.marathon,
        name="Climbathon",
        description="Team-based endurance climbing competition",
        display_order=1)

    boulder_beasts_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.boulder_beasts,
        name="Boulder Titans",
        description="Individual bouldering category awarding top "
        "5 hard ascents",
        display_order=2)

    session.add(marathon_category)
    session.add(boulder_beasts_category)

    # Commit to save the competition and categories
    session.commit()
    logger.info(f"Created mock competition: {comp.display_name}")

    # Import competition boulders using the function from init_default_comp.py
    import_competition_boulders(session, comp.id)

    return comp


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
        # Original teams
        "Rock Stars": "john.smith@example.com",
        "Boulderers": "sarah.d@example.com",
        "Flash Force": "robert.t@example.com",
        "Grip Masters": "thomas.w@example.com",
        "The Climbers": "jessica.l@example.com",
        "Ramblers": "lucas.p@example.com",

        # New teams - higher grade subcategory (6B and above)
        "Vertical Elite": "chris.e@example.com",
        "Hard Crimpers": "maria.r@example.com",
        "Send Squad": "kevin.l@example.com",

        # New teams - lower grade subcategory (6A+ and under)
        "Crag Hoppers": "alex.t@example.com",
        "Rock Rebels": "sarah.c@example.com",
        "Boulder Brigade": "emily.j@example.com"
    }

    # Assign subcategories to teams
    team_subcategories = {
        # Original teams
        "Rock Stars": MarathonSubCategory.gte_6B,
        "Boulderers": MarathonSubCategory.lt_6B,
        "Flash Force": MarathonSubCategory.gte_6B,
        "Grip Masters": MarathonSubCategory.lt_6B,
        "The Climbers": MarathonSubCategory.gte_6B,
        "Ramblers": MarathonSubCategory.lt_6B,

        # New teams - higher grade subcategory (6B and above)
        "Vertical Elite": MarathonSubCategory.gte_6B,
        "Hard Crimpers": MarathonSubCategory.gte_6B,
        "Send Squad": MarathonSubCategory.gte_6B,

        # New teams - lower grade subcategory (6A+ and under)
        "Crag Hoppers": MarathonSubCategory.lt_6B,
        "Rock Rebels": MarathonSubCategory.lt_6B,
        "Boulder Brigade": MarathonSubCategory.lt_6B
    }

    # Get captains' user IDs directly (not participant IDs)
    captains = {}
    for team_name, captain_email in captain_emails.items():
        # Get user ID for the captain
        user = session.exec(
            select(User).where(User.email == captain_email)).first()
        if user:
            captains[team_name] = user.id

    # Create teams with captains and subcategories
    teams = []
    for team_name, captain_id in captains.items():
        # Generate a unique team code
        team_code = f"TEAM{len(teams) + 1:03d}"

        team = Team(competition_id=comp.id,
                    name=team_name,
                    captain_id=captain_id,
                    team_code=team_code,
                    marathon_subcategory=team_subcategories[team_name]
                    # Using default spots=3 from the model
                    )
        teams.append(team)

    session.add_all(teams)
    session.commit()
    logger.info(f"Created {len(teams)} teams with captains and subcategories")

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
            "email": "rebecca.c@example.com",
            "team_name": "The Climbers"
        },
        {
            "email":
            "michael.b@gmail.com",  # Using a new email to avoid conflicts
            "team_name": "The Climbers"
        },

        # Ramblers team
        {
            "email": "jennifer.h@gmail.com",  # New email
            "team_name": "Ramblers"
        },
        {
            "email": "david.j@gmail.com",  # New email
            "team_name": "Ramblers"
        },

        # New teams - Vertical Elite (6B and above)
        {
            "email": "john.k@gmail.com",  # New email
            "team_name": "Vertical Elite"
        },
        {
            "email": "lisa.m@gmail.com",  # New email
            "team_name": "Vertical Elite"
        },

        # Hard Crimpers (6B and above)
        {
            "email": "robert.n@gmail.com",  # New email
            "team_name": "Hard Crimpers"
        },
        {
            "email": "amanda.p@gmail.com",  # New email
            "team_name": "Hard Crimpers"
        },

        # Send Squad (6B and above)
        {
            "email": "james.r@gmail.com",  # New email
            "team_name": "Send Squad"
        },
        {
            "email": "elizabeth.s@gmail.com",  # New email
            "team_name": "Send Squad"
        },

        # Crag Hoppers (6A+ and under)
        {
            "email": "william.t@gmail.com",  # New email
            "team_name": "Crag Hoppers"
        },
        {
            "email": "olivia.u@gmail.com",  # New email
            "team_name": "Crag Hoppers"
        },

        # Rock Rebels (6A+ and under)
        {
            "email": "benjamin.v@gmail.com",  # New email
            "team_name": "Rock Rebels"
        },
        {
            "email": "sophia.w@gmail.com",  # New email
            "team_name": "Rock Rebels"
        },

        # Boulder Brigade (6A+ and under)
        {
            "email": "daniel.x@gmail.com",  # New email
            "team_name": "Boulder Brigade"
        },
        {
            "email": "emma.y@gmail.com",  # New email
            "team_name": "Boulder Brigade"
        }
    ]

    # Create solo participants
    solo_participants = []  # We'll make all new users team members

    # Create users for new team members
    new_users = []
    new_user_emails = set()

    for member in remaining_team_members:
        email = member["email"]
        # Check if this is a new email not in the existing users
        if email not in users and email not in new_user_emails:
            # Extract first and last name from email
            parts = email.split('@')[0].split('.')
            first_name = parts[0].capitalize()
            last_name = parts[1].capitalize() if len(parts) > 1 else "User"

            new_user = User(first_name=first_name,
                            last_name=last_name,
                            email=email,
                            hashed_password=bcrypt.hashpw(
                                "password123".encode(),
                                bcrypt.gensalt()).decode(),
                            role=UserRole.user,
                            confirmed_at=datetime.now())
            new_users.append(new_user)
            new_user_emails.add(email)

    # Add new users to the database
    if new_users:
        session.add_all(new_users)
        session.commit()
        logger.info(f"Created {len(new_users)} new users for team members")

        # Update our users dictionary with the newly created users
        for user in new_users:
            users[user.email] = user.id

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
    # Get the competition
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if not comp:
        logger.error("Competition not found. Cannot create ascents.")
        return

    # Check if ascents already exist for this competition
    existing_count = session.exec(
        select(Ascent).where(Ascent.competition_id == comp.id)).all()
    if existing_count:
        logger.info(
            f"Found {len(existing_count)} ascents for this competition. "
            "Skipping ascent creation.")
        return existing_count

    # Get participants
    participants = session.exec(
        select(Participant).where(
            Participant.competition_id == comp.id)).all()
    if not participants:
        logger.error("No participants found. Cannot create ascents.")
        return

    # Query competition boulders for this competition
    from sqlmodel import select
    from database.models.crags import Route
    from database.models.competitions import CompetitionBoulder

    # Get allowed boulders for this competition
    competition_boulders_query = select(CompetitionBoulder).where(
        CompetitionBoulder.competition_id == comp.id,
        CompetitionBoulder.is_active)
    competition_boulders = session.exec(competition_boulders_query).all()

    if not competition_boulders:
        logger.error("No competition boulders found. Cannot create ascents.")
        return

    boulder_ids = [cb.boulder_id for cb in competition_boulders]
    logger.info(f"Found {len(boulder_ids)} competition boulders")

    # Get routes for these boulders
    routes_query = select(Route).where(Route.boulder_id.in_(boulder_ids))
    routes = session.exec(routes_query).all()

    if not routes:
        logger.error(
            "No routes found for competition boulders. Cannot create ascents.")
        return

    logger.info(f"Found {len(routes)} routes for competition boulders")

    # Group routes by grade for subcategory filtering
    lower_grade_routes = []  # 6A+ and below
    higher_grade_routes = []  # 6B and above

    for route in routes:
        if route.grade in [
                '3', '3+', '4', '4+', '5', '5+', '6A', '6A+', 'V0', 'V1', 'V2'
        ]:
            lower_grade_routes.append(route)
        elif route.grade in [
                '6B', '6B+', '6C', '6C+', '7A', '7A+', '7B', '7B+', '7C', 'V3',
                'V4', 'V5', 'V6', 'V7', 'V8', 'V9'
        ]:
            higher_grade_routes.append(route)

    logger.info(f"Categorized routes: {len(lower_grade_routes)} lower grade, "
                f"{len(higher_grade_routes)} higher grade")

    # Create ascents
    ascents = []

    for participant in participants:
        # Get participant's team to determine subcategory
        team = None
        if participant.team_id:
            team = session.exec(
                select(Team).where(Team.id == participant.team_id)).first()

        # Determine which routes the participant will climb
        available_routes = []
        if team and team.marathon_subcategory == MarathonSubCategory.lt_6B:
            available_routes = lower_grade_routes
        elif team and team.marathon_subcategory == MarathonSubCategory.gte_6B:
            available_routes = higher_grade_routes
        else:
            # Solo participants or teams without subcategory
            # can climb any route
            available_routes = routes

        # Ensure we have routes to assign
        if not available_routes:
            logger.warning(
                f"No suitable routes for participant {participant.id}, "
                "using all routes")
            available_routes = routes

        # Determine number of ascents for this participant
        ascent_count = random.randint(
            MIN_ASCENTS_PER_CLIMBER,
            min(MAX_ASCENTS_PER_CLIMBER, len(available_routes)))

        # Select random routes
        selected_routes = random.sample(available_routes, ascent_count)

        # Create ascents
        for route in selected_routes:
            ascent = Ascent(competition_id=comp.id,
                            participant_id=participant.id,
                            route_id=route.id,
                            team_id=participant.team_id,
                            status=True)
            ascents.append(ascent)

    session.add_all(ascents)
    session.commit()
    logger.info(f"Created {len(ascents)} mock ascents")
    return ascents


def initialize_mock_competition_data(session: Session):
    """Initialize the database with mock competition data."""
    comp = import_mock_competitions(session)
    import_mock_users(session)
    import_mock_comp_vouchers(session)

    # New approach - create temporary captains first
    import_mock_temp_captains(
        session)  # Create a minimal set of participants to be captains
    import_mock_teams(session)  # Create teams with captains assigned
    import_mock_remaining_participants(
        session)  # Create the rest of the participants

    import_mock_ascents(session)

    # Use the scoring config function from init_default_comp.py
    if comp:
        import_scoring_config(session, comp.id)

    # Final check after everything is done
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if comp:
        debug_participants_is_solo(session, comp.id,
                                   "after complete initialization")

    logger.info("Mock competition data initialization complete")

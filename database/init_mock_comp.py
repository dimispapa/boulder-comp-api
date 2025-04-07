"""
Database initialization for mock competition data.
"""
from datetime import datetime, timedelta
from sqlmodel import Session, select

from utils.loggers import logger
from database.models.competitions import (Competition, CompetitionCategory,
                                          Team, Participant, Ascent,
                                          CompetitionStatus, CategoryType)
from database.models.crags import Crag, Route

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
        status=CompetitionStatus.ONGOING,
        description="An exciting bouldering competition at our favorite crag!",
        venue="Outdoor Bouldering Area")

    session.add(comp)
    # Flush to get the competition ID
    session.flush()

    # Add categories for the competition
    marathon_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.MARATHON,
        name="Marathon",
        description="Team-based endurance climbing competition",
        display_order=1)

    boulder_beasts_category = CompetitionCategory(
        competition_id=comp.id,
        category_type=CategoryType.BOULDER_BEASTS,
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
    """Import mock team data."""
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

    # Create six mock teams
    teams = [
        Team(competition_id=comp.id,
             name="Rock Stars",
             category=CategoryType.MARATHON),
        Team(competition_id=comp.id,
             name="Boulderers",
             category=CategoryType.MARATHON),
        Team(competition_id=comp.id,
             name="Flash Force",
             category=CategoryType.MARATHON),
        Team(competition_id=comp.id,
             name="Grip Masters",
             category=CategoryType.MARATHON),
        Team(competition_id=comp.id,
             name="The Climbers",
             category=CategoryType.MARATHON),
        Team(competition_id=comp.id,
             name="Ramblers",
             category=CategoryType.MARATHON)
    ]

    session.add_all(teams)
    session.commit()
    logger.info(f"Created {len(teams)} mock teams")


def import_mock_participants(session: Session):
    """Import mock participant data."""
    # Check if participants already exist
    existing_count = session.exec(select(Participant)).first()
    if existing_count:
        logger.info("Participants already exist in database, skipping import")
        return

    # Get the competition
    comp = session.exec(
        select(Competition).where(Competition.name == MOCK_COMP_NAME)).first()
    if not comp:
        logger.error("Mock competition not found. Cannot create participants.")
        return

    # Get teams
    teams = {}
    team_results = session.exec(
        select(Team).where(Team.competition_id == comp.id))
    for team in team_results:
        teams[team.name] = team.id

    if not teams:
        logger.error(
            "No teams found for the competition. Cannot create participants.")
        return

    # Create mock participants
    participants = [
        # Rock Stars team
        Participant(competition_id=comp.id,
                    team_id=teams["Rock Stars"],
                    first_name="John",
                    last_name="Smith",
                    email="john.smith@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="RS001"),
        Participant(competition_id=comp.id,
                    team_id=teams["Rock Stars"],
                    first_name="Emily",
                    last_name="Johnson",
                    email="emily.j@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="RS002"),
        Participant(competition_id=comp.id,
                    team_id=teams["Rock Stars"],
                    first_name="Michael",
                    last_name="Brown",
                    email="michael.b@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="RS003"),

        # Boulderers team
        Participant(competition_id=comp.id,
                    team_id=teams["Boulderers"],
                    first_name="Sarah",
                    last_name="Davis",
                    email="sarah.d@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="BD001"),
        Participant(competition_id=comp.id,
                    team_id=teams["Boulderers"],
                    first_name="David",
                    last_name="Wilson",
                    email="david.w@example.com",
                    solo_entry=False,
                    club_member=False),
        Participant(competition_id=comp.id,
                    team_id=teams["Boulderers"],
                    first_name="Jessica",
                    last_name="Lee",
                    email="jessica.l@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="BD003"),

        # Flash Force team
        Participant(competition_id=comp.id,
                    team_id=teams["Flash Force"],
                    first_name="Robert",
                    last_name="Taylor",
                    email="robert.t@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="FF001"),
        Participant(competition_id=comp.id,
                    team_id=teams["Flash Force"],
                    first_name="Jennifer",
                    last_name="Garcia",
                    email="jennifer.g@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="FF002"),
        Participant(competition_id=comp.id,
                    team_id=teams["Flash Force"],
                    first_name="Daniel",
                    last_name="Martinez",
                    email="daniel.m@example.com",
                    solo_entry=False,
                    club_member=False),

        # Ramblers team
        Participant(competition_id=comp.id,
                    team_id=teams["Ramblers"],
                    first_name="Thomas",
                    last_name="Wright",
                    email="thomas.w@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="RM001"),
        Participant(competition_id=comp.id,
                    team_id=teams["Ramblers"],
                    first_name="Rebecca",
                    last_name="Chen",
                    email="rebecca.c@example.com",
                    solo_entry=False,
                    club_member=True,
                    membership_number="RM002"),
        Participant(competition_id=comp.id,
                    team_id=teams["Ramblers"],
                    first_name="Lucas",
                    last_name="Park",
                    email="lucas.p@example.com",
                    solo_entry=False,
                    club_member=False),

        # Solo participants (Boulder Beasts category)
        Participant(competition_id=comp.id,
                    first_name="Jane",
                    last_name="Doe",
                    email="jane.doe@example.com",
                    solo_entry=True,
                    club_member=True,
                    membership_number="BB001"),
        Participant(competition_id=comp.id,
                    first_name="Alex",
                    last_name="Turner",
                    email="alex.t@example.com",
                    solo_entry=True,
                    club_member=False),
        Participant(competition_id=comp.id,
                    first_name="Sarah",
                    last_name="Connor",
                    email="sarah.c@example.com",
                    solo_entry=True,
                    club_member=True,
                    membership_number="BB003")
    ]

    session.add_all(participants)
    session.commit()
    logger.info(f"Created {len(participants)} mock participants")


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

    # Get participants with their team information
    participants_query = select(
        Participant.id, Participant.first_name, Participant.last_name,
        Participant.team_id, Team.name.label("team_name")).join(
            Team, Participant.team_id == Team.id,
            isouter=True).where(Participant.competition_id == comp.id)

    participant_results = session.exec(participants_query)

    # Build participants dict and group by team
    participants = {}
    participants_by_team = {}

    for p in participant_results:
        full_name = f"{p.first_name} {p.last_name}"
        participants[full_name] = {"id": p.id, "team_id": p.team_id}

        # Group participants by team
        team_name = p.team_name if p.team_name else "Solo"
        if team_name not in participants_by_team:
            participants_by_team[team_name] = []

        participants_by_team[team_name].append(full_name)

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

    # Solo participants - various skills
    for i, member in enumerate(participants_by_team["Solo"]):
        if i % 3 == 0:  # Every 3rd solo participant
            climber_routes[member] = get_routes_by_difficulty(
                "intermediate", 7) + get_routes_by_difficulty("beginner", 5)
        elif i % 3 == 1:  # Every 3rd+1 solo participant
            climber_routes[member] = get_routes_by_difficulty(
                "advanced", 6) + get_routes_by_difficulty("intermediate", 4)
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
    import_mock_teams(session)
    import_mock_participants(session)
    import_mock_ascents(session)
    import_mock_scoring_config(session)

    logger.info("Mock competition data initialization complete")

"""
Core scoring functionality for calculating competition scores.
"""
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
import json
import uuid
from pathlib import Path
import os
import pandas as pd
from sqlmodel import Session

from utils.loggers import logger
from database.crud.competitions import get_competition_by_id, get_team_by_id
from database.models.competitions import Competition, MarathonSubCategory
from scoring.data_storage import store_results


class ScoreCalculator:
    """
    Handles score calculations for both Marathon and Boulder Beasts categories
    using pandas DataFrames for efficient data manipulation.
    """

    def __init__(self, session: Session, comp_id: str):
        """
        Initialize the score calculator.

        Args:
            session (Session): SQLModel database session.
            comp_id (str): ID of the competition
        """
        self.session = session
        self.comp_id = comp_id

        # Create data directories
        self.data_dir = Path("data/scoring_results")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        os.makedirs('data/calculations', exist_ok=True)
        os.makedirs('data/rankings', exist_ok=True)
        os.makedirs('data/raw', exist_ok=True)

        # Get competition and scoring configuration
        self.competition = self.get_competition()
        self.scoring_config = self._get_scoring_config()

        # DataFrames that will be populated during calculation
        self.ascents_df = pd.DataFrame()
        self.team_scores_df = pd.DataFrame()
        self.individual_scores_df = pd.DataFrame()

    def get_competition(self) -> Optional[Competition]:
        """Get competition directly from database."""
        return get_competition_by_id(self.session, self.comp_id)

    async def _get_scoring_config(self) -> Dict[str, Any]:
        """
        Get the scoring configuration for the competition.

        This uses the competition relationships to retrieve all the
        necessary scoring parameters.

        Returns:
            Dict containing all scoring parameters
        """
        logger.info(f"Getting scoring config for competition {self.comp_id}")

        # Get base points for all grades
        base_points = {}
        if hasattr(self.competition, 'base_points'):
            for bp in self.competition.base_points:
                base_points[bp.grade] = bp.points

        # Get volume bonus configuration
        volume_bonus = {}
        if hasattr(self.competition, 'volume_bonus'):
            volume_bonus["increment"] = \
                self.competition.volume_bonus.bonus_increment
            volume_bonus["points"] = \
                self.competition.volume_bonus.points_per_increment

        # Get team ascent bonuses (special handling for different team sizes)
        team_bonuses = {}
        if hasattr(self.competition, 'team_ascent_bonuses'):
            # Multiple bonuses - one per team size
            for tb in self.competition.team_ascent_bonuses:
                team_bonuses[tb.team_size] = tb.bonus_factor

        # Get unique ascent bonus factor
        unique_bonus_factor = None
        if hasattr(self.competition, 'unique_ascent_bonus'):
            unique_bonus_factor = \
                self.competition.unique_ascent_bonus.bonus_factor

        # Get master grade bonus factor
        master_grade_bonus_factor = None
        if hasattr(self.competition, 'master_grade_bonus'):
            master_grade_bonus_factor = \
                self.competition.master_grade_bonus.bonus_factor

        # Get remote boulder bonus factor
        remote_boulder_bonus_factor = None
        if hasattr(self.competition, 'remote_boulder_bonus'):
            remote_boulder_bonus_factor = \
                self.competition.remote_boulder_bonus.bonus_factor

        # Combine all configurations into one dictionary
        config = {
            "base_points": base_points,
            "volume_bonus": volume_bonus,
            "team_bonuses": team_bonuses,
            "unique_bonus_factor": unique_bonus_factor,
            "master_grade_bonus_factor": master_grade_bonus_factor,
            "remote_boulder_bonus_factor": remote_boulder_bonus_factor
        }

        logger.debug(f"Scoring config: {config}")
        return config

    def _save_json_data(self, data: Any, filename: str) -> str:
        """
        Save data to a JSON file.

        Args:
            data: Data to save
            filename: Base filename

        Returns:
            str: Path to the saved file
        """
        # Create a unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        full_filename = f"{filename}_{timestamp}_{unique_id}.json"
        file_path = self.data_dir / full_filename

        # Save data to file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved detailed data to {file_path}")
        return str(file_path)

    async def _prepare_ascents_dataframe(self) -> pd.DataFrame:
        """
        Prepare a DataFrame of all ascents with necessary information
        for scoring.
        Uses the competition relationship to access ascents directly.

        Returns:
            pandas.DataFrame: DataFrame with all ascent data
        """
        # Create an empty list to collect ascent data
        ascents_data = []

        # Iterate through all ascents in the competition using the relationship
        for ascent in self.competition.ascents:
            # Get related objects through relationship properties
            participant = ascent.participant
            route = ascent.route
            team = participant.team

            # Create a dictionary with all relevant ascent data
            ascent_dict = {
                "ascent_id": str(ascent.id),
                "participant_id": str(participant.id),
                "participant_name":
                f"{participant.user.first_name} {participant.user.last_name}",
                "route_id": str(route.id),
                "route_name": route.name,
                "grade": route.grade,
                "inserted_at": ascent.inserted_at,
                "is_solo": participant.is_solo
            }

            # Add team info if present
            if team:
                ascent_dict["team_id"] = str(team.id)
                ascent_dict["team_name"] = team.name
            else:
                ascent_dict["team_id"] = None
                ascent_dict["team_name"] = None

            # Append to our list
            ascents_data.append(ascent_dict)

        # Convert to DataFrame
        df = pd.DataFrame(ascents_data)

        # Add base points column using our scoring config
        df["base_points"] = df["grade"].apply(
            lambda g: self.scoring_config["base_points"].get(g, 0))

        # Store the DataFrame for further calculations
        self.ascents_df = df

        return df

    async def calculate_scores(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate scores for the competition and store results in the database.

        This method coordinates the scoring workflow:
        1. Get the scoring configuration
        2. Prepare ascent data
        3. Calculate scores based on competition category
        4. Store results in the database

        Returns:
            Dictionary with two keys: "marathon" and "boulder_beasts",
            each containing a list of rankings
        """
        try:
            # Get scoring parameters from config
            self.scoring_config = await self._get_scoring_config()

            # Prepare ascents DataFrame
            await self._prepare_ascents_dataframe()

            # Get category name from competition
            categories = self.competition.categories

            # Dictionary to return the results
            rankings = {"marathon": [], "boulder_beasts": []}

            logger.info(f"Calculating scores for competition {self.comp_id} "
                        f"with categories {categories}")
            for category in categories:
                category_name = category.name
                # Calculate scores based on category
                if category_name.lower() == "marathon":
                    team_scores, detailed_calculations = \
                        await self._calculate_marathon_scores()
                    # Store the results
                    await store_results(self.session,
                                        self.comp_id,
                                        team_scores,
                                        detailed_calculations,
                                        is_marathon=True)
                    # Add to return dictionary
                    rankings["marathon"] = team_scores
                elif category_name.lower() == "boulder beasts":
                    participant_scores = \
                        await self._calculate_boulder_beasts_scores()
                    # Store the results
                    await store_results(self.session,
                                        self.comp_id,
                                        participant_scores,
                                        None,
                                        is_marathon=False)
                    # Add to return dictionary
                    rankings["boulder_beasts"] = participant_scores
                else:
                    logger.warning(
                        f"Unsupported competition category: {category_name}")
                    raise NotImplementedError(
                        f"Scoring for {category_name} is not implemented")

            logger.info(
                f"Score calculation completed for competition {self.comp_id}")

            return rankings

        except Exception as e:
            logger.error(f"Error calculating scores: {str(e)}", exc_info=True)
            raise

    async def _get_master_grade_teams(
            self, ascents_df: pd.DataFrame) -> Dict[str, str]:
        """
        Find teams with most ascents per grade.
        """
        # Find teams with most ascents per grade
        grade_team_counts = ascents_df.groupby(
            ["grade", "team_id"]).size().reset_index(name="ascent_count")
        master_grade_teams = {}

        for grade in grade_team_counts["grade"].unique():
            grade_df = grade_team_counts[grade_team_counts["grade"] == grade]
            if not grade_df.empty:
                max_team = grade_df.loc[grade_df["ascent_count"].idxmax()]
                master_grade_teams[grade] = max_team["team_id"]

        return master_grade_teams

    async def _get_unique_ascents(self, ascents_df: pd.DataFrame) -> Set[str]:
        """
        Get unique ascents from an ascents DataFrame.
        """
        unique_routes = set(ascents_df["route_id"].unique())
        return unique_routes

    async def _calculate_route_team_bonus(
            self, route_df: pd.DataFrame, base_points: float,
            team_size: int) -> Tuple[float, float]:
        """
        Calculate team ascent bonus for a given route.

        Args:
            route_df (pd.DataFrame): DataFrame containing route data
            team_size (int): Size of the team

        Returns:
            Float of route team bonus
        """
        # Count participants who climbed this route
        team_sends = route_df["participant_id"].nunique()
        is_team_complete = team_sends == team_size

        # Calculate team ascent bonus
        route_team_bonus = 0
        if is_team_complete:
            bonus_factor = self.scoring_config["team_bonuses"].get(
                team_size, 0)
            route_team_bonus = base_points * bonus_factor

        return route_team_bonus

    async def _calculate_master_grade_bonus(
            self, team_id: str,
            team_df: pd.DataFrame) -> Tuple[float, List[str]]:
        """
        Calculate the master grade bonus for a team.
        This bonus is awarded to teams that have the most ascents for
        each grade.

        Returns:
            Tuple containing the master grade bonus score and a list of
            master grades
        """
        master_grade_bonus = 0.0
        master_grades = []

        if self.scoring_config.get("master_grade_bonus_factor"):
            bonus_factor = self.scoring_config["master_grade_bonus_factor"]

            for grade, master_team in self.master_grade_teams.items():
                if master_team == team_id:
                    master_grades.append(grade)
                    # Get all routes of this grade climbed by the team
                    grade_routes = team_df[team_df["grade"] == grade]

                    # Sum the base points for all routes of this grade
                    grade_points = grade_routes["base_points"].sum()

                    # Apply the bonus factor
                    grade_bonus = grade_points * bonus_factor

                    master_grade_bonus += grade_bonus

                    # Debug log
                    logger.debug(f"Team {team_id} gets master grade bonus of "
                                 f"{grade_bonus} for grade {grade}")

        return master_grade_bonus, master_grades

    def _get_boulder_id_for_route(self, route_id: str) -> Optional[uuid.UUID]:
        """
        Get the boulder ID for a given route ID.

        Args:
            route_id (str): ID of the route

        Returns:
            Optional[UUID]: The boulder ID or None if not found
        """
        from database.models.crags import Route
        from sqlmodel import select

        # Execute a query to get the route's boulder_id
        statement = select(Route.boulder_id).where(Route.id == route_id)
        boulder_id = self.session.exec(statement).first()

        return boulder_id

    async def _calculate_remote_boulder_bonus(self,
                                              team_df: pd.DataFrame) -> float:
        """
        Calculate the remote boulder bonus for a team.
        This bonus is applied to ascents on boulders that are
        designated as remote.

        Args:
            team_df: DataFrame with the team's ascents

        Returns:
            float: The remote boulder bonus score
        """
        from database.models.scoring import RemoteBoulder
        from sqlmodel import select

        remote_boulder_bonus = 0.0

        # Check if remote boulder bonus is configured
        if not self.scoring_config.get("remote_boulder_bonus_factor"):
            return remote_boulder_bonus

        # Get the default bonus factor from competition settings
        default_bonus_factor = self.scoring_config[
            "remote_boulder_bonus_factor"]

        # Get all remote boulder IDs and their specific bonus factors
        statement = select(RemoteBoulder)
        remote_boulders = {
            str(rb.boulder_id): rb.bonus_factor
            for rb in self.session.exec(statement).all()
        }

        if not remote_boulders:
            logger.debug("No remote boulders found in the database")
            return remote_boulder_bonus

        # Group by route to process each route once
        for route_id in team_df["route_id"].unique():
            # Convert the route_id to UUID
            route_uuid = route_id
            if isinstance(route_id, str):
                route_uuid = uuid.UUID(route_id)

            route_df = team_df[team_df["route_id"] == route_id]

            # Get boulder ID for this route
            boulder_id = self._get_boulder_id_for_route(route_uuid)

            # Continue if no boulder_id found
            if not boulder_id:
                continue

            # Check if the route's boulder is in the remote boulders list
            if str(boulder_id) in remote_boulders:
                # Get boulder-specific bonus factor
                bonus_factor = remote_boulders[str(boulder_id)]

                # Calculate bonus: base points * bonus factor
                base_points = route_df["base_points"].sum()
                route_remote_bonus = base_points * bonus_factor

                remote_boulder_bonus += route_remote_bonus

                # Debug log
                route_details = route_df.iloc[0]
                logger.debug(
                    f"Route {route_details['route_name']} gets remote bonus: "
                    f"{route_remote_bonus}"
                )

        return remote_boulder_bonus

    async def _calculate_unique_ascent_bonus(self, route_id: str,
                                             base_points: float) -> float:
        """
        Calculate unique ascent bonus for a route.
        """
        route_unique_bonus = 0
        is_unique = route_id in self.unique_routes
        if is_unique:
            route_unique_bonus = base_points * self.scoring_config[
                "unique_bonus_factor"]

        return route_unique_bonus

    async def _calculate_volume_bonus(self, total_ascents: int) -> float:
        """
        Calculate volume bonus for a given number of ascents.
        """
        volume_bonus_increment = self.scoring_config["volume_bonus"][
            "increment"]
        volume_bonus_points = self.scoring_config["volume_bonus"]["points"]
        volume_bonus = (total_ascents //
                        volume_bonus_increment) * volume_bonus_points

        return volume_bonus

    async def _calculate_marathon_scores(
            self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Calculate Marathon scores using pandas DataFrames.

        Returns:
            Tuple of (team scores list, detailed calculations list)
        """

        # Filter out solo entries
        team_ascents_df = self.ascents_df[~self.ascents_df["is_solo"]].copy()

        logger.info("Starting Marathon score calculation with "
                    f"{len(team_ascents_df)} ascents")

        # 1. Calculate unique ascents (routes climbed by only one person)
        self.unique_routes = await self._get_unique_ascents(team_ascents_df)

        # 2. Find teams with most ascents per grade (for master grade bonus)
        self.master_grade_teams = await self._get_master_grade_teams(
            team_ascents_df)

        # 3. Calculate team scores
        team_scores = []
        detailed_calculations = []

        # Get teams from the DataFrame
        teams = team_ascents_df[["team_id",
                                 "team_name"]].dropna().drop_duplicates()

        # Create a mapping of team_id to subcategory
        team_subcategories = {}
        for _, team_row in teams.iterrows():
            team_id = team_row["team_id"]
            # Get team from database to determine subcategory
            team = get_team_by_id(self.session, team_id)
            if team:
                team_subcategories[team_id] = team.marathon_subcategory

        # Iterate through all teams
        for _, team_row in teams.iterrows():
            team_id = team_row["team_id"]
            team_name = team_row["team_name"]
            subcategory = team_subcategories.get(team_id)

            # Filter ascents for this team
            team_df = team_ascents_df[team_ascents_df["team_id"] == team_id]

            # Filter out ascents that don't match the team's subcategory
            if subcategory:
                # Create mask of valid ascents for subcategory
                valid_ascents_mask = team_df.apply(
                    lambda row: self._is_route_valid_for_subcategory(
                        row["grade"], subcategory),
                    axis=1)

                # Apply filter
                filtered_team_df = team_df[valid_ascents_mask]

                # Log how many ascents were filtered out
                filtered_out = len(team_df) - len(filtered_team_df)
                if filtered_out > 0:
                    logger.info(
                        f"Team {team_name} ({subcategory.value}): "
                        f"Filtered out {filtered_out} ascents that don't "
                        f"match subcategory")

                # Use filtered DataFrame for scoring
                team_df = filtered_team_df

            # Skip if no valid ascents remain
            if len(team_df) == 0:
                logger.warning(
                    f"Team {team_name} has no valid ascents for "
                    f"subcategory {subcategory.value if subcategory else None}"
                )
                continue

            # Calculate team size
            team_size = team_df["participant_id"].nunique()

            # Get unique team members and routes
            team_routes = team_df["route_id"].unique()

            # Initialize variables
            team_completed_routes = []
            team_unique_routes = []
            detailed_routes = []

            base_score = 0
            team_ascent_bonus = 0
            unique_ascent_bonus = 0

            # Group by route to process each route once
            for route_id in team_routes:
                route_df = team_df[team_df["route_id"] == route_id]

                # Get first occurrence for route details (grade, name, etc.)
                route_details = route_df.iloc[0]

                # Total base points for this route
                base_points = route_df["base_points"].sum()
                base_score += base_points

                # Calculate team ascent bonus
                route_team_bonus = await self._calculate_route_team_bonus(
                    route_df, base_points, team_size)
                if route_team_bonus > 0:
                    # Add to the total team ascent bonus
                    team_ascent_bonus += route_team_bonus
                    # Add to the list of completed routes
                    team_completed_routes.append(route_id)

                # Calculate unique ascent bonus
                route_unique_bonus = await self._calculate_unique_ascent_bonus(
                    route_id, base_points)
                if route_unique_bonus > 0:
                    # Add to the total unique ascent bonus
                    unique_ascent_bonus += route_unique_bonus
                    # Add to the list of unique routes
                    team_unique_routes.append(route_id)

                # Store detailed route calculation
                detailed_routes.append({
                    "route_id":
                    route_id,
                    "route_name":
                    route_details["route_name"],
                    "grade":
                    route_details["grade"],
                    "base_points":
                    base_points,
                    "team_ascent_bonus":
                    route_team_bonus,
                    "unique_ascent_bonus":
                    route_unique_bonus,
                    "total_points":
                    base_points + route_team_bonus + route_unique_bonus
                })

            # Calculate volume bonus
            total_ascents = len(team_df)
            volume_bonus = await self._calculate_volume_bonus(total_ascents)

            # Calculate master grade bonus
            if team_id in self.master_grade_teams.values():
                master_grade_bonus, master_grades = \
                    await self._calculate_master_grade_bonus(team_id, team_df)
            else:
                master_grade_bonus = 0
                master_grades = []

            # Calculate remote boulder bonus
            remote_boulder_bonus = await self._calculate_remote_boulder_bonus(
                team_df)

            # Calculate total and normalized scores
            total_score = (base_score + volume_bonus + team_ascent_bonus +
                           unique_ascent_bonus + master_grade_bonus +
                           remote_boulder_bonus)
            normalized_score = total_score / team_size

            # Create team score entry
            team_score = {
                "competition_id": self.comp_id,
                "team_id": team_id,
                "team_name": team_name,
                "team_size": team_size,
                "base_score": base_score,
                "volume_bonus": volume_bonus,
                "team_ascent_bonus": team_ascent_bonus,
                "unique_ascent_bonus": unique_ascent_bonus,
                "master_grade_bonus": master_grade_bonus,
                "remote_boulder_bonus": remote_boulder_bonus,
                "total_score": total_score,
                "normalized_score": normalized_score,
                "marathon_subcategory":
                subcategory.value if subcategory else None,
                "ranking": None  # Will be set after sorting
            }

            # Create detailed calculation entry
            detailed_calculation = {
                "team_id": team_id,
                "team_name": team_name,
                "team_size": team_size,
                "routes": detailed_routes,
                "total_ascents": total_ascents,
                "volume_bonus": volume_bonus,
                "team_completed_routes": team_completed_routes,
                "team_unique_routes": team_unique_routes,
                "master_grades": master_grades,
                "master_grade_bonus": master_grade_bonus,
                "remote_boulder_bonus": remote_boulder_bonus,
                "base_score": base_score,
                "team_ascent_bonus": team_ascent_bonus,
                "unique_ascent_bonus": unique_ascent_bonus,
                "total_score": total_score,
                "normalized_score": normalized_score,
                "marathon_subcategory":
                subcategory.value if subcategory else None,
                "ranking": None  # Add ranking field, to be set after sorting
            }

            team_scores.append(team_score)
            detailed_calculations.append(detailed_calculation)

        # Group teams by subcategory
        subcategory_teams = {
            # Using the enum member names as keys
            MarathonSubCategory.lt_6B.name: [],
            MarathonSubCategory.gte_6B.name: [],
            None: []  # For teams without subcategory
        }

        for team in team_scores:
            subcategory = team.get("marathon_subcategory")
            # Use the enum values directly for comparison
            if subcategory == MarathonSubCategory.lt_6B.value:
                subcategory_teams[MarathonSubCategory.lt_6B.name].append(team)
            elif subcategory == MarathonSubCategory.gte_6B.value:
                subcategory_teams[MarathonSubCategory.gte_6B.name].append(team)
            else:
                subcategory_teams[None].append(team)

        # Sort and rank teams within each subcategory
        ranked_teams = []

        for subcategory, teams in subcategory_teams.items():
            if not teams:
                continue

            # Sort teams by normalized score
            sorted_teams = sorted(teams,
                                  key=lambda x: x["normalized_score"],
                                  reverse=True)

            # Assign rankings within subcategory
            for i, team in enumerate(sorted_teams):
                team["ranking"] = i + 1
                ranked_teams.append(team)

                # Update the corresponding detailed calculation
                for calc in detailed_calculations:
                    if calc["team_id"] == team["team_id"]:
                        calc["ranking"] = i + 1

        logger.info("Completed Marathon score calculation for "
                    f"{len(team_scores)} teams")
        return ranked_teams, detailed_calculations

    async def _calculate_boulder_beasts_scores(self) -> List[Dict[str, Any]]:
        """
        Calculate Boulder Beasts scores using pandas DataFrames.

        Returns:
            List of participant scores
        """
        ascents_df = self.ascents_df.copy()
        logger.info(f"Starting Boulder Beasts score calculation with "
                    f"{len(ascents_df)} ascents")

        # Get ALL participants from the competition
        all_participants = []
        for participant in self.competition.participants:
            all_participants.append({
                "participant_id": str(participant.id),
                "participant_name":
                f"{participant.user.first_name} {participant.user.last_name}",
                "is_solo": participant.is_solo
            })

        # Create a list to store participant scores
        participant_scores = []

        # Iterate through all participants
        for participant in all_participants:
            participant_id = participant["participant_id"]
            participant_name = participant["participant_name"]

            # Filter ascents for this participant
            participant_df = ascents_df[ascents_df["participant_id"] ==
                                        participant_id]

            if len(participant_df) > 0:
                # Participant has ascents
                # Sort routes by base points (descending) and take top 5
                top_5_routes_df = participant_df.sort_values(
                    "base_points", ascending=False).head(5)
                # Sum the base points of these top 5 routes
                top_5_routes_score = top_5_routes_df["base_points"].sum()
                # Get list of top 5 route names + grades
                top_5_routes = (top_5_routes_df["route_name"] + " - " +
                                top_5_routes_df["grade"]).tolist()

                # Calculate total points
                total_score = participant_df["base_points"].sum()
            else:
                # Participant has no ascents
                top_5_routes = []
                top_5_routes_score = 0
                total_score = 0

            # Create participant score entry
            participant_score = {
                "competition_id": self.comp_id,
                "participant_id": participant_id,
                "participant_name": participant_name,
                "total_score": total_score,
                "top_5_routes": top_5_routes,
                "top_5_routes_score": top_5_routes_score,
                "ranking": None  # Will be set after sorting
            }

            # Append the participant score to the list
            participant_scores.append(participant_score)

        # Sort participants by top 5 routes score and on a tie by total score
        sorted_scores = sorted(participant_scores,
                               key=lambda x:
                               (x["top_5_routes_score"], x["total_score"]),
                               reverse=True)
        for i, participant in enumerate(sorted_scores):
            participant["ranking"] = i + 1

        logger.info(f"Completed Boulder Beasts score calculation for "
                    f"{len(participant_scores)} participants")
        return sorted_scores

    async def _is_route_valid_for_subcategory(
            self, grade: str,
            subcategory: Optional[MarathonSubCategory]) -> bool:
        """
        Check if a route grade is valid for a given subcategory.

        Args:
            grade (str): The grade of the route
            subcategory (MarathonSubCategory): The team's subcategory

        Returns:
            bool: True if valid, False if not
        """
        if subcategory is None:
            # If no subcategory defined, all routes are valid
            return True

        # Check if grade matches subcategory requirements
        if subcategory == MarathonSubCategory.lt_6B:
            # For "6A+ and under" subcategory, grade should be <= 6A+
            return grade <= "6A+"
        elif subcategory == MarathonSubCategory.gte_6B:
            # For "6B and above" subcategory, grade should be >= 6B
            return grade >= "6B"

        # Default case - should not reach here
        logger.warning(f"Unknown subcategory: {subcategory}")
        return True

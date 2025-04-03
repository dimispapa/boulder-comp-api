"""
Core scoring functionality for calculating competition scores.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import uuid
from pathlib import Path
from sqlmodel import Session
from utils.loggers import logger
from database.crud.competitions import (get_competition_by_id,
                                        get_ascents_by_competition_id)
from database.crud.scoring import (get_base_points_by_grade,
                                   get_all_volume_bonuses,
                                   get_all_team_bonuses,
                                   get_all_master_grade_bonuses,
                                   create_marathon_ranking,
                                   create_boulder_beasts_ranking)


class ScoreCalculator:
    """
    Handles score calculations for both Marathon and Boulder Beasts categories.
    """

    def __init__(self, session: Session):
        """
        Initialize the score calculator.

        Args:
            session (Session): SQLModel database session.
        """
        self.session = session
        # Create a data directory to store JSON files if it doesn't exist
        self.data_dir = Path("data/scoring_results")
        self.data_dir.mkdir(parents=True, exist_ok=True)

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

    async def calculate_scores(self, comp_id: str) -> Dict[str, Any]:
        """
        Calculate scores for all participants in both categories.

        Args:
            comp_id (str): ID of the competition

        Returns:
            dict: Calculated scores and rankings for both categories
        """
        try:
            logger.info(
                f"Beginning score calculation for competition {comp_id}")

            # Get competition details
            comp = await self._get_competition(comp_id)
            if not comp:
                logger.error(f"Competition {comp_id} not found")
                raise ValueError(f"Competition {comp_id} not found")

            # Get all ascents for this competition
            ascents = await self._get_competition_ascents(comp_id)
            logger.info(
                f"Retrieved {len(ascents)} ascents for competition {comp_id}")

            # Save raw ascents data
            self._save_json_data({
                "competition": comp,
                "ascents": ascents
            }, f"comp_{comp_id}_raw_data")

            # Calculate Marathon scores if category is enabled
            marathon_scores = []
            if 'marathon' in comp['categories']:
                logger.info(
                    f"Calculating Marathon scores for competition {comp_id}")
                marathon_scores, marathon_details = \
                    await self._calculate_marathon_scores(
                        ascents, comp_id)
                logger.info(f"Calculated Marathon scores for "
                            f"{len(marathon_scores)} teams")

                # Save detailed Marathon calculations
                self._save_json_data(marathon_details,
                                     f"comp_{comp_id}_marathon_calculations")

                # Save final Marathon rankings
                self._save_json_data(marathon_scores,
                                     f"comp_{comp_id}_marathon_rankings")

            # Calculate Boulder Beasts scores if category is enabled
            boulder_beasts_scores = []
            if 'boulder_beasts' in comp['categories']:
                logger.info(f"Calculating Boulder Beasts scores "
                            f"for competition {comp_id}")
                boulder_beasts_scores, boulder_details = \
                    await self._calculate_boulder_beasts_scores(
                        ascents, comp_id)
                logger.info(f"Calculated Boulder Beasts scores for "
                            f"{len(boulder_beasts_scores)} participants")

                # Save detailed Boulder Beasts calculations
                self._save_json_data(
                    boulder_details,
                    f"comp_{comp_id}_boulder_beasts_calculations")

                # Save final Boulder Beasts rankings
                self._save_json_data(
                    boulder_beasts_scores,
                    f"comp_{comp_id}_boulder_beasts_rankings")

            # Save combined final rankings before storing in database
            combined_rankings = {
                "competition_id": comp_id,
                "marathon": marathon_scores,
                "boulder_beasts": boulder_beasts_scores,
                "timestamp": datetime.now().isoformat()
            }

            self._save_json_data(combined_rankings,
                                 f"comp_{comp_id}_final_rankings")

            # Store results in database
            logger.info(f"Storing calculation results in database "
                        f"for competition {comp_id}")
            await self._store_results(comp_id, marathon_scores,
                                      boulder_beasts_scores)

            logger.info(
                f"Score calculation completed for competition {comp_id}")
            return combined_rankings

        except Exception as e:
            logger.error(
                f"Error calculating scores for competition {comp_id}: {str(e)}"
            )
            raise Exception(f"Error calculating scores: {str(e)}")

    async def _get_competition(self, comp_id: str) -> Optional[Dict[str, Any]]:
        """Get competition details using SQLModel."""
        competition = get_competition_by_id(self.session, comp_id)

        if not competition:
            return None

        # Convert Competition object to dict
        # for consistency with previous implementation
        return {
            "id": str(competition.id),
            "name": competition.name,
            "categories": competition.categories_list,
            "start_date": competition.start_date,
            "end_date": competition.end_date,
            "status": competition.status,
            "crag_id": str(competition.crag_id)
        }

    async def _get_competition_ascents(self,
                                       comp_id: str) -> List[Dict[str, Any]]:
        """Get all ascents for a competition with related data
        using SQLModel."""
        # Fetch raw ascents for the competition
        ascents = get_ascents_by_competition_id(self.session, comp_id)

        # Convert to list of dictionaries
        # for consistency with previous implementation
        result = []
        for ascent in ascents:
            # Get related data
            participant = ascent.participant
            route = ascent.route
            team = participant.team

            # Create a dictionary with all required data
            ascent_dict = {
                "id": str(ascent.id),
                "competition_id": str(ascent.competition_id),
                "participant_id": str(ascent.participant_id),
                "route_id": str(ascent.route_id),
                "timestamp": ascent.timestamp,
                "participants": {
                    "id":
                    str(participant.id),
                    "first_name":
                    participant.first_name,
                    "last_name":
                    participant.last_name,
                    "email":
                    participant.email,
                    "team_id":
                    str(participant.team_id)
                    if participant.team_id else None,
                    "solo_entry":
                    participant.solo_entry
                },
                "routes": {
                    "id": str(route.id),
                    "name": route.name,
                    "display_name": route.display_name,
                    "grade": route.grade,
                    "rating": route.rating
                }
            }

            # Add team info if present
            if team:
                ascent_dict["teams"] = {
                    "id": str(team.id),
                    "name": team.name,
                    "category": team.category
                }

            result.append(ascent_dict)

        return result

    async def _calculate_marathon_scores(self, ascents: List[Dict[str, Any]],
                                         comp_id: str) -> tuple:
        """Calculate scores for the Marathon category."""
        # Group ascents by team and track which routes are climbed by each team
        team_scores = {}
        route_teams = {}  # Track which teams climbed each route

        # Detailed calculation data to save
        calculation_details = {
            "competition_id": comp_id,
            "timestamp": datetime.now().isoformat(),
            "team_ascents": {},
            "route_teams": {},
            "team_sizes": {},
            "base_scores": {},
            "unique_ascents": {},
            "volume_bonuses": {},
            "team_bonuses": {},
            "team_route_completions": {},
            "grade_leaders": {},
            "master_grade_bonuses": {},
            "normalization": {},
            "config": {
                "volume_bonus": None,
                "team_ascent_bonus": None,
                "master_grade_bonus": None
            }
        }

        logger.info(f"Processing {len(ascents)} ascents for Marathon scoring")

        # First pass: organize ascents and track route completion by teams
        for ascent in ascents:
            if not ascent.get('team_id'):
                continue  # Skip solo participants (no team_id)

            team_id = ascent['team_id']
            route_id = ascent['route_id']
            participant_id = ascent['participant_id']
            grade = ascent['grade']

            # Initialize team data if not exists
            if team_id not in team_scores:
                team_scores[team_id] = {
                    'team_id': team_id,
                    'team_name': ascent.get('teams', {}).get('name'),
                    'base_score': 0,
                    'volume_score': 0,
                    'unique_ascent_score': 0,
                    'team_ascent_bonus': 0,
                    'master_grade_bonus': 0,
                    'total_score': 0,
                    'ascents': [],
                    'route_completions':
                    {},  # Track participant completions per route
                    'grades_count': {}  # Count ascents by grade
                }

                calculation_details["team_ascents"][team_id] = []
                calculation_details["team_route_completions"][team_id] = {}

            # Track this ascent
            team_scores[team_id]['ascents'].append(ascent)

            # Add to detailed calculation data
            calculation_details["team_ascents"][team_id].append({
                "route_id":
                route_id,
                "participant_id":
                participant_id,
                "grade":
                grade,
                "ascent_id":
                ascent.get('id')
            })

            # Track which teams climbed each route
            if route_id not in route_teams:
                route_teams[route_id] = set()
                calculation_details["route_teams"][route_id] = []

            route_teams[route_id].add(team_id)
            if team_id not in calculation_details["route_teams"][route_id]:
                calculation_details["route_teams"][route_id].append(team_id)

            # Track participant completions per route for team ascent bonus
            if route_id not in team_scores[team_id]['route_completions']:
                team_scores[team_id]['route_completions'][route_id] = set()
                calculation_details["team_route_completions"][team_id][
                    route_id] = []

            team_scores[team_id]['route_completions'][route_id].add(
                participant_id)

            if participant_id not in calculation_details[
                    "team_route_completions"][team_id][route_id]:
                calculation_details["team_route_completions"][team_id][
                    route_id].append(participant_id)

            # Count ascents by grade for master grade bonus
            if grade not in team_scores[team_id]['grades_count']:
                team_scores[team_id]['grades_count'][grade] = 0
            team_scores[team_id]['grades_count'][grade] += 1

        logger.info(f"Processed ascents for {len(team_scores)} teams")

        # Second pass: calculate base scores and identify unique ascents
        for team_id, data in team_scores.items():
            # Get the number of participants in the team
            team_members = set()
            for ascent in data['ascents']:
                team_members.add(ascent['participant_id'])
            team_size = len(team_members)
            data['team_size'] = team_size

            calculation_details["team_sizes"][team_id] = team_size
            calculation_details["base_scores"][team_id] = 0
            calculation_details["unique_ascents"][team_id] = []

            # Calculate base score
            for ascent in data['ascents']:
                base_points = await self._get_base_points(ascent['grade'])
                data['base_score'] += base_points

                # Track base points in details
                calculation_details["base_scores"][team_id] += base_points

                # Check if this is a unique ascent
                # (only this team climbed this route)
                route_id = ascent['route_id']
                # Only this team climbed it
                if len(route_teams[route_id]) == 1:
                    data['unique_ascent_score'] += base_points
                    calculation_details["unique_ascents"][team_id].append({
                        "route_id":
                        route_id,
                        "grade":
                        ascent['grade'],
                        "points":
                        base_points
                    })

        logger.info("Calculating volume bonuses")
        # Calculate volume bonuses
        volume_bonus_config = await self._get_volume_bonus_config()
        calculation_details["config"]["volume_bonus"] = volume_bonus_config
        calculation_details["volume_bonuses"] = {}

        for team_id, data in team_scores.items():
            ascent_count = len(data['ascents'])
            volume_bonus = (
                (ascent_count // volume_bonus_config['bonus_increment']) *
                volume_bonus_config['points_per_increment'])
            data['volume_score'] = volume_bonus

            calculation_details["volume_bonuses"][team_id] = {
                "ascent_count":
                ascent_count,
                "bonus_increments":
                ascent_count // volume_bonus_config['bonus_increment'],
                "points_per_increment":
                volume_bonus_config['points_per_increment'],
                "total_bonus":
                volume_bonus
            }

        logger.info("Calculating team ascent bonuses")
        # Calculate team ascent bonuses
        # apply when whole team completes a route
        team_bonus_config = await self._get_team_ascent_bonus_config()
        calculation_details["config"]["team_ascent_bonus"] = team_bonus_config
        calculation_details["team_bonuses"] = {}

        for team_id, data in team_scores.items():
            team_size = data['team_size']
            data['team_ascent_bonus'] = 0
            calculation_details["team_bonuses"][team_id] = []

            # Check each route to see if the whole team completed it
            for route_id, participants in data['route_completions'].items():
                # Whole team completed this route
                if len(participants) == team_size:
                    # Get the grade of this route to calculate base points
                    route_grade = next((a['grade'] for a in data['ascents']
                                        if a['route_id'] == route_id), None)
                    if route_grade and team_size in team_bonus_config:
                        route_points = await self._get_base_points(route_grade)
                        # Apply bonus for this specific route
                        bonus_factor = team_bonus_config[team_size]
                        bonus_amount = route_points * bonus_factor
                        data['team_ascent_bonus'] += bonus_amount

                        calculation_details["team_bonuses"][team_id].append({
                            "route_id":
                            route_id,
                            "grade":
                            route_grade,
                            "base_points":
                            route_points,
                            "team_size":
                            team_size,
                            "bonus_factor":
                            bonus_factor,
                            "bonus_amount":
                            bonus_amount
                        })

        logger.info("Calculating master grade bonuses")
        # Identify teams with most ascents at each grade for master grade bonus
        grade_leaders = {}  # grade -> (team_id, count)
        calculation_details["grade_leaders"] = {}

        for team_id, data in team_scores.items():
            for grade, count in data['grades_count'].items():
                if grade not in grade_leaders or count > grade_leaders[grade][
                        1]:
                    grade_leaders[grade] = (team_id, count)
                    calculation_details["grade_leaders"][grade] = {
                        "team_id": team_id,
                        "count": count
                    }

        # Apply master grade bonus to teams with most ascents at each grade
        master_grade_config = await self._get_master_grade_bonus_config()
        calculation_details["config"][
            "master_grade_bonus"] = master_grade_config
        calculation_details["master_grade_bonuses"] = {}

        for grade, (leader_team_id, count) in grade_leaders.items():
            if grade in master_grade_config:
                # Apply bonus to the grade leader
                grade_base_points = await self._get_base_points(grade)
                bonus_factor = master_grade_config[grade]
                bonus_amount = grade_base_points * count * bonus_factor
                team_scores[leader_team_id][
                    'master_grade_bonus'] += bonus_amount

                if leader_team_id not in calculation_details[
                        "master_grade_bonuses"]:
                    calculation_details["master_grade_bonuses"][
                        leader_team_id] = []

                calculation_details["master_grade_bonuses"][
                    leader_team_id].append({
                        "grade": grade,
                        "count": count,
                        "base_points": grade_base_points,
                        "bonus_factor": bonus_factor,
                        "bonus_amount": bonus_amount
                    })

                logger.debug(f"Applied master grade bonus for grade {grade} "
                             f"to team {leader_team_id}")

        logger.info("Calculating total scores and normalizing")
        # Calculate total scores and normalize by team size
        rankings = []
        calculation_details["normalization"] = {}

        for team_id, data in team_scores.items():
            team_size = data['team_size']

            # Calculate total score (before normalization)
            unnormalized_total = (data['base_score'] + data['volume_score'] +
                                  data['unique_ascent_score'] +
                                  data['team_ascent_bonus'] +
                                  data['master_grade_bonus'])

            calculation_details["normalization"][team_id] = {
                "team_size": team_size,
                "before_normalization": {
                    "base_score": data['base_score'],
                    "volume_score": data['volume_score'],
                    "unique_ascent_score": data['unique_ascent_score'],
                    "team_ascent_bonus": data['team_ascent_bonus'],
                    "master_grade_bonus": data['master_grade_bonus'],
                    "total_score": unnormalized_total
                }
            }

            # Normalize all scores by team size
            if team_size > 0:
                # Normalize each component
                data['base_score'] /= team_size
                data['volume_score'] /= team_size
                data['unique_ascent_score'] /= team_size
                data['team_ascent_bonus'] /= team_size
                data['master_grade_bonus'] /= team_size
                data['total_score'] = (data['base_score'] +
                                       data['volume_score'] +
                                       data['unique_ascent_score'] +
                                       data['team_ascent_bonus'] +
                                       data['master_grade_bonus'])

                calculation_details["normalization"][team_id][
                    "after_normalization"] = {
                        "base_score": data['base_score'],
                        "volume_score": data['volume_score'],
                        "unique_ascent_score": data['unique_ascent_score'],
                        "team_ascent_bonus": data['team_ascent_bonus'],
                        "master_grade_bonus": data['master_grade_bonus'],
                        "total_score": data['total_score']
                    }

            # Remove the ascents list to make the JSON more manageable
            data_for_ranking = {
                k: v
                for k, v in data.items() if k != 'ascents'
            }
            rankings.append(data_for_ranking)

        # Sort by total score (already normalized)
        rankings.sort(key=lambda x: -x['total_score'])

        # Add ranks
        for i, entry in enumerate(rankings, 1):
            entry['rank'] = i

        logger.info(f"Marathon scoring completed for {len(rankings)} teams")
        return rankings, calculation_details

    async def _calculate_boulder_beasts_scores(self, ascents: List[Dict[str,
                                                                        Any]],
                                               comp_id: str) -> tuple:
        """Calculate scores for the Boulder Beasts category."""
        # Group ascents by participant
        participant_scores = {}

        # Detailed calculation data to save
        calculation_details = {
            "competition_id": comp_id,
            "timestamp": datetime.now().isoformat(),
            "participant_ascents": {},
            "sorted_ascents": {},
            "top_grades": {},
            "score_calculations": {}
        }

        logger.info(
            f"Processing {len(ascents)} ascents for Boulder Beasts scoring")

        for ascent in ascents:
            participant_id = ascent['participant_id']

            # All participants are included in Boulder Beasts category
            if participant_id not in participant_scores:
                participant_scores[participant_id] = {
                    'participant_id': participant_id,
                    'first_name': ascent.get('participants',
                                             {}).get('first_name'),
                    'last_name': ascent.get('participants',
                                            {}).get('last_name'),
                    'team_id':
                    ascent.get('team_id'),  # May be null for solo participants
                    'ascents': [],
                    'top_grades': []
                }

                calculation_details["participant_ascents"][participant_id] = []

            # Store ascent for scoring
            participant_scores[participant_id]['ascents'].append(ascent)

            # Add to detailed calculation data
            calculation_details["participant_ascents"][participant_id].append({
                "ascent_id":
                ascent.get('id'),
                "route_id":
                ascent.get('route_id'),
                "grade":
                ascent.get('grade')
            })

        logger.info(
            f"Processing ascents for {len(participant_scores)} participants")

        # Calculate scores and top grades for each participant
        rankings = []
        for participant_id, data in participant_scores.items():
            # Sort ascents by grade difficulty
            sorted_ascents = sorted(
                data['ascents'],
                key=lambda a: self._grade_to_number(a['grade']),
                reverse=True)

            # Store sorted ascents in detailed data
            calculation_details["sorted_ascents"][participant_id] = [{
                "grade":
                a['grade'],
                "route_id":
                a['route_id']
            } for a in sorted_ascents]

            # Take top 5 grades
            top_grades = [a['grade'] for a in sorted_ascents[:5]]
            data['top_grades'] = top_grades

            calculation_details["top_grades"][participant_id] = top_grades

            # Calculate total score based on top 5 ascents
            score_details = []
            total_score = 0

            for i, ascent in enumerate(sorted_ascents[:5], 1):
                grade = ascent['grade']
                points = await self._get_base_points(grade)
                total_score += points

                score_details.append({
                    "position": i,
                    "grade": grade,
                    "points": points
                })

            data['total_score'] = total_score
            calculation_details["score_calculations"][participant_id] = {
                "ascents": score_details,
                "total_score": total_score
            }

            # Remove the ascents list to make the JSON more manageable
            data_for_ranking = {
                k: v
                for k, v in data.items() if k != 'ascents'
            }
            rankings.append(data_for_ranking)

        # Sort by total score
        rankings.sort(key=lambda x: -x['total_score'])

        # Add ranks
        for i, entry in enumerate(rankings, 1):
            entry['rank'] = i

        logger.info(
            f"Boulder Beasts scoring completed for "
            f"{len(rankings)} participants")
        return rankings, calculation_details

    async def _get_base_points(self, grade: str) -> int:
        """Get base points for a grade from the database."""
        base_points = get_base_points_by_grade(self.session, grade)

        if not base_points:
            logger.warning(
                f"No base points found for grade {grade}, using 0")
            return 0

        return base_points.points

    async def _get_volume_bonus_config(self) -> Dict[str, int]:
        """Get volume bonus configuration from the database."""
        bonuses = get_all_volume_bonuses(self.session)

        if not bonuses:
            logger.warning(
                "No volume bonus configuration found, using defaults")
            return {"bonus_increment": 5, "points_per_increment": 10}

        # Return the first configuration
        bonus = bonuses[0]
        return {
            "bonus_increment": bonus.bonus_increment,
            "points_per_increment": bonus.points_per_increment
        }

    async def _get_team_ascent_bonus_config(self) -> Dict[int, float]:
        """Get team ascent bonus configuration from the database."""
        bonuses = get_all_team_bonuses(self.session)

        if not bonuses:
            logger.warning(
                "No team ascent bonus configuration found, using defaults")
            return {2: 1.1, 3: 1.2, 4: 1.3}

        # Convert to dictionary of team_size -> bonus_factor
        return {bonus.team_size: bonus.bonus_factor for bonus in bonuses}

    async def _get_master_grade_bonus_config(self) -> Dict[str, float]:
        """Get master grade bonus configuration from the database."""
        bonuses = get_all_master_grade_bonuses(self.session)

        if not bonuses:
            logger.warning(
                "No master grade bonus configuration found, using defaults"
            )
            return {"bonus_factor": 1.05}

        # Return the first configuration
        bonus = bonuses[0]
        return {"bonus_factor": bonus.bonus_factor}

    def _grade_to_number(self, grade: str) -> float:
        """
        Convert a climbing grade to a number for easier comparison.

        Example:
            "6A" -> 6.0
            "6A+" -> 6.1
            "6B" -> 6.2
            "6B+" -> 6.3
            "6C" -> 6.4
            ...
            "8C" -> 8.4

        The conversion is based on the French font grading system.
        """
        # Remove '+' and '-' from grade
        base = grade.replace('+', '').replace('-', '')

        # Extract main number and letter
        number = int(base[0])
        letter = base[1]

        # Convert letter to number (A=1, B=2, C=3)
        letter_value = ord(letter) - ord('A') + 1

        # Calculate numeric value
        value = number + (letter_value / 3)

        # Add bonus for '+' grades
        if '+' in grade:
            value += 0.33

        return value

    async def _store_results(
            self, comp_id: str, marathon_scores: List[Dict[str, Any]],
            boulder_beasts_scores: List[Dict[str, Any]]) -> None:
        """Store competition results in the database."""
        # Store Marathon rankings
        if marathon_scores:
            logger.info(
                f"Storing {len(marathon_scores)} Marathon rankings")

            # Process each team's ranking
            for team_score in marathon_scores:
                try:
                    from database.models.scoring import MarathonRanking

                    # Create or update marathon ranking
                    ranking = MarathonRanking(
                        team_id=team_score['team_id'],
                        base_score=team_score['base_score'],
                        volume_score=team_score['volume_score'],
                        unique_ascent_score=team_score[
                            'unique_ascent_score'],
                        team_ascent_bonus=team_score['team_ascent_bonus'],
                        master_grade_bonus=team_score[
                            'master_grade_bonus'],
                        total_score=team_score['total_score'],
                        rank=team_score['rank'])

                    create_marathon_ranking(self.session, ranking)
                except Exception as e:
                    logger.error(
                        f"Error storing Marathon ranking for team "
                        f"{team_score['team_id']}: {str(e)}")

        # Store Boulder Beasts rankings
        if boulder_beasts_scores:
            logger.info(
                f"Storing {len(boulder_beasts_scores)} "
                "Boulder Beasts rankings"
            )

            # Process each participant's ranking
            for participant_score in boulder_beasts_scores:
                try:
                    from database.models.scoring import (
                        BoulderBeastsRanking)

                    # Create or update boulder beasts ranking
                    ranking = BoulderBeastsRanking(
                        participant_id=participant_score['participant_id'],
                        top_grades=participant_score['top_grades'],
                        total_score=participant_score['total_score'],
                        rank=participant_score['rank'])

                    create_boulder_beasts_ranking(self.session, ranking)
                except Exception as e:
                    logger.error(
                        "Error storing Boulder Beasts ranking for "
                        f"participant {participant_score[
                            'participant_id']}: {str(e)}")

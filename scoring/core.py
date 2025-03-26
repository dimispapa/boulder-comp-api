"""
Core scoring functionality for calculating competition scores.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from supabase import Client


class ScoreCalculator:
    """
    Handles score calculations for both Marathon and Boulder Beasts categories.
    """

    def __init__(self, supabase: Client):
        """
        Initialize the score calculator.

        Args:
            supabase (Client): Initialized Supabase client
        """
        self.supabase = supabase

    async def calculate_scores(self, comp_id: str) -> Dict[str, Any]:
        """
        Calculate scores for all participants in both categories.
        
        Args:
            comp_id (str): ID of the competition
            
        Returns:
            dict: Calculated scores and rankings for both categories
        """
        try:
            # Get competition details
            comp = await self._get_competition(comp_id)
            if not comp:
                raise ValueError(f"Competition {comp_id} not found")

            # Get all ascents for this competition
            ascents = await self._get_competition_ascents(comp_id)

            # Calculate Marathon scores if category is enabled
            marathon_scores = []
            if 'marathon' in comp['categories']:
                marathon_scores = await self._calculate_marathon_scores(ascents)

            # Calculate Boulder Beasts scores if category is enabled
            boulder_beasts_scores = []
            if 'boulder_beasts' in comp['categories']:
                boulder_beasts_scores = await self._calculate_boulder_beasts_scores(ascents)

            # Store results in Supabase
            await self._store_results(comp_id, marathon_scores, boulder_beasts_scores)

            return {
                "marathon": marathon_scores,
                "boulder_beasts": boulder_beasts_scores,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            raise Exception(f"Error calculating scores: {str(e)}")

    async def _get_competition(self, comp_id: str) -> Optional[Dict[str, Any]]:
        """Get competition details from Supabase."""
        result = self.supabase.table('competitions').select('*').eq('id', comp_id).execute()

        if not result.data:
            return None

        return result.data[0]

    async def _get_competition_ascents(self, comp_id: str) -> List[Dict[str, Any]]:
        """Get all ascents for a competition with related data."""
        result = self.supabase.table('ascents').select(
            'ascents.*, participants.*, routes.*, teams.*'
        ).eq('competition_id', comp_id).execute()

        return result.data

    async def _calculate_marathon_scores(self, ascents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate scores for the Marathon category."""
        # Group ascents by team
        team_scores = {}

        for ascent in ascents:
            if not ascent.get('team_id'):
                continue

            team_id = ascent['team_id']
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
                    'unique_routes': set()
                }

            # Calculate base points for this ascent
            base_points = await self._get_base_points(ascent['grade'])
            team_scores[team_id]['base_score'] += base_points

            # Track unique ascents
            route_key = f"{ascent['route_id']}"
            if route_key not in team_scores[team_id]['unique_routes']:
                team_scores[team_id]['unique_routes'].add(route_key)
                team_scores[team_id]['unique_ascent_score'] += base_points

            # Store ascent for volume bonus calculation
            team_scores[team_id]['ascents'].append(ascent)

        # Calculate volume bonuses
        volume_bonus_config = await self._get_volume_bonus_config()
        for team_id, data in team_scores.items():
            ascent_count = len(data['ascents'])
            volume_bonus = (ascent_count // volume_bonus_config['bonus_increment']) * \
                          volume_bonus_config['points_per_increment']
            data['volume_score'] = volume_bonus

        # Calculate team ascent bonuses
        team_bonus_config = await self._get_team_ascent_bonus_config()
        for team_id, data in team_scores.items():
            team_size = len(set(a['participant_id'] for a in data['ascents']))
            if team_size in team_bonus_config:
                data['team_ascent_bonus'] = data['base_score'] * team_bonus_config[team_size]

        # Calculate master grade bonus
        master_grade_config = await self._get_master_grade_bonus_config()
        for team_id, data in team_scores.items():
            hardest_grade = max((a['grade'] for a in data['ascents']),
                              key=lambda g: self._grade_to_number(g))
            if hardest_grade in master_grade_config:
                data['master_grade_bonus'] = data['base_score'] * master_grade_config[hardest_grade]

        # Calculate total scores and create rankings
        rankings = []
        for team_id, data in team_scores.items():
            data['total_score'] = (data['base_score'] + data['volume_score'] +
                                 data['unique_ascent_score'] +
                                 data['team_ascent_bonus'] +
                                 data['master_grade_bonus'])
            rankings.append(data)

        # Sort by total score
        rankings.sort(key=lambda x: -x['total_score'])

        # Add ranks
        for i, entry in enumerate(rankings, 1):
            entry['rank'] = i

        return rankings

    async def _calculate_boulder_beasts_scores(self, ascents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate scores for the Boulder Beasts category."""
        # Group ascents by participant
        participant_scores = {}

        for ascent in ascents:
            participant_id = ascent['participant_id']
            
            # Skip if participant is not enrolled in Boulder Beasts
            if not ascent.get('participants', {}).get('boulder_beasts_enrolled'):
                continue

            if participant_id not in participant_scores:
                participant_scores[participant_id] = {
                    'participant_id': participant_id,
                    'first_name': ascent.get('participants', {}).get('first_name'),
                    'last_name': ascent.get('participants', {}).get('last_name'),
                    'ascents': [],
                    'top_grades': []
                }

            # Store ascent for scoring
            participant_scores[participant_id]['ascents'].append(ascent)

        # Calculate scores and top grades for each participant
        rankings = []
        for participant_id, data in participant_scores.items():
            # Sort ascents by grade difficulty
            sorted_ascents = sorted(
                data['ascents'],
                key=lambda a: self._grade_to_number(a['grade']),
                reverse=True)

            # Take top 5 grades
            data['top_grades'] = [a['grade'] for a in sorted_ascents[:5]]

            # Calculate total score based on top 5 ascents
            data['total_score'] = sum(await self._get_base_points(a['grade'])
                                    for a in sorted_ascents[:5])

            rankings.append(data)

        # Sort by total score
        rankings.sort(key=lambda x: -x['total_score'])

        # Add ranks
        for i, entry in enumerate(rankings, 1):
            entry['rank'] = i

        return rankings

    async def _get_base_points(self, grade: str) -> int:
        """Get base points for a grade from the base_points table."""
        result = self.supabase.table('base_points').select('points').eq('grade', grade).execute()

        if not result.data:
            return 0

        return result.data[0]['points']

    async def _get_volume_bonus_config(self) -> Dict[str, int]:
        """Get volume bonus configuration."""
        result = self.supabase.table('volume_bonus').select('*').execute()

        if not result.data:
            return {'bonus_increment': 5, 'points_per_increment': 25}

        return result.data[0]

    async def _get_team_ascent_bonus_config(self) -> Dict[int, float]:
        """Get team ascent bonus configuration."""
        result = self.supabase.table('team_ascent_bonus').select('*').execute()

        if not result.data:
            return {2: 0.10, 3: 0.15, 4: 0.20}

        return {row['team_size']: row['bonus_factor'] for row in result.data}

    async def _get_master_grade_bonus_config(self) -> Dict[str, float]:
        """Get master grade bonus configuration."""
        result = self.supabase.table('master_grade_bonus').select('*').execute()

        if not result.data:
            return {'8A': 0.50, '8A+': 0.75, '8B': 1.00}

        return {row['grade']: row['bonus_factor'] for row in result.data}

    def _grade_to_number(self, grade: str) -> float:
        """Convert grade string to numeric value for comparison."""
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

    async def _store_results(self, comp_id: str, marathon_scores: List[Dict[str, Any]],
                           boulder_beasts_scores: List[Dict[str, Any]]) -> None:
        """Store competition results in Supabase."""
        # Store Marathon rankings
        for rank in marathon_scores:
            marathon_data = {
                'competition_id': comp_id,
                'team_id': rank['team_id'],
                'base_score': rank['base_score'],
                'volume_score': rank['volume_score'],
                'unique_ascent_score': rank['unique_ascent_score'],
                'team_ascent_bonus': rank['team_ascent_bonus'],
                'master_grade_bonus': rank['master_grade_bonus'],
                'total_score': rank['total_score'],
                'rank': rank['rank'],
                'timestamp': datetime.now().isoformat()
            }
            self.supabase.table('marathon_rankings').upsert(marathon_data).execute()

        # Store Boulder Beasts rankings
        for rank in boulder_beasts_scores:
            boulder_beasts_data = {
                'competition_id': comp_id,
                'participant_id': rank['participant_id'],
                'top_grades': rank['top_grades'],
                'total_score': rank['total_score'],
                'rank': rank['rank'],
                'timestamp': datetime.now().isoformat()
            }
            self.supabase.table('boulder_beasts_rankings').upsert(boulder_beasts_data).execute()

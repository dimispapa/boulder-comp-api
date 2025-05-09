"""
Script to export competition participants to Google Sheets.

This includes:
- Solo participants
- Team participants grouped by team

Each competition will have its own Google Sheet.
"""
import os
import sys
from typing import List, Dict, Tuple
from uuid import UUID

# Set up the paths correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(os.path.dirname(parent_dir))

# Add the project root to the path so we can import from the database package
sys.path.append(project_root)

# Add script directories to path
sys.path.append(current_dir)
sys.path.append(parent_dir)

try:
    from gsheets import GoogleSheetsClient
except ImportError:
    from database.gsheets.scripts.gsheets import GoogleSheetsClient

from sqlmodel import Session, select  # noqa: E402
from database.management.base import get_db_session  # noqa: E402
from database.models.competitions import (  # noqa: E402
    Participant, Team,
)
from database.crud.competitions import (  # noqa: E402
    get_participants_by_competition_id, get_competition_by_id,
)


def get_competition_participants(
    session: Session, competition_id: UUID
) -> Tuple[List[Participant], Dict[str, List[Participant]]]:
    """
    Get competition participants grouped by solo and teams.

    Args:
        session: Database session
        competition_id: ID of the competition

    Returns:
        Tuple of solo participants and team participants grouped by team name
    """
    # Get all participants for the competition
    participants = get_participants_by_competition_id(session, competition_id)

    # Get all teams for the competition
    teams = session.exec(
        select(Team).where(Team.competition_id == competition_id)).all()
    teams_dict = {team.id: team for team in teams}

    # Separate solo and team participants
    solo_participants = []
    team_participants_by_team = {}

    for participant in participants:
        if participant.is_solo:
            solo_participants.append(participant)
        elif participant.team_id and participant.team_is_valid:
            if participant.team_id in teams_dict:
                team_name = teams_dict[participant.team_id].name
                if team_name not in team_participants_by_team:
                    team_participants_by_team[team_name] = []
                team_participants_by_team[team_name].append(participant)

    return solo_participants, team_participants_by_team


def prepare_competition_participant_data(
        participants: List[Participant]) -> List[List[str]]:
    """
    Prepare competition participant data for Google Sheets.

    Args:
        participants: List of competition participants

    Returns:
        List of rows for Google Sheets
    """
    # Headers
    headers = ['Full Name', 'Email', 'Signed Waiver', 'Registration Date']

    # Data rows
    rows = [headers]
    for participant in participants:
        user = participant.user
        if user:
            rows.append([
                f"{user.first_name} {user.last_name}", user.email,
                'Yes' if participant.signed_waiver else 'No',
                participant.inserted_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

    return rows


def export_competition_to_sheet(competition_id: UUID):
    """
    Export competition participants to Google Sheets.

    Args:
        competition_id: ID of the competition to export
    """
    # Get environment variables
    credentials_path = os.environ.get('GOOGLE_SHEETS_CREDENTIALS_PATH')
    folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')

    if not credentials_path or not folder_id:
        raise ValueError("Please set GOOGLE_SHEETS_CREDENTIALS_PATH "
                         "and GOOGLE_DRIVE_FOLDER_ID "
                         "environment variables")

    # Make sure credentials path is absolute
    if not os.path.isabs(credentials_path):
        # Try to find the file relative to the project root
        possible_paths = [
            os.path.join(project_root, credentials_path),
            os.path.join(parent_dir, 'creds',
                         os.path.basename(credentials_path)),
            os.path.join(parent_dir, os.path.basename(credentials_path)),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                credentials_path = path
                break

    print(f"Using credentials: {credentials_path}")
    print(f"File exists: {os.path.exists(credentials_path)}")
    print(f"Using folder ID: {folder_id}")

    # Initialize Google Sheets client
    client = GoogleSheetsClient(credentials_path)

    with get_db_session() as session:
        # Get competition info
        competition = get_competition_by_id(session, competition_id)
        if not competition:
            raise ValueError(f"Competition with ID {competition_id} not found")

        spreadsheet_name = f"{competition.display_name}"
        print(f"Looking for spreadsheet: '{spreadsheet_name}'")

        # Find the spreadsheet
        spreadsheet_id = client.get_spreadsheet_id_by_name(
            folder_id, spreadsheet_name)
        if not spreadsheet_id:
            print(f"Could not find spreadsheet '{spreadsheet_name}' in the "
                  f"specified folder. Make sure it exists.")
            return

        # Get participants
        solo_participants, team_participants_by_team = (
            get_competition_participants(session, competition_id))

        # Export solo participants
        solo_rows = prepare_competition_participant_data(solo_participants)
        client.write_data(spreadsheet_id, "Solo Participants!A1", solo_rows)
        print(f"Exported {len(solo_participants)} solo participants")

        # Export team participants
        for team_name, participants in team_participants_by_team.items():
            sheet_name = f"Team - {team_name}"
            team_rows = prepare_competition_participant_data(participants)
            client.write_data(spreadsheet_id, f"{sheet_name}!A1", team_rows)
            print(f"Exported {len(participants)} participants for team "
                  f"'{team_name}'")


def main():
    """Main entry point for script."""
    # Get competition ID from environment variable
    competition_id_str = os.environ.get('COMPETITION_ID')
    if not competition_id_str:
        raise ValueError("Please set COMPETITION_ID environment variable")

    competition_id = UUID(competition_id_str)
    export_competition_to_sheet(competition_id)


if __name__ == "__main__":
    main()

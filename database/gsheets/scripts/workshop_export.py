"""
Script to export workshop participants to Google Sheets.

Each workshop will be exported to a separate Google Sheet.
"""
import os
import sys
from typing import List

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

from database.management.base import get_db_session  # noqa: E402
from database.models.workshops import WorkshopParticipant  # noqa: E402
from database.crud.workshops import (  # noqa: E402
    get_participants_by_workshop,
    get_workshop_by_name,
)


def prepare_workshop_participant_data(
        participants: List[WorkshopParticipant]) -> List[List[str]]:
    """
    Prepare workshop participant data for Google Sheets.

    Args:
        participants: List of workshop participants

    Returns:
        List of rows for Google Sheets
    """
    # Headers
    headers = [
        'Full Name', 'Email', 'Phone', 'Age', 'Notes', 'Signed Waiver',
        'Registration Date'
    ]

    # Data rows
    rows = [headers]
    for participant in participants:
        rows.append([
            participant.full_name, participant.email, participant.phone or '',
            str(participant.age) if participant.age else '', participant.notes
            or '', 'Yes' if participant.signed_waiver else 'No',
            participant.inserted_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return rows


def export_workshops_to_sheets():
    """Export each workshop's participants to a separate Google Sheet."""
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

    # Get workshop participants grouped by workshop
    with get_db_session() as session:
        participants_by_workshop = get_participants_by_workshop(session)

        if not participants_by_workshop:
            print("No workshop participants found in the database.")
            return

        # Also get the workshop display names for better sheet names
        workshop_display_names = {}
        for workshop_name in participants_by_workshop:
            workshop = get_workshop_by_name(session, workshop_name)
            if workshop:
                workshop_display_names[workshop_name] = workshop.display_name

        # Export each workshop to a separate sheet
        for workshop_name, participants in participants_by_workshop.items():
            # Use display name for the spreadsheet if available
            display_name = workshop_display_names.get(workshop_name,
                                                      workshop_name)
            spreadsheet_name = f"{display_name}"

            print(f"Looking for spreadsheet: '{spreadsheet_name}'")

            # Find or create the spreadsheet
            spreadsheet_id = client.get_spreadsheet_id_by_name(
                folder_id, spreadsheet_name)
            if not spreadsheet_id:
                print(
                    f"Could not find spreadsheet '{spreadsheet_name}' in the "
                    f"specified folder. Make sure it exists.")
                continue

            # Prepare and write data
            rows = prepare_workshop_participant_data(participants)
            client.write_data(spreadsheet_id, "Participants!A1", rows)

            print(f"Exported {len(participants)} participants for workshop "
                  f"'{display_name}'")


if __name__ == "__main__":
    export_workshops_to_sheets()

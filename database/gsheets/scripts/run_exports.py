"""
Main script to run both workshop and competition exports to Google Sheets.

Required Environment Variables:
- GOOGLE_SHEETS_CREDENTIALS_PATH: Path to the Google Sheets
service account credentials JSON file
- GOOGLE_DRIVE_FOLDER_ID: ID of the Google Drive folder
containing the spreadsheets
- COMPETITION_ID: (Optional) UUID of the competition to export participants for

For each workshop, a separate Google Sheet named "Workshop -
{display_name}" should exist.
For the competition, a Google Sheet named "Competition - {display_name}"
should exist.
These sheets will be populated with participant data.
"""
import os
import sys
import argparse
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

# Import our export modules directly from the current directory
import workshop_export  # noqa: E402
import competition_export  # noqa: E402


def main():
    """Main entry point for running all exports."""
    parser = argparse.ArgumentParser(
        description='Export workshop and competition participants to '
        'Google Sheets.')
    parser.add_argument('--workshops-only',
                        action='store_true',
                        help='Export only workshop participants')
    parser.add_argument('--comp-only',
                        action='store_true',
                        help='Export only competition participants')
    parser.add_argument('--debug',
                        action='store_true',
                        help='Show additional debug information')

    args = parser.parse_args()

    # Determine what to export
    export_workshops = not args.comp_only
    export_competition = not args.workshops_only

    if args.debug:
        print(f"Current directory: {os.getcwd()}")
        print(f"Script directory: {current_dir}")
        print(f"Parent directory: {parent_dir}")
        print(f"Project root: {project_root}")
        print(f"PYTHONPATH: {sys.path}")

    # Check environment variables
    credentials_path = os.environ.get('GOOGLE_SHEETS_CREDENTIALS_PATH')
    folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')

    if not credentials_path or not folder_id:
        raise ValueError("Please set GOOGLE_SHEETS_CREDENTIALS_PATH "
                         "and GOOGLE_DRIVE_FOLDER_ID "
                         "environment variables")

    # Export workshops if needed
    if export_workshops:
        print("\n=== Exporting Workshop Participants ===")
        workshop_export.export_workshops_to_sheets()

    # Export competition if needed
    if export_competition:
        print("\n=== Exporting Competition Participants ===")
        competition_id_str = os.environ.get('COMPETITION_ID')
        if not competition_id_str:
            print("Warning: COMPETITION_ID environment variable not set. "
                  "Skipping competition export.")
        else:
            try:
                competition_id = UUID(competition_id_str)
                competition_export.export_competition_to_sheet(competition_id)
            except ValueError as e:
                print(f"Error exporting competition participants: {str(e)}")

    print("\n=== Export Complete ===")


if __name__ == "__main__":
    main()

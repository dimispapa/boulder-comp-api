from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from typing import List, Any, Optional


class GoogleSheetsClient:
    """Client for interacting with Google Sheets API."""

    def __init__(self, credentials_path: str):
        """Initialize the Google Sheets client.

        Args:
            credentials_path: Path to the service account credentials JSON file
        """
        self.credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.readonly'
            ])
        self.sheets_service = build('sheets',
                                    'v4',
                                    credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)

    def get_spreadsheet_id_by_name(self, folder_id: str,
                                   name: str) -> Optional[str]:
        """Get spreadsheet ID by its name in a specific folder.

        Args:
            folder_id: Google Drive folder ID
            name: Name of the spreadsheet

        Returns:
            str: Spreadsheet ID if found, None otherwise
        """
        query = f"name = '{name}' and '{folder_id}' in parents and " \
                "mimeType = 'application/vnd.google-apps.spreadsheet'"
        results = self.drive_service.files().list(
            q=query, spaces='drive', fields='files(id, name)').execute()

        files = results.get('files', [])
        return files[0]['id'] if files else None

    def ensure_sheet_exists(self, spreadsheet_id: str, sheet_name: str):
        """Ensure a sheet with the given name exists in the spreadsheet."""
        try:
            # Get all sheets in the spreadsheet
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id).execute()

            # Check if sheet exists
            sheet_exists = any(sheet['properties']['title'] == sheet_name
                               for sheet in spreadsheet['sheets'])

            if not sheet_exists:
                # Add new sheet
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': sheet_name
                                }
                            }
                        }]
                    }).execute()
        except Exception as e:
            raise Exception(f"Error ensuring sheet exists: {str(e)}")

    def write_data(self,
                   spreadsheet_id: str,
                   range_name: str,
                   values: List[List[Any]],
                   clear: bool = True):
        """Write data to a spreadsheet.

        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to write to (e.g. 'Sheet1!A1')
            values: 2D array of values to write
            clear: Whether to clear the range before writing
        """
        # Ensure the sheet exists
        sheet_name = range_name.split('!')[0].replace("'", "")
        self.ensure_sheet_exists(spreadsheet_id, sheet_name)

        if clear:
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id, range=range_name).execute()

        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body={
                'values': values
            }).execute()

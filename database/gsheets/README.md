# Google Sheets Export Scripts

These scripts export workshop and competition participants data to Google Sheets.

## Setup

1. **Create Google Cloud Project and Enable APIs**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Sheets API and Google Drive API
   - Create a service account with appropriate permissions
   - Download the service account credentials JSON file and save it as `boulder-fest-f8c0318def6d.json` in the `database/gsheets/creds` directory

2. **Create Google Sheets**:
   - For each workshop: Create a Google Sheet with the same name as the workshop's display name 
     (e.g., "Intro to Outdoor Bouldering – Adults (18+)")
   - For the competition: Create a Google Sheet named `Competition - {competition_display_name}`
   - Put all these sheets in a single Google Drive folder
   - Share each sheet with the service account email (give it Editor permissions)

3. **Get Google Drive Folder ID**:
   - Open your Google Drive folder in a browser
   - The URL will look like: `https://drive.google.com/drive/folders/1AbCdEfG123456789`
   - The folder ID is the part after `/folders/` (in this example, `1AbCdEfG123456789`)

4. **Set Environment Variables**:
   - Create a `.env.gsheets` file in the `database/gsheets` directory with the following content:
     ```
     # Google Drive folder ID where the spreadsheets are located
     GOOGLE_DRIVE_FOLDER_ID="your_folder_id_here"
     
     # ID of the competition to export participants for
     COMPETITION_ID="your_competition_id_here"
     ```

## Usage

Run the export scripts using the provided shell script:

```bash
cd database/gsheets/scripts
./export_to_sheets.sh
```

### Options

- `--workshops-only`: Export only workshop participants
- `--comp-only`: Export only competition participants
- `--competition-id <UUID>`: Specify a competition ID (overrides the one in .env.gsheets)
- `--debug`: Show additional debug information

Examples:
```bash
# Export only workshops
./export_to_sheets.sh --workshops-only

# Export only competition with debug info
./export_to_sheets.sh --comp-only --competition-id <UUID> --debug
```

## Output

The scripts will:

1. For each workshop, update a sheet with participant data including:
   - Full Name, Email, Phone, Age, Notes, Signed Waiver, Registration Date

2. For the competition:
   - Create a "Solo Participants" sheet with solo participants
   - Create a separate sheet for each team with its participants
   - Include: Full Name, Email, Signed Waiver, Registration Date

Each time you run the scripts, they will refresh the data in the Google Sheets with the latest information from the database.

## Sheet Structure

Workshop sheets should have a tab named "Participants" where the data will be written.

Competition sheets should have:
- A tab named "Solo Participants" for solo participants
- Additional tabs named "Team - {team_name}" for each team

## Troubleshooting

If you encounter any issues:

1. **Credentials File Not Found**:
   - Make sure your credentials file is in `database/gsheets/creds/boulder-fest-f8c0318def6d.json`
   - Alternatively, set the `CREDENTIALS_PATH` environment variable to the absolute path of your credentials file

2. **Folder ID Issues**:
   - Verify that `GOOGLE_DRIVE_FOLDER_ID` is set correctly
   - Make sure the folder exists and the service account has access to it

3. **Spreadsheet Not Found**:
   - Ensure the Google Sheets exist in the specified folder
   - Check that the spreadsheet names match exactly with the workshop display names
   - Make sure the service account has edit access to the sheets

4. **Authentication Issues**:
   - Verify the service account has the necessary permissions
   - Check that the Google Sheets API and Google Drive API are enabled
   - Make sure the credentials file is properly formatted and contains all required fields

Use the `--debug` flag to see more detailed information about the execution process. 
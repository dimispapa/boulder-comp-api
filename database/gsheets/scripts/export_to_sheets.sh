#!/bin/bash
# Script to export participants data to Google Sheets

# Change to the script directory
cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$PARENT_DIR")")"

# Try multiple possible locations for credentials
POSSIBLE_PATHS=(
  "$PARENT_DIR/creds/boulder-fest-f8c0318def6d.json"
  "$PARENT_DIR/boulder-fest-f8c0318def6d.json"
  "$PROJECT_ROOT/database/gsheets/creds/boulder-fest-f8c0318def6d.json"
  "$PROJECT_ROOT/database/gsheets/boulder-fest-f8c0318def6d.json"
  "$CREDENTIALS_PATH"  # Use environment variable if set
)

FOUND_CREDENTIALS=false
for path in "${POSSIBLE_PATHS[@]}"; do
  if [ -n "$path" ] && [ -f "$path" ]; then
    CREDENTIALS_PATH="$path"
    FOUND_CREDENTIALS=true
    echo "Found credentials at: $CREDENTIALS_PATH"
    break
  fi
done

if [ "$FOUND_CREDENTIALS" = false ]; then
  echo "Error: Could not find credentials file in any of the following locations:"
  for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -n "$path" ]; then
      echo "  - $path"
    fi
  done
  echo "Please place your credentials file in one of these locations or set CREDENTIALS_PATH environment variable."
  exit 1
fi

GSHEETS_ENV_FILE="$PARENT_DIR/.env.gsheets"

# Load environment variables if the file exists
if [ -f "$GSHEETS_ENV_FILE" ]; then
    source "$GSHEETS_ENV_FILE"
    echo "Loaded environment variables from $GSHEETS_ENV_FILE"
fi

# Set environment variables (always use the absolute path we found)
export GOOGLE_SHEETS_CREDENTIALS_PATH="$CREDENTIALS_PATH"
echo "Set GOOGLE_SHEETS_CREDENTIALS_PATH to $GOOGLE_SHEETS_CREDENTIALS_PATH"

if [ -z "$GOOGLE_DRIVE_FOLDER_ID" ]; then
    echo "Error: GOOGLE_DRIVE_FOLDER_ID environment variable not set"
    echo "Please set it in $GSHEETS_ENV_FILE or export it manually"
    exit 1
fi

# Output debug info
echo "SCRIPT_DIR: $SCRIPT_DIR"
echo "PARENT_DIR: $PARENT_DIR"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "CREDENTIALS_PATH: $CREDENTIALS_PATH"
echo "GOOGLE_SHEETS_CREDENTIALS_PATH: $GOOGLE_SHEETS_CREDENTIALS_PATH"
echo "GOOGLE_DRIVE_FOLDER_ID: $GOOGLE_DRIVE_FOLDER_ID"

# Parse command line arguments
WORKSHOPS_ONLY=false
COMP_ONLY=false
DEBUG=false
PYTHON_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --workshops-only)
            WORKSHOPS_ONLY=true
            PYTHON_ARGS="$PYTHON_ARGS $1"
            shift
            ;;
        --comp-only)
            COMP_ONLY=true
            PYTHON_ARGS="$PYTHON_ARGS $1"
            shift
            ;;
        --debug)
            DEBUG=true
            PYTHON_ARGS="$PYTHON_ARGS $1"
            shift
            ;;
        --competition-id)
            export COMPETITION_ID="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run the export script with the appropriate arguments
if [ "$WORKSHOPS_ONLY" = true ]; then
    python run_exports.py $PYTHON_ARGS
elif [ "$COMP_ONLY" = true ]; then
    if [ -z "$COMPETITION_ID" ]; then
        echo "Error: --comp-only requires --competition-id"
        exit 1
    fi
    python run_exports.py $PYTHON_ARGS
else
    # Run both exports
    if [ -z "$COMPETITION_ID" ]; then
        echo "Warning: COMPETITION_ID not set, will only export workshops"
        python run_exports.py --workshops-only $PYTHON_ARGS
    else
        python run_exports.py $PYTHON_ARGS
    fi
fi 
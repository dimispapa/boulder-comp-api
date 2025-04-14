#!/bin/bash
# Setup script to ensure data directories exist with proper permissions

DATA_DIR="/app/data"
SCRAPED_DIR="$DATA_DIR/scraped"

# Create data directories
mkdir -p $SCRAPED_DIR

# Set permissions (ensure the user running the application has access)
chmod -R 777 $DATA_DIR

echo "Directory structure verified:"
echo "============================"
ls -la $DATA_DIR
ls -la $SCRAPED_DIR
echo "============================"

# Print environment information
echo "Current working directory: $(pwd)"
echo "User running process: $(whoami)"
echo "User ID: $(id -u)"
echo "Group ID: $(id -g)"

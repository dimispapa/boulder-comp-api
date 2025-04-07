# Testing the Scoring Calculator API

This guide explains how to use the provided mock competition data and test script to verify the scoring calculator functionality in the Boulder Competition API.

## Overview

The scoring system supports two competition categories:
1. **Marathon** - Team-based scoring
2. **Boulder Beasts** - Individual-based scoring

The provided files help you create mock data and test the API endpoints.

## Files Included

1. `mock_competition_data.sql` - SQL script to create mock competition data
2. `test_scoring_api.py` - Python script to test the scoring API endpoints

## Step 1: Load Mock Competition Data

First, you need to insert the mock competition data into your database:

```bash
# Connect to your database (using psql or another PostgreSQL client)
psql -U your_username -d your_database -f mock_competition_data.sql
```

This will:
- Create a test competition with ID `00000000-aaaa-bbbb-cccc-000000000001`
- Create 4 teams with different sizes and participant configurations
- Create 15 participants (12 in teams, 3 solo entries)
- Generate realistic ascent data with various climbing grades
- Create a diverse dataset ideal for testing both scoring categories

## Step 2: Test the Scoring Calculator API

Use the provided Python script to test the scoring calculator API:

```bash
# Make the script executable
chmod +x test_scoring_api.py

# Run a complete test with all API endpoints
./test_scoring_api.py --url http://localhost:8000/api

# Test only a specific category
./test_scoring_api.py --url http://localhost:8000/api --category marathon

# Test only a specific endpoint
./test_scoring_api.py --url http://localhost:8000/api --task calculate
```

### Available Options

The test script supports several options:

- `--url`: Base URL of the API (default: http://localhost:8000/api)
- `--comp-id`: Competition ID to use (default: 00000000-aaaa-bbbb-cccc-000000000001)
- `--category`: Calculate scores for a specific category only (marathon or boulder_beasts)
- `--task`: Specific API task to test (calculate, status, rankings, leaderboard, all)
- `--task-id`: Task ID for checking status (required when using --task=status)

## API Endpoints Tested

The script tests the following API endpoints:

1. `/scoring/calculate/{comp_id}` - Trigger score calculation
2. `/scoring/status/{task_id}` - Check calculation task status
3. `/scoring/rankings/{comp_id}` - Get raw ranking data
4. `/scoring/leaderboard/{comp_id}` - Get formatted leaderboard data

## Expected Results

If everything is working correctly, you should see:

1. A successful score calculation with a task ID
2. Task status updates until completion
3. Rankings data showing teams and individual participants with their scores
4. Formatted leaderboard data for display

The mock data is designed to test various aspects of the scoring system:
- Teams of different sizes (2-4 members)
- Diverse climbing grades (from easy to very difficult)
- Different climbing volume patterns
- Several solo entries (for Boulder Beasts category)
- Different team strategies (volume-focused vs. difficulty-focused)

## Troubleshooting

If you encounter issues:

1. Check that your API server is running
2. Verify database connection settings
3. Ensure the mock data was properly loaded
4. Check API server logs for any errors
5. Verify that routes with the specified grades exist in your database

### Common Issues

- **Database connection errors**: Make sure your database is accessible and the connection string is correctly configured in `.env`.
- **"'_GeneratorContextManager' object has no attribute 'get'"**: This can occur if the wrong database session manager is used in FastAPI dependencies. The application uses `get_db()` for FastAPI endpoints and `get_db_session()` for context-managed blocks.
- **Celery task execution issues**: The scoring calculation uses async code executed within an event loop in Celery tasks. Check Celery worker logs for detailed error information.
- **Calculation timeouts**: For large competitions, calculations might take longer than expected. Consider increasing timeout settings if calculations are being terminated prematurely.

## Notes on the Mock Data

The mock data creates a realistic competition scenario:

- **Rock Stars**: A balanced team with some high-grade climbs
- **Boulder Crushers**: A volume-focused team with many ascents
- **Gravity Defiers**: A small team focused on difficult climbs
- **Chalk Monsters**: A balanced team with diverse climbing abilities
- **Solo entries**: Three individuals with varying skill levels

This diversity helps test all aspects of the scoring algorithm. 
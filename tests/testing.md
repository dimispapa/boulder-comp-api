# Testing Information

This directory contains tests for the Boulder Competition API project.

## Test Structure

- `tests/api/` - API endpoint tests
  - `test_general.py` - Basic API tests like the root endpoint
  - `test_scraper.py` - Tests for scraper API endpoints 
  - `test_media.py` - Tests for media upload API endpoints
  - `conftest.py` - Pytest configuration and fixtures for API tests
- `tests/scraper/` - Scraper functionality tests
  - `test_playwright.py` - Tests for Playwright login and data extraction
  - `test_standard_request.py` - Tests for standard HTTP request login and data extraction
  - `test_script_extraction.py` - Tests for script tag extraction methods
  - `test_extract_boulder.py` - Tests for boulder data extraction
  - `conftest.py` - Pytest configuration and fixtures for scraper tests

## Recent Updates

The test suite has been updated to:

1. Support the new database schema that includes:
   - Crags and sectors relationships
   - Boulder-sector mappings 
   - Both name (URL-friendly) and display_name (human-readable) fields for entities

2. Remove Redis dependency:
   - Tests previously requiring Redis now use mocking
   - All tests can run in any environment without external dependencies

## Running Tests

Run all tests (all tests should now pass without Redis):
```bash
python -m pytest
```

Run only API tests:
```bash
python -m pytest tests/api/
```

Run only scraper tests:
```bash
python -m pytest tests/scraper/
```

Run with verbose output:
```bash
python -m pytest -v tests/api/
```

## Test Configuration

The `pytest.ini` file in the project root configures pytest with:
- Test markers to categorize different test types
- Default path configurations 

### Test Markers

- `api`: Tests for API endpoints
- `xfail`: Tests expected to fail

> Note: The `redis` marker is no longer necessary as tests have been refactored to use mocks instead of requiring Redis.

## Mocking

The test suite uses several mocking strategies:

1. **Celery Tasks**: Mock implementations prevent actual task execution
   while verifying proper API behavior.

2. **Redis**: All Redis-dependent functionality is now mocked, making the test suite
   independent of Redis availability.

3. **File System**: File operations use mocks to avoid filesystem dependencies.

4. **Database**: Sector mappings and other database operations are mocked with
   appropriate test data reflecting the new schema.

## Debug Files and Cache

For scraper tests, test runs create debug HTML files in the `tests/scraper/debug/` 
directory that capture the state of pages during test execution. This directory
is excluded from version control (.gitignore) and Docker builds (.dockerignore).

The following test-related files and directories are also excluded:
- `.pytest_cache/` - Pytest cache directory
- `__pycache__/` - Python bytecode cache directories
- `.coverage` - Coverage data files
- `htmlcov/` - HTML coverage report directory 

## File Organization

All test files are now properly organized in the tests directory structure.
No test files should be present in the project root directory. 
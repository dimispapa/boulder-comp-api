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

## Running Tests

Run all tests:
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

Run including Redis-dependent tests:
```bash
python -m pytest --override-ini=addopts=
```

Run only Redis-dependent tests:
```bash
python -m pytest -k "redis" --override-ini=addopts=
```

## Test Configuration

The `pytest.ini` file in the project root configures pytest with:
- Test markers to categorize different test types
- Default path configurations 
- Exclusion of Redis-dependent tests by default

### Test Markers

- `api`: Tests for API endpoints
- `redis`: Tests that require Redis to be running
- `xfail`: Tests expected to fail

## Mocking

The test suite uses several mocking strategies:

1. **Celery Tasks**: Mock implementations prevent actual task execution
   while verifying proper API behavior.

2. **Redis**: Tests with the `redis` marker handle both Redis availability and
   connection errors gracefully.

3. **File System**: File operations use mocks to avoid filesystem dependencies.

## Debug Files

For scraper tests, test runs create debug HTML files in the `tests/scraper/debug/` 
directory that capture the state of pages during test execution.

## File Organization

All test files are now properly organized in the tests directory structure.
No test files should be present in the project root directory. 
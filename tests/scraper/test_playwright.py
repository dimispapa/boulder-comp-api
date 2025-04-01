"""
Test script to verify Playwright functionality with persistent sessions.
Fetches a premium topo page with JavaScript execution while maintaining
login state.
"""
import os
import json
import pytest
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from utils.playwright_utils import PlaywrightSession
from utils.loggers import logger

# Load environment variables
load_dotenv()


@pytest.mark.asyncio
async def test_with_persistent_session():
    """Test fetching premium topo pages
    using a persistent session with login."""
    # Get credentials from environment
    username = os.environ.get("CRAGS_USERNAME")
    password = os.environ.get("CRAGS_PASSWORD")
    domain = os.environ.get("CRAGS_DOMAIN", "https://27crags.com/")

    # URLs and login config
    login_url = domain + "login"
    boulder_url = domain + "crags/inia-droushia/premiumtopos/arkham"

    # Basic headers
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    }

    # Selectors for login
    login_selectors = {
        "username_field": 'input[name="web_user[username]"]',
        "password_field": 'input[name="web_user[password]"]',
        "submit_button": 'input[type="submit"]',
        "success_indicator": 'body.user-logged',
        "failure_indicator": 'a[href="/login"]'
    }

    # Credentials
    creds = {"username": username, "password": password}

    # Initialize session
    session = PlaywrightSession()

    try:
        # Initialize the session with headers
        await session.initialize(headers)
        logger.info("Initialized Playwright session")

        # Perform login
        logger.info(f"Logging in to {login_url}...")
        login_success = await session.login(login_url, creds, login_selectors)

        # Verify login was successful
        assert login_success, "Login failed"
        logger.info("Login successful. Session is now authenticated.")

        # Fetch the boulder page with the same session
        logger.info(f"Fetching boulder page: {boulder_url}")

        # Wait for topo-image or topo-image-container
        content = await session.get_content(
            boulder_url,
            wait_for_selector='.topo-image, .topo-image-container',
            wait_timeout=15000)

        logger.info(f"Retrieved content length: {len(content)}")

        # Save for examination (only in development)
        debug_file = "tests/scraper/debug/playwright_debug.html"
        os.makedirs(os.path.dirname(debug_file), exist_ok=True)
        with open(debug_file, "w") as f:
            f.write(content)
        logger.info(f"Saved content to {debug_file}")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, 'html5lib')

        # Check login status
        body = soup.find('body')
        assert body and 'user-logged' in body.get('class', []), "Not logged in"
        logger.info("Page shows logged-in status")

        # Check for topo images and scripts
        topo_images = soup.find_all('div', class_='topo-image')
        js_data_scripts = soup.find_all('script', class_='js-data')

        # Verify we have the expected content
        assert len(topo_images) > 0, "No topo images found"
        assert len(js_data_scripts) > 0, "No js-data scripts found"

        logger.info(f"Found {len(topo_images)} topo images")
        logger.info(f"Found {len(js_data_scripts)} js-data scripts")

        # Check script data
        has_valid_json = False
        for script in js_data_scripts:
            script_text = script.string if script.string else ""
            if script_text:
                try:
                    data = json.loads(script_text)
                    if 'lines' in data:
                        has_valid_json = True
                        break
                except json.JSONDecodeError:
                    continue

        assert has_valid_json, "No valid JSON with lines data found"
        logger.info("Found valid JSON data with lines")

    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        raise

    finally:
        # Close the session
        await session.close()
        logger.info("Closed Playwright session")

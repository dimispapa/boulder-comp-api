"""
Test script to fetch HTML using standard HTTP requests
(no JavaScript rendering).
Verifies authentication and script data extraction.
"""
import os
import json
import pytest
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from utils.loggers import logger
from scraper.auth_utils import standard_login

# Load environment variables
load_dotenv()


@pytest.mark.asyncio
async def test_standard_request():
    """Test fetching data with standard HTTP requests after authentication."""
    # Set up test data
    domain = os.environ.get("CRAGS_DOMAIN", "https://27crags.com/")
    boulder_url = domain + "crags/inia-droushia/premiumtopos/arkham"

    # Basic headers
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        # First, login to get authenticated session
        login_success = await standard_login(domain, headers, session, None)
        assert login_success, "Login failed"
        logger.info("Login successful")

        # Fetch the boulder page with the same session
        logger.info(f"Fetching boulder page: {boulder_url}")

        async with session.get(boulder_url) as response:
            html_content = await response.text()
            logger.info(f"Retrieved content length: {len(html_content)}")

            # Save for examination (only in development)
            debug_file = "tests/scraper/debug/standard_request_debug.html"
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, "w") as f:
                f.write(html_content)
            logger.info(f"Saved content to {debug_file}")

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html5lib')

            # Check login status
            body = soup.find('body')
            assert body and 'user-logged' in body.get('class',
                                                      []), "Not logged in"
            logger.info("Page shows logged-in status")

            # Check for topo images and scripts
            topo_images = soup.find_all('div', class_='topo-image')
            js_data_scripts = soup.find_all('script', class_='js-data')

            # Verify we have the expected content
            assert len(topo_images) > 0, "No topo images found"
            assert len(js_data_scripts) > 0, "No js-data scripts found"

            logger.info(f"Found {len(topo_images)} topo images")
            logger.info(f"Found {len(js_data_scripts)} js-data scripts")

            # Test for valid JSON in scripts
            has_valid_json = False
            for script in js_data_scripts:
                # Test different extraction methods
                for method_name, get_content in {
                        "string attribute":
                        lambda s: s.string if s.string else "",
                        "text attribute":
                        lambda s: s.text.strip(),
                        "get_text()":
                        lambda s: s.get_text().strip(),
                        "contents[0]":
                        lambda s: str(s.contents[0]).strip()
                        if s.contents else ""
                }.items():
                    content = get_content(script)
                    if not content:
                        continue

                    try:
                        data = json.loads(content)
                        if 'lines' in data:
                            logger.info(
                                f"Found valid JSON with lines using "
                                f"{method_name}")
                            has_valid_json = True
                            break
                    except json.JSONDecodeError:
                        continue

                if has_valid_json:
                    break

            assert has_valid_json, "No valid JSON with lines data found"
            logger.info(
                "Successfully extracted data from standard HTTP request")

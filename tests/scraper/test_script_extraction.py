"""
Test to verify script data extraction from HTML.
This is a static test that doesn't require HTTP requests.
"""
import json
import os
from bs4 import BeautifulSoup
from utils.loggers import logger


def test_script_extraction():
    """Test different methods of extracting script data from HTML."""
    try:
        # Set up paths
        debug_dir = "tests/scraper/debug"
        os.makedirs(debug_dir, exist_ok=True)

        # Try loading saved HTML from the recommended debug location
        html_file = f"{debug_dir}/playwright_debug.html"

        # If debug file doesn't exist, just skip the test
        if not os.path.exists(html_file):
            logger.info(f"Test HTML file not found: {html_file}")
            # This will be marked as skipped in pytest
            import pytest
            pytest.skip("Test HTML file not found")
            return

        # Load the HTML content
        with open(html_file, 'r') as f:
            html_content = f.read()

        logger.info(f"Loaded HTML file, size: {len(html_content)} bytes")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html5lib')

        # Find all script elements with js-data class
        js_data_scripts = soup.find_all('script', class_='js-data')
        logger.info(f"Found {len(js_data_scripts)} js-data scripts")

        # We should have found some scripts
        assert len(js_data_scripts) > 0, "No script elements found"

        # Test different methods of extracting the script content
        extraction_methods = {
            "string attribute": 0,
            "text attribute": 0,
            "get_text()": 0,
            "contents[0]": 0
        }

        valid_json_count = {
            "string attribute": 0,
            "text attribute": 0,
            "get_text()": 0,
            "contents[0]": 0
        }

        for script in js_data_scripts:
            # Method 1: Using the string attribute
            # (what we use with Playwright)
            string_content = script.string if script.string else ""
            if string_content:
                extraction_methods["string attribute"] += 1

                try:
                    data = json.loads(string_content)
                    valid_json_count["string attribute"] += 1
                    if 'lines' in data:
                        # This is the expected result
                        # - we should have found lines
                        pass
                except json.JSONDecodeError:
                    pass

            # Method 2: Using the text attribute
            # (what we used originally)
            text_content = script.text.strip()
            if text_content:
                extraction_methods["text attribute"] += 1

                try:
                    data = json.loads(text_content)
                    valid_json_count["text attribute"] += 1
                except json.JSONDecodeError:
                    pass

            # Method 3: Using get_text()
            get_text_content = script.get_text().strip()
            if get_text_content:
                extraction_methods["get_text()"] += 1

                try:
                    data = json.loads(get_text_content)
                    valid_json_count["get_text()"] += 1
                except json.JSONDecodeError:
                    pass

            # Method 4: Using contents[0] if available
            if script.contents:
                contents_content = str(script.contents[0]).strip()
                if contents_content:
                    extraction_methods["contents[0]"] += 1

                    try:
                        data = json.loads(contents_content)
                        valid_json_count["contents[0]"] += 1
                    except json.JSONDecodeError:
                        pass

        # Verify that we found at least one valid JSON with one method
        assert sum(valid_json_count.values()
                   ) > 0, "No valid JSON found with any method"

        # Log the results
        logger.info("\nExtraction method results:")
        for method, count in extraction_methods.items():
            logger.info(
                f"{method}: {count} non-empty, "
                f"{valid_json_count[method]} valid JSON"
            )

    except Exception as e:
        logger.error(f"Error during test: {e}")
        raise

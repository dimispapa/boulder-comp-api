"""
Utility functions for handling JavaScript-rendered pages using Playwright.
Provides browser automation to retrieve fully rendered HTML from dynamic
websites.
"""
from typing import Dict, Tuple, Any
from playwright.async_api import async_playwright, Page, Browser
import os
import asyncio
import random
import datetime
import json

from utils.loggers import logger


async def get_html_with_js(url: str,
                           headers: Dict[str, str] = None,
                           script_selector: str = 'script.js-data',
                           wait_timeout: int = 10000) -> str:
    """
    Get fully rendered HTML content after JavaScript execution
    using Playwright.

    Args:
        url (str): URL to fetch
        headers (Dict[str, str], optional): HTTP headers for the request
        script_selector (str): CSS selector to wait for
                               (default: 'script.js-data')
        wait_timeout (int): Maximum time to wait for selector in milliseconds

    Returns:
        str: HTML content after JavaScript execution
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()

            # Set headers if provided
            if headers:
                await page.set_extra_http_headers(headers)

            # Go to the URL and wait for navigation
            await page.goto(url)

            try:
                # Wait for the script element with data to be populated
                # Use a more specific selector that checks
                # for non-empty content
                await page.wait_for_selector(f'{script_selector}:not(:empty)',
                                             timeout=wait_timeout)
                logger.debug(f"Script element found and loaded for {url}")
            except Exception as e:
                logger.warning(
                    f"Timeout waiting for script element on {url}: {str(e)}")
                # Continue anyway, as the page might be loaded
                # without the script

            # Get the page content
            content = await page.content()
            logger.debug(
                f"Successfully retrieved JS-rendered content for {url}")
            return content

        except Exception as e:
            logger.error(
                f"Error getting JS-rendered content for {url}: {str(e)}")
            raise
        finally:
            await browser.close()


async def setup_browser() -> Tuple[Any, Browser, Page]:
    """
    Set up a Playwright browser instance that can be reused.

    Returns:
        Tuple: Playwright instance, Browser, and Page objects
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch()
    page = await browser.new_page()
    return playwright, browser, page


async def close_browser(playwright: Any, browser: Browser) -> None:
    """
    Close browser and playwright instances.

    Args:
        playwright: Playwright instance
        browser: Browser instance
    """
    await browser.close()
    await playwright.stop()


async def get_page_with_js(page: Page,
                           url: str,
                           script_selector: str = 'script.js-data',
                           wait_timeout: int = 10000) -> str:
    """
    Get fully rendered page content using an existing Page instance.

    Args:
        page (Page): Playwright Page instance
        url (str): URL to fetch
        script_selector (str): CSS selector to wait for
        wait_timeout (int): Maximum time to wait for selector in milliseconds

    Returns:
        str: HTML content after JavaScript execution
    """
    try:
        # Go to the URL and wait for navigation
        await page.goto(url)

        try:
            # Wait for the script element with data to be populated
            await page.wait_for_selector(f'{script_selector}:not(:empty)',
                                         timeout=wait_timeout)
            logger.debug(f"Script element found and loaded for {url}")
        except Exception as e:
            logger.warning(
                f"Timeout waiting for script element on {url}: {str(e)}")

        # Get the page content
        content = await page.content()
        logger.debug(f"Successfully retrieved JS-rendered content for {url}")
        return content

    except Exception as e:
        logger.error(f"Error getting JS-rendered content for {url}: {str(e)}")
        raise


class PlaywrightSession:
    """A class to manage a persistent Playwright browser session."""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_initialized = False

    async def initialize(self, headers: Dict[str, str] = None):
        """Initialize the Playwright session with a persistent context."""
        if self.is_initialized:
            return

        self.playwright = await async_playwright().start()

        # Add user data directory for persistent storage
        user_data_dir = "/tmp/playwright_user_data"
        os.makedirs(user_data_dir, exist_ok=True)

        # Implement user agent rotation
        user_agents = []
        for i in range(1, 6):  # Check for USER_AGENT_1 through USER_AGENT_5
            agent = os.environ.get(f"USER_AGENT_{i}")
            if agent:
                user_agents.append(agent)

        # Select a random user agent or use a default if none are defined
        user_agent = random.choice(user_agents) if user_agents else (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

        logger.debug(f"Using user agent: {user_agent}")

        # Slight variations in viewport size
        width = 1280 + random.randint(-20, 20)
        height = 800 + random.randint(-10, 10)

        # Launch with persistent context
        self.browser = await self.playwright.chromium.launch()
        self.context = await self.browser.new_context(
            viewport={
                'width': width,
                'height': height
            },
            user_agent=user_agent,
            locale="en-US",
            timezone_id="Europe/London",
            color_scheme="light",
            storage_state=os.path.join(
                user_data_dir, "storage.json") if os.path.exists(
                    os.path.join(user_data_dir, "storage.json")) else None)

        # Add default headers if provided
        if headers:
            await self.context.set_extra_http_headers(headers)

        # Create a default page
        self.page = await self.context.new_page()
        self.is_initialized = True

        # Save cookies and storage after successful initialization
        async def save_storage():
            state = await self.context.storage_state()
            # Create timestamp-based storage files
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            storage_path = os.path.join(user_data_dir,
                                        f"storage_{timestamp}.json")
            # Save to both the timestamped and the standard file
            with open(storage_path, 'w') as f:
                f.write(json.dumps(state))
            await self.context.storage_state(
                path=os.path.join(user_data_dir, "storage.json"))

        # Set up event listener to save storage on successful authentication
        self.context.on("page",
                        lambda page: asyncio.create_task(save_storage()))

        logger.debug("PlaywrightSession initialized successfully")

    async def login(self, login_url: str, credentials: Dict[str, str],
                    selectors: Dict[str, str]):
        """
        Perform login on the given URL using the provided credentials
        and selectors.

        Args:
            login_url: URL of the login page
            credentials: Dictionary with username and password keys
            selectors: Dictionary with selectors for username_field,
                       password_field, and submit_button

        Returns:
            bool: True if login appears successful, False otherwise
        """
        if not self.is_initialized:
            logger.error("Playwright session not initialized")
            return False

        try:
            # Navigate to login page
            await self.page.goto(login_url)

            # Wait for page to fully load - add this
            await self.page.wait_for_load_state('networkidle')

            # Check if we're already logged in
            already_logged = await self.page.query_selector('body.user-logged')
            if already_logged:
                logger.info("Already logged in, no need to re-authenticate")
                return True

            # Wait for the login form to be available - add this
            try:
                await self.page.wait_for_selector(selectors['username_field'],
                                                  timeout=5000)
            except Exception as e:
                logger.warning(f"Could not find username field: {str(e)}")
                # Try to locate any username field as fallback
                username_fields = await self.page.query_selector_all(
                    'input[type="text"]')
                if not username_fields:
                    logger.error("No text input fields found on login page")
                    # Take a screenshot for debugging
                    await self.page.screenshot(path="/app/login_error.png")
                    return False

            # Fill username and password
            if 'username_field' in selectors and 'username' in credentials:
                await self.page.fill(selectors['username_field'],
                                     credentials['username'])

            if 'password_field' in selectors and 'password' in credentials:
                await self.page.fill(selectors['password_field'],
                                     credentials['password'])

            # Click submit button
            if 'submit_button' in selectors:
                await self.page.click(selectors['submit_button'])
                await self.page.wait_for_load_state('networkidle')

            # Check login success based on provided success_indicator
            if 'success_indicator' in selectors:
                try:
                    await self.page.wait_for_selector(
                        selectors['success_indicator'], timeout=5000)
                    logger.info("Login successful via success indicator")
                    return True
                except Exception:
                    logger.warning("Login indicator not found")

                    # If we have a failure indicator, check for that
                    if 'failure_indicator' in selectors:
                        failure = await self.page.query_selector(
                            selectors['failure_indicator'])
                        if failure:
                            logger.warning(
                                "Login failed - failure indicator found")
                            return False

            # Check URL - often a successful login
            # redirects away from login page
            current_url = self.page.url
            if '/login' not in current_url:
                logger.info("Login appears successful "
                            "(redirected from login page)")
                return True

            # Default to assume login failed
            logger.warning("Login status uncertain, assuming failed")
            return False

        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False

    async def get_content(self,
                          url: str,
                          wait_for_selector: str = None,
                          wait_timeout: int = 10000) -> str:
        """
        Navigate to URL and get rendered content.

        Args:
            url: URL to navigate to
            wait_for_selector: Optional selector to wait for
            wait_timeout: Timeout in ms for selector waiting

        Returns:
            str: HTML content of the page
        """
        if not self.is_initialized:
            logger.error("Playwright session not initialized")
            raise RuntimeError("Playwright session not initialized")

        try:
            # Navigate to page
            await self.page.goto(url)
            await self.page.wait_for_load_state('networkidle')

            # Wait for specific selector if provided
            if wait_for_selector:
                try:
                    await self.page.wait_for_selector(wait_for_selector,
                                                      timeout=wait_timeout)
                except Exception as e:
                    logger.warning(
                        f"Timeout waiting for selector '{wait_for_selector}': "
                        f"{str(e)}")

            # Return the page content
            return await self.page.content()

        except Exception as e:
            logger.error(f"Error getting page content for {url}: {str(e)}")
            raise

    async def close(self):
        """Close all browser resources."""
        if not self.is_initialized:
            return

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

        self.is_initialized = False
        logger.debug("PlaywrightSession closed")

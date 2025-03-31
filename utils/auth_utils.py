"""
Authentication utilities for interacting with 27crags.com.
Handles login, session management, and authentication checks.
"""
import os
from bs4 import BeautifulSoup
import aiohttp
from urllib.parse import urljoin
from dotenv import load_dotenv
from utils.loggers import logger

# Load environment variables
load_dotenv()


async def perform_login(domain: str,
                        headers: dict,
                        async_session: aiohttp.ClientSession,
                        rate_limit_func=None) -> bool:
    """
    Core login functionality for 27crags.com using credentials
    from environment variables.

    This is used by the CragScraper class but contains the core login logic.

    Args:
        domain (str): Base domain for the site
        headers (dict): HTTP headers for requests
        async_session (aiohttp.ClientSession): Active session
        rate_limit_func (callable, optional): Function to call
        for rate limiting

    Returns:
        bool: True if login successful, False otherwise
    """
    try:
        # Get credentials from environment
        username = os.environ.get("CRAGS_USERNAME")
        password = os.environ.get("CRAGS_PASSWORD")

        # Validate credentials
        if not username or not password:
            logger.error("Missing credentials for login")
            return False

        login_url = urljoin(domain, "login")
        # Get login page
        if rate_limit_func:
            await rate_limit_func()
        logger.debug("Attempting to log in")

        async with async_session.get(login_url) as response:
            if response.status != 200:
                logger.error(f"Failed to load login page. Status code: "
                             f"{response.status}")
                return False

            login_page_content = await response.text()

        # Parse login page
        soup = BeautifulSoup(login_page_content, 'html5lib')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if not csrf_meta:
            logger.error("Could not find CSRF token meta tag")
            return False

        # Get CSRF token from meta tag
        csrf_token = csrf_meta.get('content')
        if not csrf_token:
            logger.error("Could not find CSRF token meta tag")
            return False

        logger.debug(f"Got CSRF token: {csrf_token[:10]}...")

        # Prepare login data
        login_data = {
            'authenticity_token': csrf_token,
            'web_user[username]': username,
            'web_user[password]': password,
            'web_user[remember_me]': '1'
        }

        # Enhanced headers for login
        enhanced_headers = {
            **headers, 'Accept':
            'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,*/*;q=0.8',
            'Content-Type':
            'application/x-www-form-urlencoded',
            'X-CSRF-Token':
            csrf_token
        }

        # Perform login
        if rate_limit_func:
            await rate_limit_func()
        async with async_session.post(login_url,
                                      data=login_data,
                                      headers=enhanced_headers,
                                      allow_redirects=True) as response:
            response_content = await response.text()
            response_url = str(response.url)

        # Check login success
        soup = BeautifulSoup(response_content, 'html5lib')
        login_successful = not check_requires_authentication(soup)

        # For additional verification, check traditional indicators
        if not login_successful:
            # Fallback checks
            login_successful = any([
                # Check for dashboard redirect
                "/" in response_url,
                # Check for user menu elements
                soup.find('div', class_='user-menu') is not None,
                # Check for logout link
                soup.find('a', href='/logout') is not None
            ])

        logger.info(f"Login {'successful' if login_successful else 'failed'}")
        return login_successful

    except Exception as e:
        logger.error(f"Failed during login: {str(e)}")
        return False


def check_requires_authentication(soup: BeautifulSoup) -> bool:
    """
    Core function to check if a page requires authentication based
    on its content.

    This is used by the CragScraper class but contains the core
    authentication check logic.

    Args:
        soup (BeautifulSoup): Parsed HTML page

    Returns:
        bool: True if authentication is required, False otherwise
    """
    # Check for sign-in link in the navigation
    sign_in_links = soup.find_all('a', href='/login')
    for link in sign_in_links:
        if "Sign in" in link.text:
            logger.debug("Page requires authentication: 'Sign in' link found")
            return True

    # Check for logged-in body class
    if not soup.find('body', class_='user-logged'):
        logger.debug(
            "Page requires authentication: No 'user-logged' body class")
        return True

    # Check for premium content locked messaging
    premium_locked = soup.find('div', class_='premium-content-locked')
    if premium_locked:
        logger.debug("Page requires authentication: Premium content is locked")
        return True

    # Page appears to be accessible
    return False

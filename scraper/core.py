"""
Core scraping functionality for 27crags.com.
Handles authentication, rate limiting, and data extraction.
"""
import json
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
import time
import os
from typing import Dict, Optional
from supabase import Client
from urllib.parse import urljoin
from dotenv import load_dotenv
import random

from utils.loggers import logger
from .models import Crag, Boulder, Route

# Load environment variables
load_dotenv()


class CragScraper:
    """
    A class to handle scraping data from 27crags.com.
    Includes rate limiting, authentication, and data extraction.
    """

    def __init__(self, headers: Dict[str, str], supabase: Client):
        """
        Initialize the scraper with headers and Supabase client.

        Args:
            headers (dict): HTTP headers for requests
            supabase (Client): Initialized Supabase client
        """
        self.headers = headers
        self.supabase = supabase
        self.session = requests.Session()
        self.is_authenticated = False
        self.last_request_time = 0
        self.batch_size = 3
        self.batch_delay = 0.1
        self.domain = os.getenv("CRAGS_DOMAIN")
        self.login_url = urljoin(self.domain, "login")

        # Configuration
        self.min_request_interval = float(
            os.getenv("MIN_REQUEST_INTERVAL", "1.7"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "5"))
        # Add lock for rate limiting
        self._rate_limit_lock = asyncio.Lock()

    def _rate_limit(self) -> None:
        """Ensures requests are spaced out by at least min_request_interval."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    async def _async_rate_limit(self) -> None:
        """Async version of rate limiting with randomization."""
        async with self._rate_limit_lock:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            base_delay = self.min_request_interval

            # Add randomness to the delay (±30%)
            jitter = base_delay * 0.3 * (2 * random.random() - 1)
            delay = max(0, base_delay + jitter - time_since_last_request)

            if delay > 0:
                await asyncio.sleep(delay)
            self.last_request_time = time.time()

    def login(self, username: str, password: str) -> bool:
        """
        Login to 27crags.com using provided credentials.

        Args:
            username (str): 27crags username
            password (str): 27crags password

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Get login page
            self._rate_limit()
            logger.debug("Attempting to get login page")
            login_page = self.session.get(self.login_url, headers=self.headers)

            # Return False if login page is not loaded
            if login_page.status_code != 200:
                logger.error(f"Failed to load login page. Status code: "
                             f"{login_page.status_code}")
                return False
            # Log login page response status and headers
            logger.debug(
                f"Login page response status: {login_page.status_code}")
            logger.debug(f"Login page response headers: {login_page.headers}")

            # Parse login page
            soup = BeautifulSoup(login_page.content, 'html5lib')
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
            logger.debug("Prepared login data")

            # Enhanced headers for login
            enhanced_headers = {
                **self.headers, 'Accept':
                ('text/html,application/xhtml+xml,application/xml;'
                 'q=0.9,*/*;q=0.8'),
                'Content-Type':
                'application/x-www-form-urlencoded',
                'X-CSRF-Token':
                csrf_token
            }
            logger.debug("Enhanced headers prepared")

            # Perform login
            self._rate_limit()
            response = self.session.post(self.login_url,
                                         data=login_data,
                                         headers=enhanced_headers,
                                         allow_redirects=True)
            logger.debug(f"Login response status: {response.status_code}")
            logger.debug(f"Login response URL: {response.url}")

            # Check login success
            soup = BeautifulSoup(response.content, 'html5lib')
            # Check multiple indicators of successful login
            is_logged_in = any([
                # Check for dashboard redirect to home page
                "/" in response.url,
                # Check for logged-in body class
                soup.find('body', class_='user-logged') is not None,
                # Check for user menu elements
                soup.find('div', class_='user-menu') is not None,
                # Check for logout link
                soup.find('a', href='/logout') is not None
            ])

            self.is_authenticated = is_logged_in
            logger.debug(f"Login successful: {is_logged_in}")
            return is_logged_in

        except Exception as e:
            logger.error(f"Failed to get login page: {str(e)}")
            return False

    async def get_html(self, url: str,
                       async_session: aiohttp.ClientSession) -> BeautifulSoup:
        """
        Async version of get_html with retry logic.

        Args:
            url (str): URL to fetch
            session (aiohttp.ClientSession): Active aiohttp session

        Returns:
            BeautifulSoup: Parsed HTML content

        Raises:
            Exception: If request fails after max retries
        """
        for attempt in range(self.max_retries):
            try:
                await self._async_rate_limit()

                if attempt > 0:
                    logger.debug(
                        f"Retry attempt {attempt} of {self.max_retries-1}...")

                async with async_session.get(url,
                                             headers=self.headers) as response:
                    if response.status == 429:
                        wait_time = int(
                            response.headers.get('Retry-After',
                                                 self.retry_delay))
                        logger.debug(f"Rate limit reached. Waiting {wait_time}"
                                     " seconds...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    content = await response.text()
                    return BeautifulSoup(content, 'html5lib')

            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Failed to fetch data after {self.max_retries}"
                        " attempts.")
                    raise Exception(f"Failed to fetch {url}: {str(e)}")

                # Exponential backoff with randomization
                wait_time = self.retry_delay * (2**attempt)
                # Add jitter (±20%)
                jitter = wait_time * 0.2 * (2 * random.random() - 1)
                wait_time = max(1, wait_time + jitter)

                logger.debug(
                    f"Request failed. Retrying in {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)

        raise Exception(
            f"Failed to fetch {url} after {self.max_retries} attempts")

    async def get_json_html(
            self, url: str,
            async_session: aiohttp.ClientSession) -> BeautifulSoup:
        """
        Async version of get_json_html.

        Args:
            url (str): URL to fetch
            session (aiohttp.ClientSession): Active aiohttp session

        Returns:
            BeautifulSoup: Parsed HTML content
        """
        await self._async_rate_limit()
        async with async_session.get(url, headers=self.headers) as response:
            content = await response.text()
            additional_ascents_json = json.loads(content)
            additional_ascents_html = additional_ascents_json['ticks']
            return BeautifulSoup(additional_ascents_html, 'html5lib')

    async def scrape_crag(self, crag_url: str, progress_callback=None) -> Crag:
        """
        Scrape all boulder data from a crag page.

        Args:
            crag_url (str): URL of the crag to scrape
            progress_callback: Optional function to call with progress updates

        Returns:
            Crag: A Crag object containing all scraped data
        """
        # Initialize skipped_boulders here
        skipped_boulders = []
        # Track start time for elapsed time calculation
        start_time = time.time()

        async with aiohttp.ClientSession(
                headers=self.headers) as async_session:
            try:
                # Get crag name
                crag_name = crag_url.split('/')[-1]
                logger.debug(f"Crag name: {crag_name}")
                logger.debug(f"Crag URL: {crag_url}")
                route_list_url = urljoin(crag_url + "/", "routelist")
                logger.debug(f"Route list URL: {route_list_url}")

                # Use session throughout
                soup = await self.get_html(route_list_url, async_session)

                # locate anchor elements with "sector-item" class.
                # These contain the boulder pages,
                # exclude the first one which is a combined list of all routes
                boulder_elements = soup.find_all(
                    'a', attrs={'class': 'sector-item'})[1:]
                total_boulders = len(boulder_elements)
                logger.info(f"Found {total_boulders} boulders on {crag_url}")

                # After finding total_boulders:
                if progress_callback:
                    elapsed_seconds = time.time() - start_time
                    progress_callback({
                        'total_boulders': total_boulders,
                        'completed_boulders': 0,
                        'elapsed_seconds': int(elapsed_seconds),
                        'status': 'in_progress'
                    })

                # Process boulders in batches
                boulders = []
                batch_size = self.batch_size
                completed_boulders = 0

                for i in range(0, total_boulders, batch_size):
                    batch = boulder_elements[i:i + batch_size]
                    for boulder_element in batch:
                        # Extract URL before processing boulder
                        boulder_url = urljoin(self.domain,
                                              boulder_element['href'])

                        # Extract boulder data
                        boulder = await self._extract_boulder_data(
                            boulder_element, async_session)
                        if boulder:  # Only append valid boulders
                            boulders.append(boulder)
                        else:
                            skipped_boulders.append(boulder_url)
                            logger.warning(
                                "No sector mapping found for boulder: "
                                f"{boulder_url}")
                            continue

                    # Add delay between batches
                    await asyncio.sleep(self.batch_delay)
                    completed_boulders += len(batch)
                    elapsed_seconds = time.time() - start_time
                    logger.info(
                        f"Completed {completed_boulders} of {total_boulders} "
                        f"boulders on {crag_url} (elapsed: "
                        f"{int(elapsed_seconds)}s)")

                    # After updating completed_boulders:
                    if progress_callback:
                        progress_callback({
                            'total_boulders':
                            total_boulders,
                            'completed_boulders':
                            completed_boulders,
                            'elapsed_seconds':
                            int(elapsed_seconds),
                            'status':
                            'in_progress'
                        })

                # Create and return Crag object
                return Crag(name=crag_name, boulders=boulders)

            except Exception as e:
                logger.error(f"Error scraping crag: {str(e)}")
                return {"success": False, "skipped_boulders": skipped_boulders}

    async def _extract_boulder_data(
            self, boulder_element: BeautifulSoup,
            async_session: aiohttp.ClientSession) -> Optional[Boulder]:
        """
        Extract data from a boulder element.

        Args:
            boulder_element (BeautifulSoup): HTML element containing boulder
            data
            session (aiohttp.ClientSession): Active aiohttp session

        Returns:
            Optional[Boulder]: Boulder object if successful, None otherwise
        """
        try:
            # Extract boulder URL from anchor element
            boulder_url = urljoin(self.domain, boulder_element['href'])
            if not boulder_url:
                logger.error(f"No boulder link found for {boulder_element}")
                return None

            # Get the boulder name
            boulder_name = boulder_element.find('div', attrs={
                'class': 'name'
            }).text.strip()

            # Get the boulder page
            boulder_page = await self.get_html(boulder_url, async_session)

            # Get the GPS lat, lon string
            gps_string = boulder_page.find(
                'a', class_=['sector-property',
                             'copytoclipboard']).get('data-href').strip()

            # Convert to postgis point
            lat, lon = map(float, gps_string.split(','))
            gps_postgis = f'POINT({lon} {lat})'

            # Process routes in batches
            routes = []
            routes_table_tbody = boulder_page.find('tbody')
            tr_elements = routes_table_tbody.find_all('tr')
            batch_size = self.batch_size
            processed_count = 0

            for i in range(0, len(tr_elements), batch_size):
                batch = tr_elements[i:i + batch_size]

                for tr_element in batch:
                    route = await self._extract_route_data(
                        tr_element, async_session)
                    if route:
                        routes.append(route)

                processed_count += 1
                await asyncio.sleep(self.batch_delay)

            # Create and return Boulder object
            return Boulder(name=boulder_name,
                           url=boulder_url,
                           gps_postgis=gps_postgis,
                           gps_string=gps_string,
                           routes=routes)

        except Exception as e:
            logger.error(f"Error extracting boulder data: {str(e)}")
            return None

    async def _extract_route_data(
            self, route_element: BeautifulSoup,
            async_session: aiohttp.ClientSession) -> Optional[Route]:
        """
        Extract data from a route element.

        Args:
            route_element (BeautifulSoup): HTML element containing route data

        Returns:
            Optional[Route]: Route object if successful, None otherwise
        """
        try:
            # Get the full URL for the route page
            anchor = route_element.find('a')
            if not anchor:
                logger.error("No anchor element found in route")
                return None

            # Extract route URL and name
            route_url = urljoin(self.domain, anchor['href'])
            route_name = anchor.text.strip()

            # Extract grade
            grade_element = route_element.find('span',
                                               attrs={'class': 'grade'})
            if not grade_element:
                logger.error(f"No grade found for route: {route_name}")
                return None
            grade = grade_element.text.strip().upper()

            # Validate essential data
            if not all([route_url, route_name, grade]):
                logger.error(f"Missing required route data for {route_url}")
                return None

            # Extract rating
            rating = route_element.find('div', attrs={
                'class': 'rating'
            }).text.strip()

            # Get route page
            route_page = await self.get_html(route_url, async_session)
            # Get the route description
            route_description = route_page.find('div',
                                                attrs={
                                                    'class': 'route-info'
                                                }).text.strip()

            # Create and return Route object
            return Route(name=route_name,
                         url=route_url,
                         grade=grade,
                         rating=rating,
                         description=route_description)

        except Exception as e:
            logger.error(f"Error extracting route data: {str(e)}")
            return None

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

from utils.loggers import logger
from .models import Crag, Boulder, Route
from utils.sector_boulder_map import create_mappings_from_excel


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
        self.base_url = "https://27crags.com"
        self.login_url = "https://27crags.com/login"

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
        """Async version of rate limiting."""
        async with self._rate_limit_lock:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval -
                                    time_since_last_request)
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
                       session: aiohttp.ClientSession) -> BeautifulSoup:
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

                async with session.get(url, headers=self.headers) as response:
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

                logger.debug(f"Request failed. Retrying in {self.retry_delay}"
                             " seconds...")
                await asyncio.sleep(self.retry_delay)

        raise Exception(
            f"Failed to fetch {url} after {self.max_retries} attempts")

    async def get_json_html(self, url: str,
                            session: aiohttp.ClientSession) -> BeautifulSoup:
        """
        Async version of get_json_html.

        Args:
            url (str): URL to fetch
            session (aiohttp.ClientSession): Active aiohttp session

        Returns:
            BeautifulSoup: Parsed HTML content
        """
        await self._async_rate_limit()
        async with session.get(url, headers=self.headers) as response:
            content = await response.text()
            additional_ascents_json = json.loads(content)
            additional_ascents_html = additional_ascents_json['ticks']
            return BeautifulSoup(additional_ascents_html, 'html5lib')

    async def scrape_crag(self, crag_url: str) -> Crag:
        """
        Scrape all boulder data from a crag page.

        Args:
            crag_url (str): URL of the crag to scrape

        Returns:
            Crag: A Crag object containing all scraped data
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                # Get crag name
                crag_name = crag_url.split('/')[-1]
                route_list_url = f"{crag_url}/routelist"

                # Use session throughout
                soup = await self.get_html(route_list_url, session)

                # locate anchor elements with "sector-item" class.
                # These contain the boulder pages,
                # exclude the first one which is a combined list of all routes
                boulder_elements = soup.find_all(
                    'a', attrs={'class': 'sector-item'})[1:]
                total_boulders = len(boulder_elements)
                logger.info(f"Found {total_boulders} boulders on {crag_url}")

                # Process boulders in batches
                boulders = []
                batch_size = self.batch_size
                completed_boulders = 0
                skipped_boulders = []

                for i in range(0, total_boulders, batch_size):
                    batch = boulder_elements[i:i + batch_size]
                    for boulder_element in batch:
                        # Extract boulder data
                        boulder = await self._extract_boulder_data(
                            boulder_element, self.session)
                        if boulder:  # Only append valid boulders
                            boulders.append(boulder)
                        else:
                            skipped_boulders.append(boulder.url)
                            logger.warning(
                                "No sector mapping found for boulder: "
                                f"{boulder.url}")
                            continue

                    # Add delay between batches
                    await asyncio.sleep(self.batch_delay)
                    completed_boulders += len(batch)
                    logger.info(
                        f"Completed {completed_boulders} of {total_boulders}"
                        f" boulders on {crag_url}")

                # Create and return Crag object
                return Crag(name=crag_name, boulders=boulders)

            except Exception as e:
                logger.error(f"Error scraping crag: {str(e)}")
                return {"success": False, "skipped_boulders": skipped_boulders}

    async def _extract_boulder_data(
            self, boulder_element: BeautifulSoup,
            session: aiohttp.ClientSession) -> Optional[Boulder]:
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
            boulder_url = urljoin(self.base_url, boulder_element['href'])
            if not boulder_url:
                logger.error(f"No boulder link found for {boulder_element}")
                return None

            # Get the boulder name
            boulder_name = boulder_element.find('div', attrs={
                'class': 'name'
            }).text.strip()

            # Get the boulder page
            boulder_page = await self.get_html(boulder_url, self.session)

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
                        tr_element, self.session)
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
            session: aiohttp.ClientSession) -> Optional[Route]:
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
            route_url = urljoin(self.base_url, anchor['href'])
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
            route_page = await self.get_html(route_url, self.session)
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

    async def _get_sector_mappings(self) -> Dict[str, str]:
        """
        Fetch boulder-sector mappings from Supabase.

        Returns:
            Dict[str, str]: Dictionary mapping boulder URLs to sector IDs
        """
        try:
            result = await create_mappings_from_excel(
                self.supabase, "data/boulder_sector_mappings.xlsx")

            # Create mapping dictionary
            return {
                item['boulder_url']: item['sector_id']
                for item in result.data
            }

        except Exception as e:
            logger.error(f"Error fetching sector mappings: {str(e)}")
            raise

    async def _store_data_in_supabase(self, crag: Crag) -> None:
        """
        Store the scraped data in Supabase tables.

        Args:
            crag (Crag): Crag object containing all scraped data
        """
        try:
            # Get sector mappings
            sector_mappings = await self._get_sector_mappings()

            # Store boulders
            for boulder in crag.boulders:
                # Get sector ID from mapping
                sector_id = sector_mappings.get(boulder.url)
                if not sector_id:
                    logger.warning(
                        f"No sector mapping found for boulder: {boulder.url}")
                    continue

                # Start transaction
                async with self.supabase.pool.acquire() as connection:
                    async with connection.transaction():
                        # Insert boulder
                        boulder_data = {
                            'sector_id': sector_id,
                            **boulder.to_supabase_dict()
                        }
                        result = await connection.table('boulders').upsert(
                            boulder_data,
                            on_conflict='url').execute()
                        boulder_id = result.data[0]['id']

                        # Insert routes within same transaction
                        for route in boulder.routes:
                            route_data = {
                                'boulder_id': boulder_id,
                                **route.to_supabase_dict()
                            }
                            await connection.table('routes').upsert(
                                route_data,
                                on_conflict='url').execute()

        except Exception as e:
            logger.error(f"Error in transaction storing data in Supabase: "
                         f"{str(e)}")
            raise

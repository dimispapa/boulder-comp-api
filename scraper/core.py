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
from typing import Dict, Optional, List
from supabase import Client
from urllib.parse import urljoin
from dotenv import load_dotenv
import random

from utils.general_utils import normalize_url
from utils.loggers import logger
from .models import Crag, Boulder, Route, BoulderPhoto, RouteLineData
from utils.auth_utils import perform_login, check_requires_authentication

# Load environment variables
load_dotenv()


class CragScraper:
    """
    A class to handle scraping data from 27crags.com.
    Includes rate limiting, authentication, and data extraction.
    """

    def __init__(self, headers: Dict[str, str], supabase: Client,
                 crag_name: str):
        """
        Initialize the scraper with headers and Supabase client.

        Args:
            headers (dict): HTTP headers for requests
            supabase (Client): Initialized Supabase client
            crag_name (str): Name of the crag to scrape
        """
        self.headers = headers
        self.supabase = supabase
        self.session = requests.Session()
        self.last_request_time = 0
        self.batch_size = 3
        self.batch_delay = 0.1
        self.domain = os.getenv("CRAGS_DOMAIN")
        self.login_url = urljoin(self.domain, "login")
        self.crag_name = crag_name
        self.crag_url = urljoin(self.domain, f"crags/{crag_name}")

        # Configuration
        self.min_request_interval = float(
            os.getenv("MIN_REQUEST_INTERVAL", "1.7"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "5"))
        # Add lock for rate limiting
        self._rate_limit_lock = asyncio.Lock()

    async def _rate_limit(self) -> None:
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

    async def login(self, async_session: aiohttp.ClientSession = None) -> bool:
        """
        Login to 27crags.com using credentials from environment variables.

        Args:
            async_session (aiohttp.ClientSession, optional): Active session

        Returns:
            bool: True if login successful, False otherwise
        """
        return await perform_login(self.domain, self.headers, async_session,
                                   self._rate_limit)

    def requires_authentication(self, soup: BeautifulSoup) -> bool:
        """
        Check if a page requires authentication based on its content.

        Args:
            soup (BeautifulSoup): Parsed HTML page

        Returns:
            bool: True if authentication is required, False otherwise
        """
        return check_requires_authentication(soup)

    async def get_html(self, url: str,
                       async_session: aiohttp.ClientSession) -> BeautifulSoup:
        """
        Async version of get_html with retry logic and authentication handling.

        Args:
            url (str): URL to fetch
            async_session (aiohttp.ClientSession): Active aiohttp session

        Returns:
            BeautifulSoup: Parsed HTML content

        Raises:
            Exception: If request fails after max retries
        """
        for attempt in range(self.max_retries):
            try:
                await self._rate_limit()

                if attempt > 0:
                    logger.debug(
                        f"Retry attempt {attempt} of {self.max_retries-1}...")

                async with async_session.get(url,
                                             headers=self.headers) as response:
                    if response.status == 429:
                        wait_time = int(
                            response.headers.get('Retry-After',
                                                 self.retry_delay))
                        logger.debug(
                            f"Rate limit reached. Waiting {wait_time} "
                            "seconds...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html5lib')

                    # Check if page requires authentication
                    if self.requires_authentication(soup):
                        logger.warning(f"Page requires authentication: {url}")

                        # Attempt to login
                        if await self.login(async_session):
                            logger.info(
                                "Successfully logged in, retrying request")
                            # Don't count this as an attempt, just re-request
                            return await self.get_html(url, async_session)
                        else:
                            logger.error(
                                "Authentication failed, returning page as-is")

                    return soup

            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Failed to fetch data after {self.max_retries} "
                        "attempts.")
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

    async def scrape_crag(self, progress_callback=None) -> Crag:
        """
        Scrape all boulder data from a crag page.

        Args:
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

                login_result = await self.login(async_session)
                logger.info("Initial login "
                            f"{'successful' if login_result else 'failed'}")

                # Continue with the rest of the scraping process
                # get_html will handle authentication challenges automatically

                # Get crag route list
                route_list_url = urljoin(self.crag_url + "/", "routelist")
                logger.debug(f"Fetching route list: {route_list_url}")

                # Use session throughout
                soup = await self.get_html(route_list_url, async_session)

                # locate anchor elements with "sector-item" class.
                # These contain the boulder pages,
                # exclude the first one which is a combined list of all routes
                boulder_elements = soup.find_all(
                    'a', attrs={'class': 'sector-item'})[1:]
                total_boulders = len(boulder_elements)
                logger.info(
                    f"Found {total_boulders} boulders on {self.crag_url}")

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
                        boulder_url = normalize_url(boulder_url)
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
                        f"boulders on {self.crag_url} (elapsed: "
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
                return Crag(name=self.crag_name, boulders=boulders)

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

            # Get the boulder name and boulder url name
            boulder_name = boulder_element.find('div', attrs={
                'class': 'name'
            }).text.strip()
            boulder_url_name = boulder_element['href'].split('/')[-1]
            # Get the boulder page
            boulder_page = await self.get_html(boulder_url, async_session)

            # Get the GPS lat, lon string
            gps_string = boulder_page.find(
                'a', class_=['sector-property',
                             'copytoclipboard']).get('data-href').strip()

            # Convert to postgis point
            lat, lon = map(float, gps_string.split(','))
            gps_postgis = f'POINT({lon} {lat})'

            # Go to the boulder premium page and get the image and lines
            premium_topo_url = urljoin(self.crag_url + "/",
                                       f"premiumtopos/{boulder_url_name}")
            logger.debug(f"Fetching premium topo page for boulder "
                         f"'{boulder_name}': {premium_topo_url}")
            boulder_premium_page = await self.get_html(premium_topo_url,
                                                       async_session)

            # Log the found topo images
            img_divs = boulder_premium_page.find_all('div',
                                                     class_='topo-image')
            logger.debug(f"Found {len(img_divs)} topo images for boulder "
                         f"'{boulder_name}'")

            # Create a list to store boulder photos
            boulder_photos = []

            # Process each photo with detailed logging
            for idx, img_div in enumerate(img_divs):
                try:
                    # Get the image URL
                    img_url = img_div.find('img')['src']
                    logger.debug(
                        f"Processing photo {idx + 1}/{len(img_divs)} for "
                        f"boulder '{boulder_name}': {img_url}")

                    # Generate a unique photo ID
                    photo_id = f"{hash(img_url)}_{idx}"
                    logger.debug(f"Generated photo ID: {photo_id}")

                    # Get the lines data with detailed logging
                    lines_element = img_div.find('script', class_='js-data')
                    if lines_element:
                        try:
                            lines_data = json.loads(lines_element.text.strip())
                            logger.debug(
                                f"Found lines data for photo {photo_id}:")
                            logger.debug(f"- Number of lines: "
                                         f"{len(lines_data.get('lines', []))}")
                            logger.debug(f"- Has strong line: "
                                         f"{'strong_line' in lines_data}")

                            # Create a BoulderPhoto object
                            photo = BoulderPhoto(id=photo_id,
                                                 url=img_url,
                                                 lines_data=lines_data)

                            boulder_photos.append(photo)
                            logger.debug(
                                f"Successfully added photo {photo_id} to "
                                f"boulder '{boulder_name}'")
                        except json.JSONDecodeError as je:
                            logger.error(
                                f"Failed to parse lines data JSON for photo"
                                f" {photo_id}: {str(je)}")
                            logger.debug(
                                "Raw lines data: "
                                f"{lines_element.text.strip()[:100]}...")
                    else:
                        logger.warning(
                            f"No lines data found for photo {photo_id}")
                except Exception as e:
                    logger.error(f"Error processing photo {idx} for boulder"
                                 f" '{boulder_name}': {str(e)}")
                    continue

            logger.info(f"Successfully processed {len(boulder_photos)} photos "
                        f"for boulder '{boulder_name}'")

            # Process routes in batches
            routes = []
            routes_table_tbody = boulder_page.find('tbody')
            tr_elements = routes_table_tbody.find_all('tr')
            batch_size = self.batch_size

            for i in range(0, len(tr_elements), batch_size):
                batch = tr_elements[i:i + batch_size]

                for tr_element in batch:
                    route = await self._extract_route_data(
                        tr_element, async_session, boulder_photos)
                    if route:
                        routes.append(route)

                await asyncio.sleep(self.batch_delay)

            # Create and return Boulder object
            return Boulder(name=boulder_name,
                           url=boulder_url,
                           gps_postgis=gps_postgis,
                           gps_string=gps_string,
                           routes=routes,
                           photos=boulder_photos)

        except Exception as e:
            logger.error(f"Error extracting boulder data: {str(e)}")
            return None

    async def _extract_route_data(
            self, route_element: BeautifulSoup,
            async_session: aiohttp.ClientSession,
            boulder_photos: List[BoulderPhoto]) -> Optional[Route]:
        """
        Extract data from a route element.

        Args:
            route_element (BeautifulSoup): HTML element containing route data
            async_session (aiohttp.ClientSession): Active aiohttp session
            boulder_photos: List of boulder photos to associate lines with

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
            route_url = normalize_url(route_url)
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
            rating = float(
                route_element.find('div', attrs={
                    'class': 'rating'
                }).text.strip())

            # Get route page
            route_page = await self.get_html(route_url, async_session)
            # Get the route description
            route_description = route_page.find('div',
                                                attrs={
                                                    'class': 'route-info'
                                                }).text.strip()

            # Extract line data with detailed logging
            route_line_data = []
            topo_images = route_page.find_all('div', class_='topo-image')

            logger.debug(f"Processing line data for route '{route_name}'")
            logger.debug(f"Found {len(topo_images)} topo images for route")

            if topo_images:
                for idx, topo_image in enumerate(topo_images):
                    try:
                        # Get the image URL
                        img_url = topo_image.find('img')['src']
                        logger.debug(f"Processing topo image "
                                     f"{idx + 1}/{len(topo_images)}: "
                                     f"{img_url}")

                        # Find matching boulder photo
                        matching_photo = next(
                            (p for p in boulder_photos if p.url == img_url),
                            None)

                        if matching_photo:
                            logger.debug(f"Found matching boulder photo: "
                                         f"{matching_photo.id}")

                            script_data = topo_image.find('script',
                                                          class_='js-data')
                            if script_data:
                                try:
                                    json_data = json.loads(
                                        script_data.text.strip())

                                    # Log the structure of the line data
                                    logger.debug(
                                        f"Line data structure for route "
                                        f"'{route_name}'")
                                    logger.debug(
                                        f"- Has lines: {'lines' in json_data}")
                                    logger.debug(
                                        f"- Has strong line: "
                                        f"{'strong_line' in json_data}")

                                    if 'strong_line' in json_data:
                                        # Create a RouteLineData object
                                        line_data = RouteLineData(
                                            photo_id=matching_photo.id,
                                            line_points=json_data[
                                                'strong_line'])
                                        route_line_data.append(line_data)
                                        logger.debug(
                                            f"Added line data for photo "
                                            f"{matching_photo.id}")
                                    else:
                                        logger.warning(
                                            f"No strong line found for route "
                                            f"'{route_name}' in photo "
                                            f"{matching_photo.id}")
                                except json.JSONDecodeError as je:
                                    logger.error(
                                        f"Failed to parse line data JSON: "
                                        f"{str(je)}")
                                    logger.debug(
                                        "Raw line data: "
                                        f"{script_data.text.strip()[:100]}...")
                            else:
                                logger.warning(
                                    f"No matching boulder photo found"
                                    f" for URL: {img_url}")
                    except Exception as e:
                        logger.error(f"Error processing line data for image"
                                     f" {idx}: {str(e)}")
                        continue

            logger.info(
                f"Processed {len(route_line_data)} line datasets for route "
                f"'{route_name}'")

            # Create and return Route object
            route = Route(name=route_name,
                          url=route_url,
                          grade=grade,
                          rating=rating,
                          description=route_description,
                          line_data=route_line_data)

            logger.debug(f"Created route object for '{route_name}' with "
                         f"{len(route_line_data)} line datasets")
            return route

        except Exception as e:
            logger.error(f"Error extracting route data: {str(e)}")
            return None

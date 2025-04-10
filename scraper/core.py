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
from sqlmodel import Session
from urllib.parse import urljoin
from dotenv import load_dotenv
import random

from utils.general_utils import normalize_url, format_name
from utils.loggers import logger
from .models import Crag, Boulder, Route, BoulderPhoto, RouteLineData
from .auth_utils import check_requires_authentication, standard_login
from .playwright_utils import PlaywrightSession, extract_session_cookies

# Load environment variables
load_dotenv()

# Flag to determine if we should use Playwright for JavaScript rendering
USE_PLAYWRIGHT = os.getenv("USE_PLAYWRIGHT", "true").lower() == "true"


class CragScraper:
    """
    A class to handle scraping data from 27crags.com.
    Includes rate limiting, authentication, and data extraction.
    """

    def __init__(self,
                 headers: Dict[str, str],
                 session: Session = None,
                 crag_name: str = None):
        """
        Initialize the scraper with headers and database session.

        Args:
            headers (dict): HTTP headers for requests
            session (Session, optional): Database session for storing data
            crag_name (str, optional): Name of the crag to scrape
        """
        self.headers = headers
        self.session = session
        self.own_session = session is None
        self.http_session = requests.Session()
        self.last_request_time = 0
        self.batch_size = 3
        self.batch_delay = 0.1
        self.domain = os.getenv("CRAGS_DOMAIN")
        self.login_url = urljoin(self.domain, "login")
        self.crag_name = crag_name
        self.crag_url = urljoin(self.domain,
                                f"crags/{crag_name}") if crag_name else None

        # Configuration
        self.min_request_interval = float(
            os.getenv("MIN_REQUEST_INTERVAL", "1.7"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "5"))

        # Initialize Playwright session if needed
        self.playwright_session = None
        if USE_PLAYWRIGHT:
            self.playwright_session = PlaywrightSession()

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
        Uses standard login first, initializes Playwright if needed.

        Args:
            async_session (aiohttp.ClientSession, optional): Active session

        Returns:
            bool: True if login successful, False otherwise
        """
        # Get credentials from environment
        username = os.environ.get("CRAGS_USERNAME")
        password = os.environ.get("CRAGS_PASSWORD")

        if not username or not password:
            logger.error("Missing login credentials in environment variables")
            return False

        # If we have a session, try standard login first
        if async_session:
            logger.info("Attempting standard login")
            login_success = await standard_login(self.domain, self.headers,
                                                 async_session,
                                                 self._rate_limit)

            if login_success:
                logger.info("Standard login successful")

                # Initialize Playwright if needed but don't use for login
                if USE_PLAYWRIGHT and self.playwright_session:
                    if not self.playwright_session.is_initialized:
                        await self.playwright_session.initialize(self.headers)

                        # Transfer cookies to Playwright session
                        cookies = await extract_session_cookies(
                            async_session, self.domain)
                        if cookies:
                            await self.playwright_session.context.add_cookies(
                                cookies)
                            logger.info("Transferred cookies to Playwright")

                return True
            else:
                logger.warning("Standard login failed")

        # Try Playwright login as fallback
        if USE_PLAYWRIGHT and self.playwright_session:
            logger.info("Attempting Playwright login")

            if not self.playwright_session.is_initialized:
                await self.playwright_session.initialize(self.headers)

            credentials = {"username": username, "password": password}
            login_selectors = {
                "username_field": 'input[name="web_user[username]"]',
                "password_field": 'input[name="web_user[password]"]',
                "submit_button": 'input[type="submit"]',
                "success_indicator": 'body.user-logged'
            }

            playwright_login = await self.playwright_session.login(
                self.login_url, credentials, login_selectors)

            if playwright_login:
                logger.info("Playwright login successful")
                return True
            else:
                logger.error("Playwright login failed")

        logger.error("All login methods failed")
        return False

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
        Get HTML content, using Playwright only
        when JavaScript rendering is needed.

        Args:
            url (str): URL to fetch
            async_session (aiohttp.ClientSession): Active aiohttp session

        Returns:
            BeautifulSoup: Parsed HTML content
        """
        # Determine if this URL needs JavaScript rendering
        needs_js = any([
            '/premiumtopos/' in url,  # Premium topos with SVG routes need JS
            'strong_line' in url,  # Pages with route lines need JS
            '/topo/' in url  # Topo pages need JS
        ])

        # Use Playwright for JavaScript-heavy pages
        if needs_js and USE_PLAYWRIGHT and self.playwright_session:
            try:
                # Ensure Playwright is initialized
                if not self.playwright_session.is_initialized:
                    await self.playwright_session.initialize(self.headers)
                    # Transfer cookies from standard session
                    cookies = await extract_session_cookies(
                        async_session, self.domain)
                    if cookies:
                        await self.playwright_session.context.add_cookies(
                            cookies)

                # Get content using Playwright
                logger.debug(
                    f"Using Playwright for JavaScript rendering: {url}")
                content = await self.playwright_session.get_content(
                    url,
                    wait_for_selector=(
                        '.topo-image, .topo-image-container, script.js-data'),
                    wait_timeout=15000)
                soup = BeautifulSoup(content, 'html5lib')

                # Handle authentication if needed
                if self.requires_authentication(soup):
                    logger.warning("Page requires authentication despite "
                                   f"using Playwright: {url}")
                    if await self.login(async_session):
                        logger.info(
                            "Successfully re-authenticated, retrying request")
                        # Transfer cookies again and retry
                        cookies = await extract_session_cookies(
                            async_session, self.domain)
                        await self.playwright_session.context.add_cookies(
                            cookies)
                        content = await self.playwright_session.get_content(url
                                                                            )
                        soup = BeautifulSoup(content, 'html5lib')

                return soup

            except Exception as e:
                logger.error(f"Playwright request failed: {str(e)}")
                logger.info("Falling back to standard request")
                # Fall through to standard request

        # Standard request for everything else
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

    async def scrape_crag(self, progress_callback=None):
        """
        Scrape all boulder data from a crag page.

        Args:
            progress_callback: Optional function to call with progress updates

        Returns:
            Crag: A Crag object containing all scraped data
        """
        # Initialize skipped_boulders list
        skipped_boulders = []
        # Track start time for elapsed time calculation
        start_time = time.time()

        async with aiohttp.ClientSession(
                headers=self.headers) as async_session:
            try:
                # Initial login
                login_result = await self.login(async_session)
                logger.info("Initial login "
                            f"{'successful' if login_result else 'failed'}")
                if not login_result:
                    logger.error(
                        "Failed to login, cannot proceed with scraping")
                    return {"success": False, "error": "Authentication failed"}

                # Get crag route list
                route_list_url = urljoin(self.crag_url + "/", "routelist")
                logger.debug(f"Fetching route list: {route_list_url}")

                # Use session throughout
                soup = await self.get_html(route_list_url, async_session)

                # Get crag display name from the page
                # (either the h1.cragname element or the text of the anchor
                # inside it)
                crag_title_element = soup.find('h1', class_='cragname')
                if crag_title_element:
                    # Check h1 title attribute first
                    if crag_title_element.get('title'):
                        title = crag_title_element.get('title')
                        crag_display_name = title.strip()
                    else:
                        # Try to find anchor inside the h1
                        crag_anchor = crag_title_element.find('a')
                        if crag_anchor:
                            crag_display_name = crag_anchor.text.strip()
                        else:
                            crag_display_name = crag_title_element.text.strip()
                else:
                    # Fallback to using the crag name from URL
                    crag_display_name = self.crag_name.replace('-',
                                                               ' ').title()

                logger.info(f"Found crag display name: {crag_display_name}")

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
                            boulder_element, boulder_url, async_session)
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

                # Cleanup Playwright session if it was used
                if (USE_PLAYWRIGHT and self.playwright_session
                        and self.playwright_session.is_initialized):
                    logger.info("Closing Playwright session")
                    await self.playwright_session.close()

                # Create and return Crag object
                return Crag(name=self.crag_name,
                            display_name=crag_display_name,
                            boulders=boulders)

            except Exception as e:
                # Cleanup Playwright session if an exception occurs
                if (USE_PLAYWRIGHT and self.playwright_session
                        and self.playwright_session.is_initialized):
                    logger.info("Closing Playwright session due to exception")
                    await self.playwright_session.close()

                logger.error(f"Error scraping crag: {str(e)}")
                return {"success": False, "skipped_boulders": skipped_boulders}

    async def _extract_boulder_data(
            self, boulder_element: BeautifulSoup, boulder_url: str,
            async_session: aiohttp.ClientSession) -> Optional[Boulder]:
        """
        Extract data from a boulder element.

        Args:
            boulder_element (BeautifulSoup): HTML element containing boulder
            data
            boulder_url (str): URL of the boulder
            async_session (aiohttp.ClientSession): Active aiohttp session

        Returns:
            Optional[Boulder]: Boulder object if successful, None otherwise
        """
        try:
            # Get the boulder name and boulder url name
            boulder_display_name = boulder_element.find(
                'div', class_='name').text.strip()
            boulder_name = format_name(boulder_display_name)
            boulder_url_name = boulder_url.split('/')[-1]
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

            # Premium topo pages always require JavaScript to render properly
            # They contain SVG elements and dynamic scripts
            boulder_premium_page = await self.get_html(premium_topo_url,
                                                       async_session)

            # Log the found topo images
            img_divs = boulder_premium_page.find_all('div',
                                                     class_='topo-image')
            logger.debug(f"Found {len(img_divs)} topo images for boulder "
                         f"'{boulder_name}'")

            # Process each photo
            boulder_photos = []
            for idx, img_div in enumerate(img_divs):
                try:
                    # Get the image URL
                    img_url = img_div.find('img')['src']
                    logger.debug(
                        f"Processing photo {idx + 1}/{len(img_divs)} for "
                        f"boulder '{boulder_name}': {img_url}")
                    # Get the order of the photo
                    order = idx + 1
                    # Generate a photo ID using
                    # crag_sector_boulder_number format for easy
                    # replacement and reference of photos
                    photo_id = f"{self.crag_name}_{boulder_name}_{order}"

                    # Extract lines data from JavaScript elements
                    lines_data = self._extract_lines_data(img_div, photo_id)

                    # Always create and add the photo, even without lines data
                    photo = BoulderPhoto(id=photo_id,
                                         source_url=img_url,
                                         order=order,
                                         lines_data=lines_data or {})
                    boulder_photos.append(photo)
                    logger.debug(
                        f"Added photo {photo_id} to boulder '{boulder_name}'")

                except Exception as e:
                    logger.error(f"Error processing photo {idx} for boulder"
                                 f" '{boulder_name}': {str(e)}")
                    continue

            logger.info(
                f"Successfully processed {len(boulder_photos)} photos for "
                f"boulder '{boulder_name}'")

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
                           photos=boulder_photos,
                           display_name=boulder_display_name)

        except Exception as e:
            logger.error(f"Error extracting boulder data: {str(e)}")
            return None

    def _get_boulder_lines(self, img_div, photo_id, img_url, boulder_name):
        """
        Extract lines data from boulder photo.

        Note: This is a regular method (not async) to avoid coroutine issues.

        Args:
            img_div: The HTML div containing the topo image
            photo_id: Generated ID for the photo
            img_url: URL of the topo image
            boulder_name: Name of the boulder for logging

        Returns:
            BoulderPhoto object if successful, None otherwise
        """
        lines_element = img_div.find('script', class_='js-data')
        if not lines_element:
            logger.warning(f"No lines data element found for photo {photo_id}")
            return None

        try:
            lines_text = lines_element.text.strip()
            if not lines_text:
                logger.warning(f"Empty lines data for photo {photo_id}")
                return None

            lines_data = json.loads(lines_text)

            # For boulder photos, we expect to have "lines"
            # but not necessarily "strong_line"
            if 'lines' in lines_data:
                logger.debug(f"Found lines data for photo {photo_id}:")
                logger.debug(f"- Number of lines: {len(lines_data['lines'])}")

                # Create a BoulderPhoto object with all the lines data
                photo = BoulderPhoto(
                    id=photo_id,
                    source_url=img_url,
                    order=1,  # Default order
                    lines_data=lines_data)

                logger.debug(
                    f"Successfully extracted lines data for photo {photo_id} "
                    f"with {len(lines_data['lines'])} lines for boulder "
                    f"'{boulder_name}'")
                return photo
            else:
                logger.warning(
                    f"No 'lines' field found in data for photo {photo_id}")
                return None

        except json.JSONDecodeError as je:
            logger.error("Failed to parse lines data JSON for photo "
                         f"{photo_id}: {str(je)}")
            if lines_element.text.strip():
                logger.debug(
                    f"Raw lines data: {lines_element.text.strip()[:200]}...")
            else:
                logger.warning(
                    f"Lines data is empty string for photo {photo_id}")
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
            route_display_name = anchor.text.strip()
            route_name = format_name(route_display_name)
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
            img_divs = route_page.find_all('div', class_='topo-image')

            logger.debug(f"Processing line data for route '{route_name}'")
            logger.debug(f"Found {len(img_divs)} topo images for route")

            if img_divs:
                for idx, img_div in enumerate(img_divs):
                    try:
                        # Get the image URL
                        img_url = img_div.find('img')['src']
                        logger.debug(f"Processing topo image "
                                     f"{idx + 1}/{len(img_divs)}: "
                                     f"{img_url}")

                        # Find matching boulder photo
                        matching_photo = next((p for p in boulder_photos
                                               if p.source_url == img_url),
                                              None)

                        if matching_photo:
                            logger.debug(f"Found matching boulder photo: "
                                         f"{matching_photo.id}")

                            # Extract route line data
                            line_data = self._get_route_lines(
                                img_div, matching_photo, route_name)
                            if line_data:
                                route_line_data.append(line_data)
                        else:
                            logger.warning(f"No matching boulder photo found"
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
                          line_data=route_line_data,
                          display_name=route_display_name)

            logger.debug(f"Created route object for '{route_name}' with "
                         f"{len(route_line_data)} line datasets")
            return route

        except Exception as e:
            logger.error(f"Error extracting route data: {str(e)}")
            return None

    def _get_route_lines(self, img_div, matching_photo, route_name):
        """
        Extract route line data from a topo image.

        Args:
            img_div: The HTML div containing the topo image
            matching_photo: Matching BoulderPhoto object
            route_name: Name of the route for logging

        Returns:
            RouteLineData object if successful, None otherwise
        """
        # First extract all lines data
        lines_data = self._extract_lines_data(img_div, matching_photo.id)

        # Check specifically for strong_line which highlights this route
        if not lines_data:
            return None

        if 'strong_line' in lines_data:
            # Create a RouteLineData object with the strong_line data
            line_data = RouteLineData(photo_id=matching_photo.id,
                                      line_points=lines_data['strong_line'])
            logger.debug(
                f"Found strong line for route '{route_name}' in photo "
                f"{matching_photo.id}")
            return line_data
        else:
            # It's normal for some route photos not to have a strong_line
            # if they're showing multiple routes
            logger.info(
                f"No strong line found for route '{route_name}' in photo "
                f"{matching_photo.id} - this may be a multi-route topo")
            return None

    def _extract_lines_data(self, img_div, photo_id):
        """
        Extract lines data from topo image JavaScript.

        Args:
            img_div: HTML div containing the topo image
            photo_id: Generated photo ID for logging

        Returns:
            dict: Parsed lines data or empty dict if not found
        """
        lines_element = img_div.find('script', class_='js-data')
        if not lines_element:
            logger.warning(f"No lines data element found for photo {photo_id}")
            return {}

        # Extract text content based on browser rendering method
        if USE_PLAYWRIGHT:
            # Playwright might store content differently
            lines_text = lines_element.string if lines_element.string else ""
        else:
            lines_text = lines_element.text.strip()

        if not lines_text:
            logger.warning(f"Empty lines data for photo {photo_id}")
            return {}

        # Try to parse JSON data
        try:
            lines_data = json.loads(lines_text)

            # Log successful extraction
            logger.debug(f"Extracted lines data for photo {photo_id}: "
                         f"keys={', '.join(lines_data.keys())}")

            # Log line paths if present
            if 'lines' in lines_data:
                logger.debug(
                    f"Photo {photo_id} has {len(lines_data['lines'])} "
                    "line paths")

            return lines_data

        except json.JSONDecodeError as je:
            logger.error(
                f"Failed to parse lines data JSON for photo {photo_id}: "
                f"{str(je)}")
            if lines_text:
                logger.debug(
                    f"Raw content (first 200 chars): {lines_text[:200]}...")
            return {}

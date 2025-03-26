"""
Core scraping functionality for 27crags.com.
Handles authentication, rate limiting, and data extraction.
"""
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
import time
import os
from typing import Dict, Any
from datetime import datetime
from supabase import Client


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
        self.login_url = "https://27crags.com/login"

        # Configuration (can be moved to env vars)
        self.min_request_interval = float(
            os.getenv("MIN_REQUEST_INTERVAL", "1.0"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "5"))
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
            # Get login page for CSRF token
            self._rate_limit()
            login_page = self.session.get(self.login_url, headers=self.headers)

            if login_page.status_code != 200:
                return False

            soup = BeautifulSoup(login_page.content, 'html5lib')
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if not csrf_meta:
                return False

            csrf_token = csrf_meta.get('content')
            if not csrf_token:
                return False

            # Prepare login data
            login_data = {
                'authenticity_token': csrf_token,
                'web_user[username]': username,
                'web_user[password]': password,
                'web_user[remember_me]': '1'
            }

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

            # Perform login
            self._rate_limit()
            response = self.session.post(self.login_url,
                                         data=login_data,
                                         headers=enhanced_headers,
                                         allow_redirects=True)

            # Check login success
            soup = BeautifulSoup(response.content, 'html5lib')
            is_logged_in = any([
                "/" in response.url,
                soup.find('body', class_='user-logged') is not None,
                soup.find('div', class_='user-menu') is not None,
                soup.find('a', href='/logout') is not None
            ])

            self.is_authenticated = is_logged_in
            return is_logged_in

        except Exception:
            return False

    async def scrape_crag(self, crag_url: str) -> Dict[str, Any]:
        """
        Scrape boulder and route data from a 27crags crag page.
        
        Args:
            crag_url (str): URL of the crag to scrape
            
        Returns:
            dict: Dictionary containing boulders, routes, and ascents data
        """
        async with aiohttp.ClientSession() as session:
            try:
                # Get crag page
                async with session.get(crag_url,
                                       headers=self.headers) as response:
                    if response.status != 200:
                        raise Exception(
                            f"Failed to fetch crag page: {response.status}")

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html5lib')

                    # Extract boulders
                    boulders = []
                    boulder_elements = soup.find_all('div', class_='boulder')

                    for boulder in boulder_elements:
                        boulder_data = await self._extract_boulder_data(
                            boulder, session)
                        if boulder_data:
                            boulders.append(boulder_data)

                    # Compile all data
                    data = {
                        'boulders': boulders,
                        'timestamp': datetime.now().isoformat()
                    }

                    # Store in Supabase
                    await self._store_data_in_supabase(data)

                    return data

            except Exception as e:
                raise Exception(f"Error scraping crag: {str(e)}")

    async def _extract_boulder_data(
            self, boulder_element: BeautifulSoup,
            session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Extract data from a boulder element including its routes."""
        try:
            name = boulder_element.find('h3').text.strip()
            url = boulder_element.find('a')['href']

            # Get boulder page for routes
            await self._async_rate_limit()
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html5lib')

                routes = []
                route_elements = soup.find_all('div', class_='route')

                for route in route_elements:
                    route_data = self._extract_route_data(route)
                    if route_data:
                        routes.append(route_data)

                return {'name': name, 'url': url, 'routes': routes}

        except Exception:
            return None

    def _extract_route_data(self,
                            route_element: BeautifulSoup) -> Dict[str, Any]:
        """Extract data from a route element including ascents."""
        try:
            name = route_element.find('h4').text.strip()
            grade = route_element.find('span', class_='grade').text.strip()
            ascents = int(
                route_element.find('span', class_='ascents').text.strip())

            # Extract ascent logs if available
            ascent_log = []
            ascents_div = route_element.find('div', class_='ascent-log')
            if ascents_div:
                for ascent in ascents_div.find_all('div', class_='ascent'):
                    ascent_data = {
                        'climber_name':
                        ascent.find('a', class_='climber').text.strip(),
                        'ascent_type':
                        ascent.find('span', class_='type').text.strip(),
                        'ascent_date':
                        ascent.find('span', class_='date').text.strip()
                    }
                    ascent_log.append(ascent_data)

            return {
                'name': name,
                'grade': grade,
                'ascents': ascents,
                'ascent_log': ascent_log
            }

        except Exception:
            return None

    async def _store_data_in_supabase(self, data: Dict[str, Any]) -> None:
        """Store the scraped data in Supabase tables."""
        try:
            # Store boulders
            for boulder in data['boulders']:
                boulder_data = {'name': boulder['name'], 'url': boulder['url']}
                result = self.supabase.table('boulders').upsert(
                    boulder_data).execute()
                boulder_id = result.data[0]['id']

                # Store routes for this boulder
                for route in boulder['routes']:
                    route_data = {
                        'boulder_id': boulder_id,
                        'name': route['name'],
                        'grade': route['grade'],
                        'ascents_count': route['ascents']
                    }
                    result = self.supabase.table('routes').upsert(
                        route_data).execute()
                    route_id = result.data[0]['id']

                    # Store ascents for this route
                    for ascent in route['ascent_log']:
                        ascent_data = {
                            'route_id': route_id,
                            'climber_name': ascent['climber_name'],
                            'ascent_type': ascent['ascent_type'],
                            'ascent_date': ascent['ascent_date']
                        }
                        self.supabase.table('ascents').upsert(
                            ascent_data).execute()

        except Exception as e:
            raise Exception(f"Error storing data in Supabase: {str(e)}")

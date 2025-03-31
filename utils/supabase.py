import os
from supabase import create_client, Client
from dotenv import load_dotenv
import traceback

from utils.general_utils import normalize_url
from scraper.models import Crag
from utils.loggers import logger

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Verify credentials exist
if not SUPABASE_URL or not SUPABASE_ANON_KEY or not SUPABASE_SERVICE_ROLE_KEY:
    logger.warning("Supabase credentials not found in environment variables.")


def initialize_supabase_client() -> Client:
    """Get a regular Supabase client with anon key for read operations."""
    try:
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {str(e)}")
        raise


def initialize_admin_supabase_client() -> Client:
    """Get a Supabase client with admin privileges for write operations."""
    try:
        admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        return admin_client
    except Exception as e:
        logger.error(f"Error creating admin Supabase client: {str(e)}")
        raise


# Initialize both clients for reuse
_regular_client = initialize_supabase_client()
_admin_client = initialize_admin_supabase_client()


def get_supabase_client() -> Client:
    """Get the regular Supabase client (with anon key)."""
    return _regular_client


def get_admin_supabase_client() -> Client:
    """Get the admin Supabase client (with service role key)."""
    return _admin_client


def get_boulder_mappings(supabase: Client) -> dict:
    """
    Get complete boulder mappings with all IDs directly from
    boulder_sector_mappings table.

    Args:
        supabase (Client): Supabase client

    Returns:
        dict: Mapping of boulder URLs to sector IDs
    """
    try:
        # Query the mappings table directly with all needed IDs
        response = supabase.table("boulder_sector_mappings").select(
            "boulder_url,sector_id").execute()
        mappings = response.data

        if not mappings:
            logger.warning("No boulder-sector mappings found in database.")
            return {}

        # Create direct URL-to-sector-ID mapping
        return {
            normalize_url(mapping['boulder_url']): mapping['sector_id']
            for mapping in mappings
        }

    except Exception as e:
        logger.error(f"Error getting boulder mappings: {str(e)}")
        return {}


def store_crag_data(crag: Crag, supabase: Client) -> dict:
    """
    Store crag data in Supabase using admin privileges.

    Args:
        crag (Crag): Crag object containing scraping data
        supabase (Client): Supabase client with admin privileges.

    Returns:
        dict: Status of the storage operation
    """
    try:
        # Create counters to track stored items
        stored_boulders = 0
        stored_routes = 0
        stored_photos = 0
        stored_line_data = 0
        skipped_boulders = []

        # Get boulder-sector mappings directly from the database table
        sector_map = get_boulder_mappings(supabase)

        # Store boulders and routes directly with the supabase client
        for boulder in crag.boulders:
            # Get sector ID from mapping
            sector_id = sector_map.get(boulder.url)
            if not sector_id:
                logger.warning(
                    f"No sector mapping found for boulder: {boulder.url}")
                skipped_boulders.append(boulder.url)
                continue

            # Insert boulder
            boulder_data = {
                'sector_id': sector_id,
                **boulder.to_dict()
            }
            result = supabase.table('boulders').upsert(
                boulder_data, on_conflict='url').execute()

            # Get the boulder_id from the result
            boulder_id = result.data[0]['id']
            stored_boulders += 1

            # Insert boulder photos if any
            for photo in boulder.photos:
                photo_data = {
                    'boulder_id': boulder_id,
                    'url': photo.url,
                    'photo_id': photo.id,
                    'lines_data': photo.lines_data
                }
                supabase.table('boulder_photos').upsert(
                    photo_data, on_conflict='boulder_id,photo_id').execute()
                stored_photos += 1

            # Insert routes with their line data
            for route in boulder.routes:
                # First insert the route
                route_data = {
                    'boulder_id': boulder_id,
                    **route.to_dict()
                }
                route_result = supabase.table('routes').upsert(
                    route_data, on_conflict='url').execute()

                # Get the route_id from the result
                route_id = route_result.data[0]['id']
                stored_routes += 1

                # If the route has line data, update the route with it
                if route.line_data:
                    # Convert RouteLineData objects to serializable format
                    line_data_json = [{
                        'photo_id': line.photo_id,
                        'line_points': line.line_points
                    } for line in route.line_data]

                    # Update the route with the line data
                    supabase.table('routes').update({
                        'line_data': line_data_json
                    }).eq('id', route_id).execute()
                    stored_line_data += len(route.line_data)

        return {
            "status": "success",
            "stored_boulders": stored_boulders,
            "stored_routes": stored_routes,
            "stored_photos": stored_photos,
            "stored_line_data": stored_line_data,
            "skipped_boulders": skipped_boulders
        }

    except Exception as e:
        logger.error(f"Error storing crag data in Supabase: {str(e)}")
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }

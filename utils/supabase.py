import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import traceback

from scraper.models import Crag

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Verify credentials exist
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase credentials not found in environment variables.")


def initialize_supabase_client() -> Client:
    """
    Get a Supabase client instance with the configured credentials.

    Returns:
        Client: A Supabase client instance.
    """
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {str(e)}")
        raise


# Initialize a global client for reuse
supabase_client = initialize_supabase_client()


def get_supabase_client() -> Client:
    """
    Get the initialized Supabase client.

    Returns:
        Client: The initialized Supabase client.
    """
    return supabase_client


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
            mapping['boulder_url']: mapping['sector_id']
            for mapping in mappings
        }

    except Exception as e:
        logger.error(f"Error getting boulder mappings: {str(e)}")
        return {}


def store_crag_data(supabase: Client, crag: Crag) -> dict:
    """
    Store crag data in Supabase.

    Args:
        supabase (Client): Supabase client
        crag (Crag): Crag object containing scraping data

    Returns:
        dict: Status of the storage operation
    """
    try:
        # Create a counter to track stored items
        stored_boulders = 0
        stored_routes = 0
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
                **boulder.to_supabase_dict()
            }
            result = supabase.table('boulders').upsert(
                boulder_data, on_conflict='url').execute()

            # Get the boulder_id from the result
            boulder_id = result.data[0]['id']
            stored_boulders += 1

            # Insert routes
            for route in boulder.routes:
                route_data = {
                    'boulder_id': boulder_id,
                    **route.to_supabase_dict()
                }
                supabase.table('routes').upsert(route_data,
                                                on_conflict='url').execute()
                stored_routes += 1

        return {
            "status": "success",
            "stored_boulders": stored_boulders,
            "stored_routes": stored_routes,
            "skipped_boulders": skipped_boulders
        }

    except Exception as e:
        logger.error(f"Error storing crag data in Supabase: {str(e)}")
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }

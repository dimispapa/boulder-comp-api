import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import traceback

from scraper.models import Crag
from utils.sector_boulder_map import create_mappings_from_excel

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

        # Get sector mappings
        sector_mappings = create_mappings_from_excel(
            supabase, "data/boulder_sector_mappings.xlsx")

        sector_map = {
            item['boulder_url']: item['sector_id']
            for item in sector_mappings
        }

        # Start transaction
        connection = supabase.pool.acquire()
        try:
            connection.transaction()

            # Store boulders
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
                result = connection.table('boulders').upsert(
                    boulder_data, on_conflict='url').execute()
                boulder_id = result.data[0]['id']
                stored_boulders += 1

                # Insert routes within same transaction
                for route in boulder.routes:
                    route_data = {
                        'boulder_id': boulder_id,
                        **route.to_supabase_dict()
                    }
                    connection.table('routes').upsert(
                        route_data, on_conflict='url').execute()
                    stored_routes += 1

            # Commit the transaction if we got here without errors
            connection.commit()

            return {
                "status": "success",
                "stored_boulders": stored_boulders,
                "stored_routes": stored_routes,
                "skipped_boulders": skipped_boulders
            }
        except Exception as e:
            # Rollback transaction on error
            connection.rollback()
            logger.error(f"Transaction error: {str(e)}, rolling back")
            raise
        finally:
            # Always release the connection back to the pool
            supabase.pool.release(connection)

    except Exception as e:
        logger.error(f"Error storing crag data in Supabase: {str(e)}")
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }

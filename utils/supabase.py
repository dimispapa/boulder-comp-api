import os
from supabase import create_client, Client
from dotenv import load_dotenv
import traceback

from utils.general_utils import normalize_url, format_name
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
        photo_errors = []

        # Log the start of the storage process with summary counts
        total_boulders = len(crag.boulders)
        total_routes = sum(len(boulder.routes) for boulder in crag.boulders)
        total_photos = sum(len(boulder.photos) for boulder in crag.boulders)
        total_line_data = sum(
            len(route.line_data) for boulder in crag.boulders
            for route in boulder.routes)

        logger.info(f"Starting storage process for crag: {crag.name}")
        logger.info(
            f"Processing {total_boulders} boulders, {total_routes} routes, "
            f"{total_photos} photos, and {total_line_data} line data entries")

        # Get boulder-sector mappings directly from the database table
        sector_map = get_boulder_mappings(supabase)
        logger.info(
            f"Loaded {len(sector_map)} boulder-sector mappings from database")

        # Store boulders and routes directly with the supabase client
        for i, boulder in enumerate(crag.boulders, 1):
            # Get sector ID from mapping
            sector_id = sector_map.get(boulder.url)
            if not sector_id:
                logger.warning(
                    f"No sector mapping found for boulder: {boulder.url}")
                skipped_boulders.append(boulder.url)
                continue

            # Log progress periodically (every 5 boulders)
            if i % 5 == 0 or i == 1 or i == total_boulders:
                logger.info(
                    f"Processing boulder {i}/{total_boulders}: {boulder.name}")

            # Format name from the original display name
            display_name = boulder.name
            name = format_name(display_name)

            # Insert boulder - only include fields
            # that match the database schema
            boulder_data = {
                'sector_id': sector_id,
                'name': name,
                'display_name': display_name,
                'url': boulder.url,
                'gps_postgis': boulder.gps_postgis,
                'gps_string': boulder.gps_string
            }

            result = supabase.table('boulders').upsert(
                boulder_data, on_conflict='url').execute()

            # Get the boulder_id from the result
            boulder_id = result.data[0]['id']
            stored_boulders += 1

            # Insert boulder photos if any
            photo_count = len(boulder.photos)
            if photo_count > 0:
                logger.debug(
                    f"Storing {photo_count} photos for boulder: {boulder.name}"
                )

            for photo in boulder.photos:
                try:
                    # Make sure lines_data is properly formatted for JSONB
                    photo_data = {
                        'boulder_id': boulder_id,
                        'url': photo.url,
                        'photo_id': photo.id,
                        'lines_data': photo.lines_data
                        or {}  # Ensure it's not None
                    }

                    # Log the photo data being inserted for debugging
                    logger.debug(
                        f"Inserting photo for boulder {boulder.name}: "
                        f"ID={photo.id}, URL={photo.url}")

                    # Execute the insert with explicit on_conflict parameter
                    result = supabase.table('boulder_photos').upsert(
                        photo_data,
                        on_conflict='boulder_id,photo_id').execute()

                    # Log successful insertion
                    logger.debug(
                        f"Successfully inserted photo {photo.id} with ID: "
                        f"{result.data[0]['id']}")
                    stored_photos += 1
                except Exception as e:
                    # Log detailed error and continue with other photos
                    error_msg = f"Error inserting photo {photo.id} for "
                    + f"boulder {boulder.name}: {str(e)}"
                    logger.error(error_msg)
                    photo_errors.append({
                        'boulder_name': boulder.name,
                        'boulder_id': boulder_id,
                        'photo_id': photo.id,
                        'error': str(e)
                    })

            # Insert routes with their line data - only include fields that
            # match the database schema
            route_count = len(boulder.routes)
            if route_count > 0:
                logger.debug(
                    f"Storing {route_count} routes for boulder: {boulder.name}"
                )

            for route in boulder.routes:
                # Format route name from display name
                route_display_name = route.name
                route_name = format_name(route_display_name)

                # First insert the route
                route_data = {
                    'boulder_id': boulder_id,
                    'name': route_name,
                    'display_name': route_display_name,
                    'url': route.url,
                    'grade': route.grade,
                    'rating': route.rating,
                    'description': route.description
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

        # Log final storage statistics
        logger.info(f"Storage process completed for crag: {crag.name}")
        logger.info(
            f"Storage summary - Stored: {stored_boulders}/{total_boulders} "
            f"boulders, {stored_routes}/{total_routes} routes, "
            f"{stored_photos}/{total_photos} photos, "
            f"{stored_line_data}/{total_line_data} line data entries")

        if skipped_boulders:
            logger.warning(
                f"Skipped {len(skipped_boulders)} boulders due to missing "
                "sector mappings")

        if photo_errors:
            logger.error(
                f"Encountered {len(photo_errors)} errors while storing photos")
            for err in photo_errors[:
                                    5]:  # Log the first 5 errors for reference
                logger.error(f"  - Boulder: {err['boulder_name']}, Photo: "
                             f"{err['photo_id']}, Error: {err['error']}")

        return {
            "status": "success",
            "crag_name": crag.name,
            "total_boulders": total_boulders,
            "total_routes": total_routes,
            "total_photos": total_photos,
            "total_line_data": total_line_data,
            "stored_boulders": stored_boulders,
            "stored_routes": stored_routes,
            "stored_photos": stored_photos,
            "stored_line_data": stored_line_data,
            "skipped_boulders": skipped_boulders,
            "photo_errors": photo_errors
        }

    except Exception as e:
        logger.error(f"Error storing crag data in Supabase: {str(e)}")
        return {
            "status": "error",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }

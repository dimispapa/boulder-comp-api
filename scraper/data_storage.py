"""
Functions for storing scraped data into the database.
"""
import traceback
from sqlmodel import Session
from utils.general_utils import format_name
from utils.loggers import logger
from database.models.crags import Boulder, Route
from database.models.media import BoulderPhoto
from scraper.models import Crag as ScraperCrag
from database.crud.crags import (get_all_boulder_mappings,
                                 create_or_update_boulder,
                                 create_or_update_route,
                                 create_or_update_photo)


def get_boulder_sector_mappings(session: Session) -> dict:
    """
    Get mappings of boulder URLs to sector IDs from database.

    Args:
        session (Session): Database session

    Returns:
        dict: Mapping of boulder URLs to sector IDs
    """
    try:
        # Get mappings from the database
        mappings = get_all_boulder_mappings(session)

        if not mappings:
            logger.warning("No boulder-sector mappings found in database.")
            return {}

        return mappings

    except Exception as e:
        logger.error(f"Error getting boulder mappings: {str(e)}")
        return {}


def store_crag_data(crag: ScraperCrag, session: Session) -> dict:
    """
    Store crag data in database.

    Args:
        crag (ScraperCrag): Crag object containing scraping data
        session (Session): SQLModel session

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
        sector_map = get_boulder_sector_mappings(session)
        logger.info(
            f"Loaded {len(sector_map)} boulder-sector mappings from database")

        # Store boulders and routes
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

            # Create or update boulder
            new_boulder = Boulder(sector_id=sector_id,
                                  name=boulder.name,
                                  display_name=boulder.display_name,
                                  url=boulder.url,
                                  gps_postgis=boulder.gps_postgis,
                                  gps_string=boulder.gps_string)
            saved_boulder = create_or_update_boulder(session, new_boulder)
            boulder_id = saved_boulder.id
            stored_boulders += 1
            logger.debug(
                f"Stored boulder: {boulder.name} with ID {boulder_id}")

            # Insert boulder photos if any
            photo_count = len(boulder.photos)
            if photo_count > 0:
                logger.debug(
                    f"Storing {photo_count} photos for boulder: {boulder.name}"
                )

            for photo in boulder.photos:
                try:
                    # Make sure lines_data is properly formatted for JSONB
                    new_photo = BoulderPhoto(boulder_id=boulder_id,
                                             source_url=photo.source_url,
                                             order=photo.order,
                                             photo_id=photo.id,
                                             lines_data=photo.lines_data or {})

                    # Log the photo data being inserted for debugging
                    logger.debug(f"Inserting photo {photo.order} for boulder "
                                 f"{boulder.name}: ID={photo.id}, "
                                 f"URL={photo.source_url}")

                    # Create or update the photo
                    saved_photo = create_or_update_photo(session, new_photo)

                    # Log successful insertion
                    logger.debug(
                        f"Successfully stored photo {photo.id} with ID: "
                        f"{saved_photo.id}")
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

            # Insert routes with their line data
            route_count = len(boulder.routes)
            if route_count > 0:
                logger.debug(
                    f"Storing {route_count} routes for boulder: {boulder.name}"
                )

            for route in boulder.routes:
                # Format route name from display name
                route_display_name = route.display_name
                route_name = format_name(route_display_name)

                # First insert the route
                line_data_json = None

                # If the route has line data, prepare it for storage
                if route.line_data:
                    # Convert RouteLineData objects to serializable format
                    line_data_json = [{
                        'photo_id': line.photo_id,
                        'line_points': line.line_points
                    } for line in route.line_data]

                # Create or update the route
                new_route = Route(boulder_id=boulder_id,
                                  name=route_name,
                                  display_name=route_display_name,
                                  url=route.url,
                                  grade=route.grade,
                                  rating=route.rating,
                                  description=route.description,
                                  line_data=line_data_json)

                create_or_update_route(session, new_route)
                stored_routes += 1

                if line_data_json:
                    stored_line_data += len(line_data_json)

        # Return storage summary
        return {
            "status": "success",
            "message": "Crag data stored successfully",
            "summary": {
                "stored_boulders": stored_boulders,
                "stored_routes": stored_routes,
                "stored_photos": stored_photos,
                "stored_line_data": stored_line_data,
                "skipped_boulders": len(skipped_boulders),
                "photo_errors": len(photo_errors)
            }
        }

    except Exception as e:
        logger.error(f"Error storing crag data: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Failed to store crag data: {str(e)}",
            "traceback": traceback.format_exc()
        }

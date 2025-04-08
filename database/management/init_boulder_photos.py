#!/usr/bin/env python
"""
Script to upload boulder photos to Cloudinary.
Can be run as a standalone script or imported as a module.
"""
import argparse
import sys

from utils.loggers import logger
from database.management.base import get_db_session
from sqlmodel import select


def reupload_boulder_photos(crag_name="inia-droushia", reset_urls=True):
    """Re-upload boulder photos to Cloudinary after database reset."""
    try:
        logger.info(f"Re-uploading boulder photos for crag: {crag_name}")

        # Import CloudinaryUploader from utils
        from utils.cloudinary_uploader import CloudinaryUploader

        # Create a session and uploader instance
        with get_db_session() as session:
            # First, reset storage_url to null if requested
            if reset_urls:
                # Import BoulderPhoto model here to avoid circular imports
                from database.models.media import BoulderPhoto

                # Get boulder IDs for the specified crag
                from database.models.crags import Boulder, Sector, Crag

                crag_query = select(Crag.id).where(Crag.name == crag_name)
                crag_id = session.exec(crag_query).first()

                if crag_id:
                    # Find all boulders in this crag
                    sector_query = select(
                        Sector.id).where(Sector.crag_id == crag_id)
                    sector_ids = list(session.exec(sector_query))

                    boulder_query = select(Boulder.id).where(
                        Boulder.sector_id.in_(sector_ids))
                    boulder_ids = list(session.exec(boulder_query))

                    # Reset storage URLs for all photos in these boulders
                    photo_query = select(BoulderPhoto).where(
                        BoulderPhoto.boulder_id.in_(boulder_ids))
                    photos = session.exec(photo_query).all()

                    if photos:
                        for photo in photos:
                            photo.storage_url = None
                            session.add(photo)

                        session.commit()
                        logger.info(f"Reset storage_url for {len(photos)} "
                                    "boulder photos")

            # Create uploader and upload all photos
            uploader = CloudinaryUploader(session)
            result = uploader.upload_photos_for_crag(crag_name)

            if result.get("status") == "success":
                logger.info(f"Successfully uploaded boulder photos: "
                            f"{result.get('uploaded', 0)} photos uploaded")
                return True
            else:
                logger.error(f"Failed to upload boulder photos: {result}")
                return False

    except Exception as e:
        logger.error(f"Error uploading boulder photos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload boulder photos to Cloudinary.")
    parser.add_argument("--crag",
                        type=str,
                        default="inia-droushia",
                        help="Crag name to upload photos for")
    parser.add_argument("--skip-reset",
                        action="store_true",
                        help="Skip resetting storage URLs before upload")
    args = parser.parse_args()

    success = reupload_boulder_photos(args.crag, not args.skip_reset)
    if not success:
        logger.error("Failed to upload boulder photos")
        sys.exit(1)

    logger.info("Boulder photo upload complete")

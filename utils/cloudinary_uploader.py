"""
Utility for uploading photos to Cloudinary.
"""
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Dict, Any, List
from supabase import Client
from utils.loggers import logger
import traceback
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")


class CloudinaryUploader:
    """Handles uploading photos to Cloudinary"""

    def __init__(self, supabase: Client, folder_base: str = "boulder-comp"):
        """
        Initialize the uploader with Cloudinary and Supabase clients.

        Args:
            supabase (Client): Initialized Supabase client
            folder_base (str): Base folder name in Cloudinary
        """
        self.supabase = supabase
        self.folder_base = folder_base
        # Cache to store verified folder paths to reduce API calls
        self.folder_cache = set()

        # Initialize Cloudinary with credentials
        cloudinary.config(cloud_name=CLOUDINARY_CLOUD_NAME,
                          api_key=CLOUDINARY_API_KEY,
                          api_secret=CLOUDINARY_API_SECRET,
                          secure=True)

        logger.info(
            f"CloudinaryUploader initialized with base folder: {folder_base}")

    def pre_create_folders(self, crag_name=None):
        """
        Pre-create all folders needed for uploads to minimize API calls.

        Args:
            crag_name (str, optional): Name of the crag to create folders for.
                If None, creates folders for all crags.

        Returns:
            bool: True if folder creation was successful, False otherwise
        """
        logger.info(
            "Pre-creating folders to minimize API calls during uploads")

        # First, make sure the base folder exists
        if not self._ensure_folder_exists(self.folder_base):
            logger.error(f"Failed to create base folder: {self.folder_base}")
            return False

        # Create boulder-photos folder
        boulder_photos_folder = f"{self.folder_base}/boulder-photos"
        if not self._ensure_folder_exists(boulder_photos_folder):
            logger.error(f"Failed to create folder: {boulder_photos_folder}")
            return False

        # Create competition-photos folder
        competition_photos_folder = f"{self.folder_base}/competition-photos"
        if not self._ensure_folder_exists(competition_photos_folder):
            logger.error(
                f"Failed to create folder: {competition_photos_folder}")
            # Continue anyway - we might not need competition folders

        # If we're only interested in a specific crag
        if crag_name:
            try:
                # Get crag information
                crag_response = self.supabase.table('crags').select(
                    'id, name, display_name').eq('name', crag_name).execute()

                if not crag_response.data:
                    logger.error(f"Crag {crag_name} not found in database")
                    return False

                crag_id = crag_response.data[0]['id']

                # Create the crag folder
                crag_folder = f"{boulder_photos_folder}/{crag_name}"
                if not self._ensure_folder_exists(crag_folder):
                    logger.error(
                        f"Failed to create crag folder: {crag_folder}")
                    return False

                # Get sectors in this crag
                sector_response = self.supabase.table('sectors').select(
                    'id, name').eq('crag_id', crag_id).execute()

                if not sector_response.data:
                    logger.info(f"No sectors found for crag {crag_name}")
                    return True

                # Create a folder for each sector
                for sector in sector_response.data:
                    sector_name = sector['name']
                    # Use the full nested path as originally designed
                    folder = \
                        f"{boulder_photos_folder}/{crag_name}/{sector_name}"
                    if not self._ensure_folder_exists(folder):
                        logger.warning(f"Failed to create folder: {folder}")
                        # Continue with next sector

                return True

            except Exception as e:
                logger.error(f"Error pre-creating folders: {str(e)}")
                logger.error(f"Exception details: {traceback.format_exc()}")
                return False

        # If no crag specified, we're done with the base folders
        return True

    def upload_photos_for_crag(self, crag_name: str) -> Dict[str, Any]:
        """
        Upload all boulder photos for a specific crag to Cloudinary.

        Args:
            crag_name (str): Name of the crag to upload photos for

        Returns:
            Dict[str, Any]: Result containing upload statistics
        """
        logger.info(f"Starting boulder photo upload for crag: {crag_name}")

        # Pre-create folders to minimize API calls during uploads
        self.pre_create_folders(crag_name)

        # Initialize counters
        successful_uploads = 0
        failed_uploads: List[Dict[str, Any]] = []
        total_photos_to_upload = 0

        try:
            # Get crag information
            crag_response = self.supabase.table('crags').select(
                'id, name, display_name').eq('name', crag_name).execute()

            if not crag_response.data:
                error_msg = f"Crag {crag_name} not found in database"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "crag_name": crag_name,
                    "error": error_msg,
                    "total": 0,
                    "uploaded": 0,
                    "failed": 0,
                    "failures": []
                }

            crag_id = crag_response.data[0]['id']
            crag_display_name = crag_response.data[0]['display_name']

            logger.info(f"Found crag: {crag_display_name} (ID: {crag_id})")

            # Get sectors in this crag
            sector_response = self.supabase.table('sectors').select(
                'id, name, display_name').eq('crag_id', crag_id).execute()

            if not sector_response.data:
                error_msg = f"No sectors found for crag {crag_display_name}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "crag_name": crag_name,
                    "error": error_msg,
                    "total": 0,
                    "uploaded": 0,
                    "failed": 0,
                    "failures": []
                }

            logger.info(f"Found {len(sector_response.data)} sectors in crag "
                        f"{crag_display_name}")

            for sector in sector_response.data:
                sector_id = sector['id']
                sector_name = sector['name']
                sector_display_name = sector['display_name']

                logger.info(f"Processing sector: {sector_display_name} "
                            f"(ID: {sector_id})")

                # Get boulders in this sector
                boulder_response = (self.supabase.table('boulders').select(
                    'id, name, display_name').eq('sector_id',
                                                 sector_id).execute())

                if not boulder_response.data:
                    logger.info(f"No boulders found in sector: "
                                f"{sector_display_name}")
                    continue

                # Get all boulder IDs in this sector
                boulder_ids = [b['id'] for b in boulder_response.data]
                boulder_names = {
                    b['id']: b['name']
                    for b in boulder_response.data
                }
                boulder_display_names = {
                    b['id']: b['display_name']
                    for b in boulder_response.data
                }

                logger.info(f"Found {len(boulder_ids)} boulders in sector "
                            f"{sector_display_name}")

                # Get photos that need uploading (where cloudinary_url is null)
                sector_photos_to_upload = []

                for boulder_id in boulder_ids:
                    # Look for photos that need uploading to Cloudinary
                    photo_response = self.supabase.table('boulder_photos') \
                        .select('id, url, photo_id') \
                        .eq('boulder_id', boulder_id) \
                        .is_('cloudinary_url', 'null') \
                        .execute()

                    if photo_response.data:
                        # Add boulder name and id to each photo
                        for photo in photo_response.data:
                            photo['boulder_name'] = boulder_names[boulder_id]
                            photo['boulder_display_name'] = \
                                boulder_display_names[boulder_id]
                            photo['boulder_id'] = boulder_id
                            photo['sector_name'] = sector_name
                            photo['sector_display_name'] = sector_display_name
                            photo['crag_name'] = crag_name
                            photo['crag_display_name'] = crag_display_name
                            # Mark as boulder photo
                            photo['photo_type'] = 'boulder'

                        sector_photos_to_upload.extend(photo_response.data)

                if not sector_photos_to_upload:
                    logger.info(f"No photos found to upload for sector: "
                                f"{sector_display_name}")
                    continue

                logger.info(
                    f"Found {len(sector_photos_to_upload)} photos to upload "
                    f"for sector: {sector_display_name}")

                total_photos_to_upload += len(sector_photos_to_upload)

                # Process photos one by one for better error tracking
                for photo in sector_photos_to_upload:
                    result = self._upload_boulder_photo(photo)
                    if result["success"]:
                        successful_uploads += 1
                    else:
                        failed_uploads.append({
                            "photo_id":
                            photo["id"],
                            "photo_url":
                            photo["url"],
                            "boulder_id":
                            photo["boulder_id"],
                            "boulder_name":
                            photo["boulder_name"],
                            "error":
                            result["error"]
                        })

            # Completed processing all sectors
            logger.info(
                f"Completed photo upload for crag {crag_display_name}. "
                f"Stats: {successful_uploads}/{total_photos_to_upload} "
                f"successful uploads.")

            return {
                "status": "success",
                "crag_name": crag_name,
                "total": total_photos_to_upload,
                "uploaded": successful_uploads,
                "failed": len(failed_uploads),
                "failures": failed_uploads
            }

        except Exception as e:
            error_msg = (f"Error uploading photos for crag {crag_name}: "
                         f"{str(e)}")
            logger.error(error_msg)
            logger.error(f"Exception details: {traceback.format_exc()}")
            return {
                "status": "error",
                "crag_name": crag_name,
                "error": error_msg,
                "total": total_photos_to_upload,
                "uploaded": successful_uploads,
                "failed": len(failed_uploads),
                "failures": failed_uploads
            }

    def upload_competition_photos(self, competition_id: str) -> Dict[str, Any]:
        """
        Upload user-submitted photos for a competition to Cloudinary.

        Args:
            competition_id (str): ID of the competition

        Returns:
            Dict[str, Any]: Result containing upload statistics
        """
        logger.info(
            f"Starting user photo upload for competition: {competition_id}")

        # Initialize counters
        successful_uploads = 0
        failed_uploads: List[Dict[str, Any]] = []
        total_photos_to_upload = 0

        try:
            # Get competition information
            competition_response = self.supabase.table('competitions').select(
                'id, name, display_name').eq('id', competition_id).execute()

            if not competition_response.data:
                error_msg = (f"Competition with ID {competition_id} not "
                             f"found in database")
                logger.error(error_msg)
                return {
                    "status": "error",
                    "competition_id": competition_id,
                    "error": error_msg,
                    "total": 0,
                    "uploaded": 0,
                    "failed": 0,
                    "failures": []
                }

            competition_name = competition_response.data[0]['name']
            competition_display_name = competition_response.data[0][
                'display_name']

            logger.info(f"Found competition: {competition_display_name}")

            # Get user-submitted photos for this competition
            # that need uploading
            photo_response = self.supabase.table('competition_photos') \
                .select('id, url, uploader_id, description') \
                .eq('competition_id', competition_id) \
                .is_('cloudinary_url', 'null') \
                .execute()

            if not photo_response.data:
                logger.info(f"No photos found for competition: "
                            f"{competition_display_name}")
                return {
                    "status": "success",
                    "competition_id": competition_id,
                    "total": 0,
                    "uploaded": 0,
                    "failed": 0,
                    "failures": []
                }

            total_photos_to_upload = len(photo_response.data)
            logger.info(f"Found {total_photos_to_upload} photos to upload for "
                        f"competition: {competition_display_name}")

            # Get uploader information for all photos
            uploader_ids = list(
                set(photo['uploader_id'] for photo in photo_response.data))
            uploader_response = self.supabase.table('participants') \
                .select('id, user_id, display_name') \
                .in_('id', uploader_ids) \
                .execute()

            uploader_info = {
                u['id']: u['display_name']
                for u in uploader_response.data
            }

            # Process photos
            for photo in photo_response.data:
                # Add competition info to photo
                photo['competition_name'] = competition_name
                photo['competition_display_name'] = competition_display_name
                photo['competition_id'] = competition_id
                # Add uploader info if available
                photo['uploader_name'] = uploader_info.get(
                    photo['uploader_id'], 'unknown')
                # Mark as competition photo
                photo['photo_type'] = 'competition'

                result = self._upload_competition_photo(photo)
                if result["success"]:
                    successful_uploads += 1
                else:
                    failed_uploads.append({
                        "photo_id": photo["id"],
                        "photo_url": photo["url"],
                        "uploader_id": photo["uploader_id"],
                        "error": result["error"]
                    })

            # Completed processing
            logger.info(
                f"Completed photo upload for competition "
                f"{competition_display_name}. "
                f"Stats: {successful_uploads}/{total_photos_to_upload} "
                f"successful uploads.")

            return {
                "status": "success",
                "competition_id": competition_id,
                "total": total_photos_to_upload,
                "uploaded": successful_uploads,
                "failed": len(failed_uploads),
                "failures": failed_uploads
            }

        except Exception as e:
            error_msg = (f"Error uploading photos for competition "
                         f"{competition_id}: {str(e)}")
            logger.error(error_msg)
            logger.error(f"Exception details: {traceback.format_exc()}")
            return {
                "status": "error",
                "competition_id": competition_id,
                "error": error_msg,
                "total": total_photos_to_upload,
                "uploaded": successful_uploads,
                "failed": len(failed_uploads),
                "failures": failed_uploads
            }

    def _ensure_folder_exists(self, folder_path: str) -> bool:
        """
        Check if a folder exists in Cloudinary, and create it if it doesn't.
        Uses caching to reduce API calls.

        Args:
            folder_path (str): The full path of the folder to check/create

        Returns:
            bool: True if folder exists or was created successfully,
                 False on error
        """
        # Check if this folder path has already been verified
        if folder_path in self.folder_cache:
            return True

        try:
            # Split the path to get parent folder and current folder
            path_parts = folder_path.split('/')

            # If this is a root folder
            if len(path_parts) == 1:
                folders_response = cloudinary.api.root_folders()
                root_folders = [
                    folder["path"]
                    for folder in folders_response.get("folders", [])
                ]

                if folder_path not in root_folders:
                    logger.info(f"Creating root folder: {folder_path}")
                    cloudinary.api.create_folder(folder_path)

                # Add to cache
                self.folder_cache.add(folder_path)
                return True

            # For nested folders, first ensure parent exists
            parent_path = '/'.join(path_parts[:-1])
            if not self._ensure_folder_exists(parent_path):
                return False

            # Check if the current folder exists in the parent
            subfolders_response = cloudinary.api.subfolders(parent_path)
            subfolder_paths = [
                folder["path"]
                for folder in subfolders_response.get("folders", [])
            ]

            if folder_path not in subfolder_paths:
                logger.info(f"Creating folder: {folder_path}")
                cloudinary.api.create_folder(folder_path)

            # Add to cache
            self.folder_cache.add(folder_path)
            return True

        except Exception as e:
            if "Rate Limit Exceeded" in str(e):
                logger.warning("Cloudinary rate limit exceeded. "
                               "Using cached folders where possible.")

            logger.error(f"Error ensuring folder exists: {str(e)}")
            logger.error(f"Exception details: {traceback.format_exc()}")
            return False

    def _setup_folder_structure(self, folder_path: str) -> bool:
        """
        Set up the folder structure for uploads.

        Args:
            folder_path (str): The full path to set up

        Returns:
            bool: True if structure was set up successfully, False otherwise
        """
        try:
            return self._ensure_folder_exists(folder_path)
        except Exception as e:
            logger.error(f"Error setting up folder structure: {str(e)}")
            logger.error(f"Exception details: {traceback.format_exc()}")
            return False

    def _upload_boulder_photo(self, photo_data: Dict[str,
                                                     Any]) -> Dict[str, Any]:
        """
        Upload a single boulder photo to Cloudinary.

        Args:
            photo_data (dict): Photo data including URL and metadata

        Returns:
            dict: Result of the upload operation
        """
        photo_id = photo_data["id"]
        source_url = photo_data["url"]
        boulder_display_name = photo_data["boulder_display_name"]
        boulder_name = photo_data["boulder_name"]
        crag_name = photo_data["crag_name"]
        sector_name = photo_data["sector_name"]

        logger.info(
            f"Uploading photo {photo_id} for boulder {boulder_display_name}")
        logger.debug(f"Source URL: {source_url}")

        try:
            # Use the original nested folder structure
            folder_path = \
                f"{self.folder_base}/boulder-photos/{crag_name}/{sector_name}"

            # Check if this folder exists in our cache first
            if folder_path not in self.folder_cache:
                # Try parent folder levels as fallback
                parent_folder = \
                    f"{self.folder_base}/boulder-photos/{crag_name}"
                if parent_folder in self.folder_cache:
                    # Create sector folder if possible
                    if self._ensure_folder_exists(folder_path):
                        # Successfully created the full path
                        pass
                    else:
                        # If we can't create the sector folder,
                        # use the crag folder
                        folder_path = parent_folder
                else:
                    # Try boulder-photos folder
                    parent_folder = f"{self.folder_base}/boulder-photos"
                    if parent_folder in self.folder_cache:
                        folder_path = parent_folder
                    else:
                        # Last resort - use base folder
                        folder_path = self.folder_base
                        if folder_path not in self.folder_cache:
                            # No folders - use root
                            folder_path = ""

            # Generate a safe filename (without folder path)
            safe_boulder_name = "".join(c if c.isalnum() or c == "_" else "_"
                                        for c in boulder_display_name)
            safe_crag_name = "".join(c if c.isalnum() or c == "_" else "_"
                                     for c in crag_name)
            safe_sector_name = "".join(c if c.isalnum() or c == "_" else "_"
                                       for c in sector_name)

            # Create unique filename with crag, sector, and boulder info
            file_name = (f"{safe_crag_name}_{safe_sector_name}_"
                         f"{safe_boulder_name}_{photo_data['photo_id']}_"
                         f"{uuid.uuid4().hex[:8]}")

            # Upload directly from the URL to Cloudinary
            # using the folder parameter
            upload_result = cloudinary.uploader.upload(
                source_url,
                folder=folder_path,
                public_id=file_name,
                resource_type="image",
                overwrite=True,
                responsive=True,  # Generate responsive variants
                tags=["boulder", crag_name, sector_name, boulder_name])

            # Get the secure URL from the response
            cloudinary_url = upload_result["secure_url"]

            # Update the database with the new Cloudinary URL
            self.supabase.table("boulder_photos").update({
                "cloudinary_url":
                cloudinary_url,
                "cloudinary_public_id":
                upload_result["public_id"],
                "cloudinary_resource_type":
                "image"
            }).eq("id", photo_id).execute()

            logger.info(
                f"Successfully uploaded photo {photo_id} to Cloudinary: "
                f"{cloudinary_url}")
            return {
                "success": True,
                "photo_id": photo_id,
                "cloudinary_url": cloudinary_url
            }
        except Exception as e:
            error_msg = (f"Error uploading photo {photo_id} to Cloudinary: "
                         f"{str(e)}")
            logger.error(error_msg)
            logger.error(f"Exception details: {traceback.format_exc()}")
            return {"success": False, "photo_id": photo_id, "error": error_msg}

    def _upload_competition_photo(
            self, photo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload a single competition photo to Cloudinary.

        Args:
            photo_data (dict): Photo data including URL and metadata

        Returns:
            dict: Result of the upload operation
        """
        photo_id = photo_data["id"]
        source_url = photo_data["url"]
        competition_name = photo_data["competition_name"]
        uploader_name = photo_data["uploader_name"]

        logger.info(
            f"Uploading competition photo {photo_id} from {uploader_name}")
        logger.debug(f"Source URL: {source_url}")

        try:
            # Generate folder path for organizing in Cloudinary
            folder_path = (f"{self.folder_base}/competition-photos/"
                           f"{competition_name}")

            # Set up the folder structure for this upload
            folder_setup_success = self._setup_folder_structure(folder_path)

            if not folder_setup_success:
                logger.warning(
                    f"Could not set up folder structure for {folder_path}. "
                    f"Will attempt upload with simplified path.")
                # Fall back to a simpler path if folder creation failed
                if (f"{self.folder_base}/competition-photos"
                        in self.folder_cache):
                    folder_path = f"{self.folder_base}/competition-photos"
                elif self.folder_base in self.folder_cache:
                    folder_path = self.folder_base
                else:
                    # Last resort - root folder
                    folder_path = ""

            # Generate a safe filename (without folder path)
            safe_uploader_name = "".join(c if c.isalnum() or c == "_" else "_"
                                         for c in uploader_name)

            # Create unique filename with uploader info
            file_name = f"{safe_uploader_name}_{uuid.uuid4().hex[:8]}"

            # Upload directly from the URL to Cloudinary using folder parameter
            upload_result = cloudinary.uploader.upload(
                source_url,
                folder=folder_path,
                public_id=file_name,
                resource_type="image",
                overwrite=True,
                responsive=True,  # Generate responsive variants
                moderation="aws_rek",  # Use AWS Rekognition for
                # content moderation
                tags=[
                    "competition", competition_name, "user-submitted",
                    safe_uploader_name
                ])

            # Get the secure URL from the response
            cloudinary_url = upload_result["secure_url"]

            # Update the database with the new Cloudinary URL
            self.supabase.table("competition_photos").update({
                "cloudinary_url":
                cloudinary_url,
                "cloudinary_public_id":
                upload_result["public_id"],
                "cloudinary_resource_type":
                "image",
                "moderation_status":
                upload_result.get("moderation", {}).get("status", "pending")
            }).eq("id", photo_id).execute()

            logger.info(
                f"Successfully uploaded competition photo {photo_id} to "
                f"Cloudinary: {cloudinary_url}")
            return {
                "success": True,
                "photo_id": photo_id,
                "cloudinary_url": cloudinary_url
            }
        except Exception as e:
            error_msg = (f"Error uploading competition photo {photo_id} to "
                         f"Cloudinary: {str(e)}")
            logger.error(error_msg)
            logger.error(f"Exception details: {traceback.format_exc()}")
            return {"success": False, "photo_id": photo_id, "error": error_msg}

"""
Utility for uploading photos to Supabase Storage.
"""
import uuid
import requests
from typing import Dict, Any
from supabase import Client
from utils.loggers import logger
import traceback


class PhotoUploader:
    """Handles uploading photos from scraped URLs to Supabase Storage"""

    def __init__(self, supabase: Client, bucket_name: str = "boulder-photos"):
        """
        Initialize the uploader with a Supabase client.

        Args:
            supabase (Client): Initialized Supabase client
            bucket_name (str): Name of the Supabase storage bucket
        """
        self.supabase = supabase
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists, create if it doesn't"""
        try:
            logger.info(f"Checking if bucket {self.bucket_name} exists...")
            buckets = self.supabase.storage.list_buckets()
            bucket_exists = any(b['name'] == self.bucket_name for b in buckets)

            if not bucket_exists:
                logger.info(f"Bucket {self.bucket_name} does not exist, "
                            f"creating it...")
                # Try to create bucket
                try:
                    # Create bucket with public access
                    self.supabase.storage.create_bucket(
                        name=self.bucket_name, options={'public': True})
                    logger.info(
                        f"Created new storage bucket: {self.bucket_name}")
                except Exception as bucket_err:
                    # Log error
                    logger.warning(
                        f"Failed to create bucket: {str(bucket_err)}")
            else:
                logger.info(
                    f"Bucket {self.bucket_name} already exists. Proceeding...")
        except Exception as e:
            logger.error(f"Error checking/creating bucket: {str(e)}")
            logger.error(f"Exception details: {traceback.format_exc()}")

    def upload_photos_for_crag(self, crag_name: str) -> Dict[str, Any]:
        """
        Upload all photos for a specific crag that haven't been uploaded yet.

        Args:
            crag_name (str): Name of the crag to process photos for

        Returns:
            dict: Statistics about the upload operation
        """
        try:
            # Get crag ID for the provided crag name
            logger.info(f"Getting crag ID for crag: {crag_name}")
            crag_response = (
                self.supabase.table('crags').select('id, display_name').eq(
                    'name', crag_name).execute())

            if not crag_response.data:
                logger.error(f"Crag not found with name: {crag_name}")
                return {
                    "status": "error",
                    "error": f"Crag '{crag_name}' not found",
                    "failures": []
                }

            crag_id = crag_response.data[0]['id']
            crag_display_name = crag_response.data[0]['display_name']
            logger.info(f"Found crag ID: {crag_id} for '{crag_display_name}'")

            # Get sectors in this crag
            sector_response = (self.supabase.table('sectors').select(
                'id, name, display_name').eq('crag_id', crag_id).execute())

            if not sector_response.data:
                logger.info(f"No sectors found in crag: {crag_display_name}")
                return {
                    "status": "success",
                    "uploaded": 0,
                    "skipped": 0,
                    "failures": []
                }

            # Process each sector in the crag
            successful_uploads = 0
            failed_uploads = []
            total_photos_to_upload = 0

            for sector in sector_response.data:
                sector_id = sector['id']
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

                # Get photos that need uploading (where storage_url is null)
                # Note: We need to do separate queries per boulder due to
                # Supabase limitations
                sector_photos_to_upload = []

                for boulder_id in boulder_ids:
                    photo_response = self.supabase.table('boulder_photos') \
                        .select('id, url, photo_id') \
                        .eq('boulder_id', boulder_id) \
                        .is_('storage_url', 'null') \
                        .execute()

                    if photo_response.data:
                        # Add boulder name and id to each photo
                        for photo in photo_response.data:
                            photo['boulder_name'] = boulder_names[boulder_id]
                            photo['boulder_display_name'] = \
                                boulder_display_names[boulder_id]
                            photo['boulder_id'] = boulder_id

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
                    result = self._upload_photo(photo)
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

            return {
                "status": "success",
                "total": total_photos_to_upload,
                "uploaded": successful_uploads,
                "failed": len(failed_uploads),
                "failures": failed_uploads
            }

        except Exception as e:
            logger.error(
                f"Error uploading photos for crag {crag_name}: {str(e)}")
            return {"status": "error", "error": str(e), "failures": []}

    def _upload_photo(self, photo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload a single photo and update the database

        Args:
            photo_data: Dictionary with photo information

        Returns:
            dict: Result of the upload operation
        """
        photo_id = photo_data['id']
        source_url = photo_data['url']
        boulder_display_name = photo_data['boulder_display_name']

        try:
            # Download the image
            response = requests.get(source_url, timeout=30)
            if response.status_code != 200:
                error_msg = f"Failed to download photo from {source_url}: " \
                            f"HTTP {response.status_code}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "photo_id": photo_id,
                    "error": error_msg
                }

            image_data = response.content

            # Generate file path and name
            safe_boulder_name = "".join(c if c.isalnum() else "_"
                                        for c in boulder_display_name)
            file_name = f"{safe_boulder_name}_{photo_data['photo_id']}"
            file_name += f"_{uuid.uuid4().hex[:8]}.jpg"
            file_path = f"boulders/{file_name}"

            # Upload to Supabase Storage
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=image_data,
                file_options={
                    "content-type": "image/jpeg",
                    "cache-control": "3600"
                })
            logger.info(f"Upload result: {result}")

            # Get public URL
            public_url = self.supabase.storage.from_(
                self.bucket_name).get_public_url(file_path)

            # Update the database with the new URL
            self.supabase.table("boulder_photos").update({
                "storage_url":
                public_url
            }).eq("id", photo_id).execute()

            logger.info(
                f"Successfully uploaded photo {photo_id} to {public_url}")
            return {
                "success": True,
                "photo_id": photo_id,
                "storage_url": public_url
            }

        except Exception as e:
            logger.error(f"Error uploading photo {photo_id}: {str(e)}")
            return {"success": False, "photo_id": photo_id, "error": str(e)}

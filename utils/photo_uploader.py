"""
Utility for uploading photos to Supabase Storage.
"""
import uuid
import requests
from typing import Dict, Any
from supabase import Client
from utils.loggers import logger


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
            buckets = self.supabase.storage.list_buckets()
            if not any(b['name'] == self.bucket_name for b in buckets):
                self.supabase.storage.create_bucket(self.bucket_name,
                                                    {'public': True})
                logger.info(f"Created new storage bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error checking/creating bucket: {str(e)}")

    def upload_photos_for_crag(self, crag_name: str) -> Dict[str, Any]:
        """
        Upload all photos for a specific crag that haven't been uploaded yet.

        Args:
            crag_name (str): Name of the crag to process photos for

        Returns:
            dict: Statistics about the upload operation
        """
        try:
            # Get all boulder photos that need processing
            # (where storage_url is null)
            query = """
            SELECT bp.id, bp.url, bp.photo_id, b.name as boulder_name,
            b.id as boulder_id
            FROM boulder_photos bp
            JOIN boulders b ON bp.boulder_id = b.id
            JOIN sectors s ON b.sector_id = s.id
            JOIN crags c ON s.crag_id = c.id
            WHERE c.name = :crag_name
            AND bp.storage_url IS NULL
            """

            # Execute raw SQL query to get photos that need uploading
            response = self.supabase.rpc('select_raw', {
                'query': query,
                'params': {
                    'crag_name': crag_name
                }
            }).execute()
            photos_to_upload = response.data

            if not photos_to_upload:
                logger.info(f"No photos found to upload for crag: {crag_name}")
                return {
                    "status": "success",
                    "uploaded": 0,
                    "skipped": 0,
                    "failures": []
                }

            logger.info(
                f"Found {len(photos_to_upload)} photos to upload for crag: "
                f"{crag_name}")

            # Process photos one by one for better error tracking
            successful_uploads = 0
            failed_uploads = []

            for photo in photos_to_upload:
                result = self._upload_photo(photo)
                if result["success"]:
                    successful_uploads += 1
                else:
                    failed_uploads.append({
                        "photo_id": photo["id"],
                        "photo_url": photo["url"],
                        "boulder_id": photo["boulder_id"],
                        "boulder_name": photo["boulder_name"],
                        "error": result["error"]
                    })

            return {
                "status": "success",
                "total": len(photos_to_upload),
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
        boulder_name = photo_data['boulder_name']

        try:
            # Download the image
            response = requests.get(source_url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to download photo from {source_url}: "
                             f"{response.status_code}")
                return {
                    "success": False,
                    "photo_id": photo_id,
                    "error": f"HTTP {response.status_code}"
                }

            image_data = response.content

            # Generate file path and name
            safe_boulder_name = "".join(c if c.isalnum() else "_"
                                        for c in boulder_name)
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

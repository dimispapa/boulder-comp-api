-- Add Cloudinary-specific columns to boulder_photos table
ALTER TABLE boulder_photos
ADD COLUMN IF NOT EXISTS cloudinary_url TEXT,
ADD COLUMN IF NOT EXISTS cloudinary_public_id TEXT,
ADD COLUMN IF NOT EXISTS cloudinary_resource_type TEXT DEFAULT 'image';

-- Add comment for documentation
COMMENT ON COLUMN boulder_photos.cloudinary_url IS 'URL of the photo in Cloudinary, populated after successful migration';
COMMENT ON COLUMN boulder_photos.cloudinary_public_id IS 'Cloudinary public ID (used for referencing the image in Cloudinary APIs)';
COMMENT ON COLUMN boulder_photos.cloudinary_resource_type IS 'Cloudinary resource type (image, video, etc.)'; 
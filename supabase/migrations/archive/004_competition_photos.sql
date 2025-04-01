-- Add Cloudinary specific columns to boulder_photos table if they don't exist
ALTER TABLE boulder_photos
ADD COLUMN IF NOT EXISTS cloudinary_url TEXT,
ADD COLUMN IF NOT EXISTS cloudinary_public_id TEXT,
ADD COLUMN IF NOT EXISTS cloudinary_resource_type TEXT DEFAULT 'image';

-- Create competition_photos table for user-submitted photos
CREATE TABLE IF NOT EXISTS competition_photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    uploader_id UUID NOT NULL REFERENCES participants(id) ON DELETE SET NULL,
    url TEXT NOT NULL,
    cloudinary_url TEXT,
    cloudinary_public_id TEXT,
    cloudinary_resource_type TEXT DEFAULT 'image',
    description TEXT,
    moderation_status TEXT DEFAULT 'pending',
    approved BOOLEAN DEFAULT FALSE,
    featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add comments for documentation
COMMENT ON TABLE competition_photos IS 'User-submitted photos for competitions';
COMMENT ON COLUMN competition_photos.uploader_id IS 'ID of the participant who uploaded the photo';
COMMENT ON COLUMN competition_photos.url IS 'Original source URL of the photo';
COMMENT ON COLUMN competition_photos.cloudinary_url IS 'URL of the photo in Cloudinary';
COMMENT ON COLUMN competition_photos.cloudinary_public_id IS 'Cloudinary public ID for the photo';
COMMENT ON COLUMN competition_photos.description IS 'User-provided description of the photo';
COMMENT ON COLUMN competition_photos.moderation_status IS 'Status of content moderation (pending, approved, rejected)';
COMMENT ON COLUMN competition_photos.approved IS 'Whether the photo has been approved by a moderator';
COMMENT ON COLUMN competition_photos.featured IS 'Whether the photo is featured on the competition page';

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS competition_photos_competition_id_idx ON competition_photos(competition_id);
CREATE INDEX IF NOT EXISTS competition_photos_uploader_id_idx ON competition_photos(uploader_id);
CREATE INDEX IF NOT EXISTS competition_photos_approved_idx ON competition_photos(approved);
CREATE INDEX IF NOT EXISTS competition_photos_featured_idx ON competition_photos(featured);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_competition_photos_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER competition_photos_updated_at
BEFORE UPDATE ON competition_photos
FOR EACH ROW
EXECUTE FUNCTION update_competition_photos_updated_at(); 
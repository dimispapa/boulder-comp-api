-- LEGACY SQL MIGRATION FILE FOR LEGACY DATABASE ON SUPABASE - DO NOT USE

-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS boulder_beasts_rankings CASCADE;
DROP TABLE IF EXISTS marathon_rankings CASCADE;
DROP TABLE IF EXISTS scored_ascents CASCADE;
DROP TABLE IF EXISTS master_grade_bonus CASCADE;
DROP TABLE IF EXISTS team_ascent_bonus CASCADE;
DROP TABLE IF EXISTS unique_ascent_bonus CASCADE;
DROP TABLE IF EXISTS volume_bonus CASCADE;
DROP TABLE IF EXISTS base_points CASCADE;
DROP TABLE IF EXISTS ascents CASCADE;
DROP TABLE IF EXISTS participants CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
DROP TABLE IF EXISTS competitions CASCADE;
DROP TABLE IF EXISTS routes CASCADE;
DROP TABLE IF EXISTS boulder_photos CASCADE;
DROP TABLE IF EXISTS competition_photos CASCADE;
DROP TABLE IF EXISTS boulder_sector_mappings CASCADE;
DROP TABLE IF EXISTS boulders CASCADE;
DROP TABLE IF EXISTS sectors CASCADE;
DROP TABLE IF EXISTS crags CASCADE;
-- Drop enum types
DROP TYPE IF EXISTS competition_status CASCADE;
DROP TYPE IF EXISTS competition_category CASCADE;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Create enum types
CREATE TYPE competition_status AS ENUM ('upcoming', 'ongoing', 'completed');
CREATE TYPE competition_category AS ENUM ('marathon', 'boulder_beasts');

-- Create crags table
CREATE TABLE crags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create sectors table
CREATE TABLE sectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL UNIQUE,
    crag_id UUID NOT NULL REFERENCES crags(id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert initial crags
INSERT INTO crags (id, name, display_name) VALUES
    (uuid_generate_v4(), 'inia-droushia', 'Inia Droushia');

-- Insert initial sectors
INSERT INTO sectors (id, name, display_name, crag_id) VALUES
    (uuid_generate_v4(), 'inia', 'Inia', (SELECT id FROM crags WHERE name = 'inia-droushia')),
    (uuid_generate_v4(), 'pano-droushia', 'Pano Droushia', (SELECT id FROM crags WHERE name = 'inia-droushia')),
    (uuid_generate_v4(), 'kato-droushia', 'Kato Droushia', (SELECT id FROM crags WHERE name = 'inia-droushia')),
    (uuid_generate_v4(), 'alikou', 'Alikou', (SELECT id FROM crags WHERE name = 'inia-droushia')),
    (uuid_generate_v4(), 'kari', 'Kari', (SELECT id FROM crags WHERE name = 'inia-droushia')),
    (uuid_generate_v4(), 'gerakopetra', 'Gerakopetra', (SELECT id FROM crags WHERE name = 'inia-droushia')),
    (uuid_generate_v4(), 'pano-akamas', 'Pano Akamas', (SELECT id FROM crags WHERE name = 'inia-droushia')),
    (uuid_generate_v4(), 'panorama', 'Panorama', (SELECT id FROM crags WHERE name = 'inia-droushia'));

-- Create boulders table
CREATE TABLE boulders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sector_id UUID NOT NULL REFERENCES sectors(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    gps_postgis GEOGRAPHY(POINT),
    gps_string TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create boulder-sector mapping table
CREATE TABLE boulder_sector_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    boulder_url TEXT NOT NULL UNIQUE,
    sector_name TEXT NOT NULL,
    sector_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Add constraints to ensure data integrity
    CONSTRAINT fk_sector_name FOREIGN KEY (sector_name) REFERENCES sectors(name),
    CONSTRAINT fk_sector_id FOREIGN KEY (sector_id) REFERENCES sectors(id)
);

-- Add a trigger to automatically populate sector_id when sector_name is inserted/updated
CREATE OR REPLACE FUNCTION set_sector_id_from_name() 
RETURNS TRIGGER AS $$
BEGIN
    -- Look up the sector_id based on the sector_name
    SELECT id INTO NEW.sector_id FROM sectors WHERE name = NEW.sector_name;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_insert_or_update_boulder_sector_mappings
BEFORE INSERT OR UPDATE ON boulder_sector_mappings
FOR EACH ROW
EXECUTE FUNCTION set_sector_id_from_name();

-- Create boulder_photos table
CREATE TABLE boulder_photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    boulder_id UUID NOT NULL REFERENCES boulders(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    photo_id TEXT NOT NULL,
    cloudinary_url TEXT,
    cloudinary_public_id TEXT,
    cloudinary_resource_type TEXT DEFAULT 'image',
    lines_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(boulder_id, photo_id)
);
-- Add comment for documentation
COMMENT ON COLUMN boulder_photos.cloudinary_url IS 'URL of the photo in Cloudinary, populated after successful upload';
COMMENT ON COLUMN boulder_photos.cloudinary_public_id IS 'Cloudinary public ID (used for referencing the image in Cloudinary APIs)';
COMMENT ON COLUMN boulder_photos.cloudinary_resource_type IS 'Cloudinary resource type (image, video, etc.)';

-- Create routes table
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    boulder_id UUID NOT NULL REFERENCES boulders(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    grade TEXT NOT NULL,
    rating FLOAT,
    description TEXT,
    line_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create competitions table
CREATE TABLE competitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    crag_id UUID NOT NULL REFERENCES crags(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL UNIQUE,
    categories competition_category[] NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status competition_status NOT NULL DEFAULT 'ongoing',
    description TEXT,
    venue TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT categories_not_empty CHECK (array_length(categories, 1) > 0)
);

-- Add documentation comments for the competitions table
COMMENT ON COLUMN competitions.categories IS 'Competition categories: ["marathon"], ["boulder_beasts"], or ["marathon", "boulder_beasts"]. Must select at least one.';
COMMENT ON CONSTRAINT categories_not_empty ON competitions IS 'Ensures at least one category is selected';
COMMENT ON COLUMN competitions.status IS 'Competition status: "upcoming", "ongoing", or "completed". Automatically updated based on dates, except "completed" which must be set manually.';

-- Create function to update competition status based on dates
CREATE OR REPLACE FUNCTION update_competition_status()
RETURNS TRIGGER AS $$
DECLARE
    current_date DATE := CURRENT_DATE;
BEGIN
    -- If this is an UPDATE operation and status is already 'completed', don't change it
    IF TG_OP = 'UPDATE' AND OLD.status = 'completed' THEN
        RETURN NEW;
    END IF;
    
    -- If the user has explicitly set status to 'completed' in this operation, respect that
    IF NEW.status = 'completed' THEN
        RETURN NEW;
    END IF;
    
    -- Set status based on current date relative to start/end dates
    IF current_date < NEW.start_date THEN
        NEW.status := 'upcoming';
    ELSIF current_date >= NEW.start_date AND current_date <= NEW.end_date THEN
        NEW.status := 'ongoing';
    END IF;
    
    -- Note: We don't automatically set to 'completed'
    -- This must be done manually
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to run the function
CREATE TRIGGER update_competition_status_trigger
BEFORE INSERT OR UPDATE ON competitions
FOR EACH ROW
EXECUTE FUNCTION update_competition_status();

-- Example of inserting a competition with multiple categories
-- This demonstrates the proper syntax for the categories array
-- COMMENT OUT BEFORE RUNNING IN PRODUCTION
-- INSERT INTO competitions (name, crag_id, display_name, categories, start_date, end_date, description, venue)
-- VALUES (
--     'example-competition',
--     (SELECT id FROM crags WHERE name = 'inia-droushia'),
--     'Example Competition',
--     ["marathon", "boulder_beasts"],
--     '2025-05-01',
--     '2025-05-15',
--     'This is an example competition with multiple categories',
--     'Inia Droushia'
-- );

-- Create teams table
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    captain_id UUID,
    category TEXT NOT NULL DEFAULT 'marathon',
    team_size INTEGER,
    paid BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create participants table
CREATE TABLE participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    solo_entry BOOLEAN NOT NULL DEFAULT FALSE,
    club_member BOOLEAN NOT NULL DEFAULT FALSE,
    membership_number TEXT,
    paid BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create function to update team size based on participant count
CREATE OR REPLACE FUNCTION update_team_size()
RETURNS TRIGGER AS $$
BEGIN
    -- If a participant was added or removed from a team
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') AND NEW.team_id IS NOT NULL THEN
        -- Update the team size for the team this participant was added to
        UPDATE teams 
        SET team_size = (
            SELECT COUNT(*) 
            FROM participants 
            WHERE team_id = NEW.team_id
        ),
        updated_at = NOW()
        WHERE id = NEW.team_id;
    END IF;
    
    -- If a participant was removed or changed teams
    IF (TG_OP = 'UPDATE' OR TG_OP = 'DELETE') AND 
       (TG_OP = 'DELETE' OR OLD.team_id IS DISTINCT FROM NEW.team_id) AND
       OLD.team_id IS NOT NULL THEN
        -- Update the team size for the team this participant was removed from
        UPDATE teams 
        SET team_size = (
            SELECT COUNT(*) 
            FROM participants 
            WHERE team_id = OLD.team_id
        ),
        updated_at = NOW()
        WHERE id = OLD.team_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to run the function
CREATE TRIGGER update_team_size_trigger
AFTER INSERT OR UPDATE OR DELETE ON participants
FOR EACH ROW
EXECUTE FUNCTION update_team_size();

-- Create ascents table
CREATE TABLE ascents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    route_id UUID NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create function to automatically set team_id from participant
CREATE OR REPLACE FUNCTION set_ascent_team_id()
RETURNS TRIGGER AS $$
BEGIN
    -- Look up the team_id from the participant
    SELECT team_id INTO NEW.team_id 
    FROM participants 
    WHERE id = NEW.participant_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to run the function
CREATE TRIGGER before_insert_or_update_ascents
BEFORE INSERT OR UPDATE ON ascents
FOR EACH ROW
EXECUTE FUNCTION set_ascent_team_id();

-- Create scoring configuration tables
CREATE TABLE base_points (
    grade TEXT PRIMARY KEY,
    points INTEGER NOT NULL,
    increment_factor FLOAT
);

CREATE TABLE volume_bonus (
    bonus_increment INTEGER PRIMARY KEY,
    points_per_increment INTEGER NOT NULL
);

CREATE TABLE unique_ascent_bonus (
    bonus_factor FLOAT PRIMARY KEY
);

CREATE TABLE team_ascent_bonus (
    team_size INTEGER PRIMARY KEY,
    bonus_factor FLOAT NOT NULL
);

CREATE TABLE master_grade_bonus (
    bonus_factor FLOAT PRIMARY KEY
);

-- Create scoring result tables
CREATE TABLE scored_ascents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ascent_id UUID NOT NULL REFERENCES ascents(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    route_id UUID NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    base_points FLOAT NOT NULL,
    volume_bonus FLOAT NOT NULL,
    unique_bonus FLOAT NOT NULL,
    total_points FLOAT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE marathon_rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    base_score FLOAT NOT NULL,
    volume_score FLOAT NOT NULL,
    unique_ascent_score FLOAT NOT NULL,
    team_ascent_bonus FLOAT NOT NULL,
    master_grade_bonus FLOAT NOT NULL,
    total_score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE boulder_beasts_rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    top_grades TEXT[] NOT NULL,
    total_score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create competition_photos table for user-submitted photos
CREATE TABLE competition_photos (
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

-- Create updated_at trigger for competition_photos
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

-- Create indexes for better query performance
CREATE INDEX idx_sectors_name ON sectors(name);
CREATE INDEX idx_boulders_sector_id ON boulders(sector_id);
CREATE INDEX idx_boulder_photos_boulder_id ON boulder_photos(boulder_id);
CREATE INDEX idx_routes_boulder_id ON routes(boulder_id);
CREATE INDEX idx_teams_competition_id ON teams(competition_id);
CREATE INDEX idx_participants_competition_id ON participants(competition_id);
CREATE INDEX idx_participants_team_id ON participants(team_id);
CREATE INDEX idx_ascents_competition_id ON ascents(competition_id);
CREATE INDEX idx_ascents_participant_id ON ascents(participant_id);
CREATE INDEX idx_ascents_route_id ON ascents(route_id);
CREATE INDEX idx_scored_ascents_ascent_id ON scored_ascents(ascent_id);
CREATE INDEX idx_scored_ascents_participant_id ON scored_ascents(participant_id);
CREATE INDEX idx_scored_ascents_route_id ON scored_ascents(route_id);
CREATE INDEX idx_marathon_rankings_competition_id ON marathon_rankings(competition_id);
CREATE INDEX idx_marathon_rankings_team_id ON marathon_rankings(team_id);
CREATE INDEX idx_boulder_beasts_rankings_competition_id ON boulder_beasts_rankings(competition_id);
CREATE INDEX idx_boulder_beasts_rankings_participant_id ON boulder_beasts_rankings(participant_id);
CREATE INDEX idx_boulder_sector_mappings_url ON boulder_sector_mappings(boulder_url);
CREATE INDEX idx_boulder_sector_mappings_sector_id ON boulder_sector_mappings(sector_id);
CREATE INDEX idx_sectors_crag_id ON sectors(crag_id);
CREATE INDEX idx_competitions_crag_id ON competitions(crag_id);
CREATE INDEX idx_boulder_photos_cloudinary_url ON boulder_photos(cloudinary_url);
CREATE INDEX idx_competition_photos_competition_id ON competition_photos(competition_id);
CREATE INDEX idx_competition_photos_uploader_id ON competition_photos(uploader_id);
CREATE INDEX idx_competition_photos_approved ON competition_photos(approved);
CREATE INDEX idx_competition_photos_featured ON competition_photos(featured);
CREATE INDEX idx_ascents_team_id ON ascents(team_id);

-- Create RLS (Row Level Security) policies
ALTER TABLE crags ENABLE ROW LEVEL SECURITY;
ALTER TABLE sectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE boulders ENABLE ROW LEVEL SECURITY;
ALTER TABLE boulder_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE ascents ENABLE ROW LEVEL SECURITY;
ALTER TABLE scored_ascents ENABLE ROW LEVEL SECURITY;
ALTER TABLE marathon_rankings ENABLE ROW LEVEL SECURITY;
ALTER TABLE boulder_beasts_rankings ENABLE ROW LEVEL SECURITY;
ALTER TABLE competition_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE boulder_sector_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE base_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE volume_bonus ENABLE ROW LEVEL SECURITY;
ALTER TABLE unique_ascent_bonus ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_ascent_bonus ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_grade_bonus ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access
CREATE POLICY "Public read access for crags" ON crags
    FOR SELECT USING (true);

CREATE POLICY "Public read access for sectors" ON sectors
    FOR SELECT USING (true);

CREATE POLICY "Public read access for boulders" ON boulders
    FOR SELECT USING (true);

CREATE POLICY "Public read access for boulder_photos" ON boulder_photos
    FOR SELECT USING (true);

CREATE POLICY "Public read access for routes" ON routes
    FOR SELECT USING (true);

CREATE POLICY "Public read access for competitions" ON competitions
    FOR SELECT USING (true);

CREATE POLICY "Public read access for teams" ON teams
    FOR SELECT USING (true);

CREATE POLICY "Public read access for participants" ON participants
    FOR SELECT USING (true);

CREATE POLICY "Public read access for ascents" ON ascents
    FOR SELECT USING (true);

CREATE POLICY "Public read access for scored_ascents" ON scored_ascents
    FOR SELECT USING (true);

CREATE POLICY "Public read access for marathon_rankings" ON marathon_rankings
    FOR SELECT USING (true);

CREATE POLICY "Public read access for boulder_beasts_rankings" ON boulder_beasts_rankings
    FOR SELECT USING (true);

CREATE POLICY "Public read access for competition_photos" ON competition_photos
    FOR SELECT USING (approved = true);

-- Create policies for authenticated write access
CREATE POLICY "Authenticated write access for ascents" ON ascents
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated write access for participants" ON participants
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated write access for teams" ON teams
    FOR ALL USING (auth.role() = 'authenticated');

-- Create policies for admin access
CREATE POLICY "Admin access for all tables" ON crags
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON sectors
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON boulders
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON boulder_photos
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON routes
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON competitions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON teams
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON participants
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON ascents
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON scored_ascents
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON marathon_rankings
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON boulder_beasts_rankings
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admin access for all tables" ON competition_photos
    FOR ALL USING (auth.role() = 'service_role');

-- Insert default scoring configuration
INSERT INTO base_points (grade, points, increment_factor) VALUES
    ('3', 5, 1.2),
    ('3+', 6, 1.2),
    ('4', 7, 1.2),
    ('4+', 8, 1.2),
    ('5', 10, 1.2),
    ('5+', 12, 1.2),
    ('6A', 14, 1.2),
    ('6A+', 17, 1.2),
    ('6B', 20, 1.2),
    ('6B+', 24, 1.2),
    ('6C', 29, 1.2),
    ('6C+', 35, 1.2),
    ('7A', 42, 1.2),
    ('7A+', 50, 1.2),
    ('7B', 60, 1.2),
    ('7B+', 72, 1.2),
    ('7C', 86, 1.2),
    ('7C+', 103, 1.2),
    ('8A', 124, 1.2),
    ('8A+', 149, 1.2),
    ('8B', 179, 1.2),
    ('8B+', 215, 1.2),
    ('8C', 258, 1.2),
    ('8C+', 310, 1.2),
    ('9A', 372, 1.2);

INSERT INTO volume_bonus (bonus_increment, points_per_increment) VALUES
    (5, 25);

INSERT INTO unique_ascent_bonus (bonus_factor) VALUES
    (1.0);

INSERT INTO team_ascent_bonus (team_size, bonus_factor) VALUES
    (2, 0.10),
    (3, 0.18),
    (4, 0.28);

INSERT INTO master_grade_bonus (bonus_factor) VALUES
    (0.50);
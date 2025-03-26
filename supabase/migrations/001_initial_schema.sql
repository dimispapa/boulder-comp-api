-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Create enum types
CREATE TYPE competition_status AS ENUM ('ongoing', 'completed');
CREATE TYPE competition_category AS ENUM ('marathon', 'boulder_beasts');

-- Create sectors table
CREATE TABLE sectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    gps_coords GEOGRAPHY(POINT),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create boulders table
CREATE TABLE boulders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    sector_id UUID NOT NULL REFERENCES sectors(id) ON DELETE RESTRICT,
    gps_coords GEOGRAPHY(POINT),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create boulder_photos table
CREATE TABLE boulder_photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    boulder_id UUID NOT NULL REFERENCES boulders(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    caption TEXT,
    "order" INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create routes table
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    boulder_id UUID NOT NULL REFERENCES boulders(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    grade TEXT NOT NULL,
    rating FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create competitions table
CREATE TABLE competitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    category TEXT[] NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status competition_status NOT NULL DEFAULT 'ongoing',
    description TEXT,
    venue TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create teams table
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    captain_id UUID,
    category TEXT NOT NULL DEFAULT 'marathon',
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

-- Create ascents table
CREATE TABLE ascents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    route_id UUID NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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
    top_grades TEXT[] NOT NULL,
    total_score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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

-- Create RLS (Row Level Security) policies
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

-- Create policies for public read access
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

-- Create policies for authenticated write access
CREATE POLICY "Authenticated write access for ascents" ON ascents
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated write access for participants" ON participants
    FOR ALL USING (auth.role() = 'authenticated');

-- Create policies for admin access
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
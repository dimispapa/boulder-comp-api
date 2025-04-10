CREATE OR REPLACE FUNCTION set_participant_team_validity()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.team_id IS NOT NULL THEN
        -- Get team validity
        SELECT is_valid INTO NEW.team_is_valid 
        FROM teams 
        WHERE id = NEW.team_id;
    ELSE
        -- No team
        NEW.team_is_valid := NULL;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_participant_team_validity ON participants;
CREATE TRIGGER trigger_set_participant_team_validity
BEFORE INSERT OR UPDATE OF team_id ON participants
FOR EACH ROW
EXECUTE FUNCTION set_participant_team_validity(); 
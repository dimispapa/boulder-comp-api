CREATE OR REPLACE FUNCTION update_participants_team_validity()
RETURNS TRIGGER AS $$
BEGIN
    -- When a team's is_valid changes, update all its participants
    UPDATE participants
    SET team_is_valid = NEW.is_valid
    WHERE team_id = NEW.id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_participants_team_validity ON teams;
CREATE TRIGGER trigger_update_participants_team_validity
AFTER UPDATE OF is_valid ON teams
FOR EACH ROW
EXECUTE FUNCTION update_participants_team_validity(); 
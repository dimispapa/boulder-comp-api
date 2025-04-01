-- Create the boulder-photos storage bucket if it doesn't exist
INSERT INTO storage.buckets (id, name, public, avif_autodetection, owner)
VALUES ('boulder-photos', 'boulder-photos', FALSE, TRUE, NULL)
ON CONFLICT (id) DO NOTHING;

-- Disable public access to the entire bucket
UPDATE storage.buckets SET public = FALSE WHERE id = 'boulder-photos';

-- Enable RLS on the bucket
UPDATE storage.buckets SET enable_row_level_security = TRUE WHERE id = 'boulder-photos';

-- Create policy for authenticated users to upload photos (service role and admin only)
CREATE POLICY "Admin can upload photos" ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'boulder-photos' AND 
  (auth.role() = 'service_role' OR auth.role() = 'authenticated' AND auth.uid() IN (
    SELECT auth.uid() FROM auth.users WHERE auth.email() IN (
      SELECT email FROM auth.users WHERE id IN (
        SELECT user_id FROM auth.users_admin_roles WHERE role = 'admin'
      )
    )
  ))
);

-- Allow admins to update photos
CREATE POLICY "Admin can update photos" ON storage.objects
FOR UPDATE TO authenticated
USING (
  bucket_id = 'boulder-photos' AND 
  (auth.role() = 'service_role' OR auth.role() = 'authenticated' AND auth.uid() IN (
    SELECT auth.uid() FROM auth.users WHERE auth.email() IN (
      SELECT email FROM auth.users WHERE id IN (
        SELECT user_id FROM auth.users_admin_roles WHERE role = 'admin'
      )
    )
  ))
);

-- Create policy for authenticated users to view photos based on competition participation
CREATE POLICY "Participants can view competition photos" ON storage.objects
FOR SELECT TO authenticated
USING (
  bucket_id = 'boulder-photos' AND
  EXISTS (
    SELECT 1 FROM participants p
    JOIN competitions c ON p.competition_id = c.id
    JOIN crags cr ON c.crag_id = cr.id
    -- Check if the path starts with the crag name which associates with the participant's competition
    WHERE (storage.foldername(name))[1] = cr.name
    AND p.email = auth.email()
  )
);

-- Create policy for service_role to access all photos
CREATE POLICY "Service role full access" ON storage.objects
FOR ALL TO service_role
USING (bucket_id = 'boulder-photos')
WITH CHECK (bucket_id = 'boulder-photos');

-- Create policy for admin to view all photos
CREATE POLICY "Admin can view all photos" ON storage.objects
FOR SELECT TO authenticated
USING (
  bucket_id = 'boulder-photos' AND
  auth.uid() IN (
    SELECT auth.uid() FROM auth.users WHERE auth.email() IN (
      SELECT email FROM auth.users WHERE id IN (
        SELECT user_id FROM auth.users_admin_roles WHERE role = 'admin'
      )
    )
  )
);

-- Create a table to track user roles (if it doesn't exist already)
CREATE TABLE IF NOT EXISTS auth.users_admin_roles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, role)
);

-- Grant access to the roles table
GRANT ALL ON auth.users_admin_roles TO postgres, authenticated, service_role; 
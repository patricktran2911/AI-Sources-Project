-- Re-apply the user password using md5 so it matches the pg_hba.conf auth method.
-- The initial user creation by Docker uses scram-sha-256 (default).
-- This script runs after startup with password_encryption=md5 already active,
-- so ALTER USER re-hashes the password in md5 format.
DO $$
DECLARE
  v_user TEXT := current_user;
  v_pass TEXT := 'aipassword';
BEGIN
  -- Use md5 for this session to ensure hash is stored as md5
  SET LOCAL password_encryption = 'md5';
  EXECUTE format('ALTER USER %I WITH PASSWORD %L', v_user, v_pass);
END $$;

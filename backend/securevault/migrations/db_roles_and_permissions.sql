-- ==============================================================================
-- CloudOpt PostgreSQL Owner vs. Runtime Role Separation Runbook
-- ==============================================================================
-- Purpose:
--   1. Separate migration/DDL administrative operations (cloudopt_owner)
--      from runtime web application traffic (cloudopt_app).
--   2. Enforce DB-level append-only protection on audit_logs:
--      cloudopt_app can NEVER UPDATE, DELETE, or TRUNCATE audit_logs rows.
--
-- Execution Runbook:
--   Step 1: Connect as database superuser / postgres admin (e.g. Supabase postgres).
--   Step 2: Replace '<OWNER_PASSWORD>' and '<APP_PASSWORD>' with secure secrets from Vault/KMS.
--   Step 3: Run this script against your target database (staging/production).
--   Step 4: Configure CI / migration runner env:
--           MIGRATION_DATABASE_URL=postgresql://cloudopt_owner:<OWNER_PASSWORD>@<host>:5432/<dbname>
--   Step 5: Configure application runtime web service env:
--           DATABASE_URL=postgresql://cloudopt_app:<APP_PASSWORD>@<host>:5432/<dbname>
-- ==============================================================================

BEGIN;

-- 1. Create Roles (if they do not already exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cloudopt_owner') THEN
        CREATE ROLE cloudopt_owner WITH LOGIN PASSWORD '<OWNER_PASSWORD>' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cloudopt_app') THEN
        CREATE ROLE cloudopt_app WITH LOGIN PASSWORD '<APP_PASSWORD>' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;

-- 2. Schema Ownership and Usage
ALTER SCHEMA public OWNER TO cloudopt_owner;
GRANT USAGE, CREATE ON SCHEMA public TO cloudopt_owner;
GRANT USAGE ON SCHEMA public TO cloudopt_app;

-- 3. Revoke default public schema privileges from public role
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- 4. Transfer ownership of all existing tables and sequences to cloudopt_owner
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO cloudopt_owner;', r.tablename);
    END LOOP;
    FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO cloudopt_owner;', r.sequence_name);
    END LOOP;
END
$$;

-- 5. Set default privileges for objects created by cloudopt_owner in the future
ALTER DEFAULT PRIVILEGES FOR ROLE cloudopt_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cloudopt_app;

ALTER DEFAULT PRIVILEGES FOR ROLE cloudopt_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO cloudopt_app;

-- 6. Grant standard CRUD permissions on existing application tables to cloudopt_app
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cloudopt_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cloudopt_app;

-- 7. Hardened Append-Only Permissions for audit_logs
-- Explicitly REVOKE UPDATE, DELETE, and TRUNCATE from the runtime role.
REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.audit_logs FROM cloudopt_app;

-- Verify cloudopt_app has only SELECT and INSERT on audit_logs
GRANT SELECT, INSERT ON TABLE public.audit_logs TO cloudopt_app;

COMMIT;


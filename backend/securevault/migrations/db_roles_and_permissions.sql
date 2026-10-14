-- ==============================================================================
-- CloudOpt PostgreSQL Owner vs. Runtime Role Separation & RLS Runbook
-- ==============================================================================
-- Purpose:
--   1. Separate migration/DDL administrative operations (cloudopt_owner)
--      from runtime web application traffic (cloudopt_app).
--   2. Enforce DB-level append-only protection on audit_logs:
--      cloudopt_app can NEVER UPDATE, DELETE, or TRUNCATE audit_logs rows.
--   3. Enable Row-Level Security (RLS) on all application tables.
--   4. Revoke access from default PostgREST roles (anon, authenticated)
--      to prevent accidental exposure via Supabase Data APIs.
--   5. Connection Architecture Guidance:
--      - Render API & Celery Worker: Use Supabase Session Pooler (port 5432) or
--        Direct Connection (port 5432). DO NOT use Transaction Pooler (port 6543)
--        for migrations or Celery task locks, as PgBouncer in transaction mode
--        does not support prepared statements, LISTEN/NOTIFY, or advisory locks.
--
-- Execution Runbook:
--   Step 1: Connect as database superuser / postgres admin in Supabase SQL Editor.
--   Step 2: Replace '<OWNER_PASSWORD>' and '<APP_PASSWORD>' with secure secrets from Vault/KMS.
--   Step 3: Run this script against your target database (staging/production).
--   Step 4: Configure CI / migration runner env:
--           MIGRATION_DATABASE_URL=postgresql://cloudopt_owner:<OWNER_PASSWORD>@<host>:5432/<dbname>
--   Step 5: Configure application runtime web service env:
--           DATABASE_URL=postgresql://cloudopt_app:<APP_PASSWORD>@<host>:5432/<dbname>
-- ==============================================================================

BEGIN;

-- 1. Create Dedicated Roles (if they do not already exist)
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

-- 8. Revoke all privileges from Supabase PostgREST roles (anon, authenticated)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
        REVOKE ALL ON SCHEMA public FROM anon;
    END IF;
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
        REVOKE ALL ON SCHEMA public FROM authenticated;
    END IF;
END
$$;

-- 9. Enable Row-Level Security (RLS) and define cloudopt_app policy
DO $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', t.tablename);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I;', 'cloudopt_app_policy_' || t.tablename, t.tablename);
        EXECUTE format('CREATE POLICY %I ON public.%I FOR ALL TO cloudopt_app USING (true) WITH CHECK (true);', 'cloudopt_app_policy_' || t.tablename, t.tablename);
    END LOOP;
END
$$;

COMMIT;

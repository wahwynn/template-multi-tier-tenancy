-- Shared schema for non-tenant Django operations (auth, contenttypes, django_migrations).
-- Runs once at database creation time as the postgres superuser.

CREATE SCHEMA IF NOT EXISTS shared;
GRANT ALL ON SCHEMA shared TO app;

-- Set the default search_path for the app role so that plain
-- manage.py migrate writes to shared instead of public.
ALTER ROLE app SET search_path TO shared, public;

-- Lock public: prevent the app user from creating tables there.
-- (PostgreSQL 15+ revokes CREATE on public from PUBLIC by default;
-- this is explicit for clarity and older versions.)
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM app;

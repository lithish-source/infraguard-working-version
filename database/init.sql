-- ============================================================
-- InfraGuard — Database initialization script
-- Usage: psql -U postgres -f init.sql
-- ============================================================

-- Create role + database (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'infraguard') THEN
        CREATE ROLE infraguard WITH LOGIN PASSWORD 'infraguard' CREATEDB;
    END IF;
END $$;

-- Connect to default DB to create the app DB if missing
SELECT 'CREATE DATABASE infraguard OWNER infraguard'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'infraguard')\gexec

\c infraguard

-- Enable extensions (requires superuser; run as postgres if it fails)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Run schema + seed
\i schema.sql
\i seed.sql

\echo 'InfraGuard database initialized successfully.'

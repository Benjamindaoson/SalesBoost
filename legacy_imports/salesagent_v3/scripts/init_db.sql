-- SalesAgent V3 Database Initialization Script
-- This script runs automatically when PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For JSONB indexing
CREATE EXTENSION IF NOT EXISTS "vector";

SELECT 'CREATE DATABASE salesagent_test OWNER salesagent'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'salesagent_test')\gexec

\connect salesagent_test
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "vector";

\connect salesagent

-- Set timezone
SET timezone = 'UTC';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE salesagent TO salesagent;
GRANT ALL PRIVILEGES ON DATABASE salesagent_test TO salesagent;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS public;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'SalesAgent V3 database initialized successfully';
END $$;

-- Football Coach Bot Database Setup Script
-- Run this with: psql -U postgres -h localhost -f setup_database.sql

-- Create database
CREATE DATABASE football_coach_bot;

-- Create user with password
CREATE USER footballbot WITH ENCRYPTED PASSWORD 'SecureBot123!';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE football_coach_bot TO footballbot;

-- Allow user to create databases (for testing)
ALTER USER footballbot CREATEDB;

-- Connect to the new database
\c football_coach_bot

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO footballbot;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO footballbot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO footballbot;

-- Display success message
SELECT 'Database setup completed successfully!' AS status;

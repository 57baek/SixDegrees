-- v1.2 Phase 14-01: Add timezone column to profiles table
-- Created: 2026-02-25
-- Purpose: profiles table lacks a timezone column. Backend scheduler uses timezone
--          to determine active hours per user. Adding timezone (TEXT NOT NULL DEFAULT 'UTC')
--          allows the scheduler to read from profiles.timezone after the user_profiles
--          → profiles migration is complete.
-- Migration name: add_timezone_to_profiles
-- Safe to re-run (ADD COLUMN IF NOT EXISTS)

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC';

-- Verification query:
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'profiles' AND column_name = 'timezone';
-- Expected: column_name='timezone', data_type='text', column_default='UTC'

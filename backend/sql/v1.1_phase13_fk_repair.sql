-- v1.1 Phase 13: FK Repair — posts.user_id and comments.user_id
-- Created: 2026-02-24
-- Purpose: Drop stale FK constraints on posts and comments, then add
--          correct FKs targeting profiles.id.
--          PostgREST resolves embedded joins by following FK relationships; without
--          correct FKs pointing to profiles, joins like profiles(display_name)
--          return null — causing 'Unknown User' / 'Unknown' in the UI.
-- Requirements covered: FEND-04 (post author names), FEND-05 (comment author names)
-- Safe to re-run (idempotent throughout — all changes guarded by IF (NOT) EXISTS checks)


-- ============================================================
-- Section 1: Drop stale FK on posts (if exists)
-- ============================================================

DO $$
BEGIN
    -- Drop posts_user_profile_fk if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'posts_user_profile_fk'
          AND table_name = 'posts'
          AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.posts DROP CONSTRAINT posts_user_profile_fk;
    END IF;

    -- Drop posts_user_id_fkey if it exists (Postgres auto-naming convention)
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'posts_user_id_fkey'
          AND table_name = 'posts'
          AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.posts DROP CONSTRAINT posts_user_id_fkey;
    END IF;
END $$;


-- ============================================================
-- Section 2: Add correct FK on posts → profiles
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_posts_profiles'
          AND table_name = 'posts'
          AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.posts
            ADD CONSTRAINT fk_posts_profiles
            FOREIGN KEY (user_id) REFERENCES public.profiles(id);
    END IF;
END $$;


-- ============================================================
-- Section 3: Drop stale FK on comments (if exists)
-- ============================================================

DO $$
BEGIN
    -- Drop comments_user_id_fkey if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'comments_user_id_fkey'
          AND table_name = 'comments'
          AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.comments DROP CONSTRAINT comments_user_id_fkey;
    END IF;

    -- Drop comments_user_profile_fk if it exists (alternate naming)
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'comments_user_profile_fk'
          AND table_name = 'comments'
          AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.comments DROP CONSTRAINT comments_user_profile_fk;
    END IF;
END $$;


-- ============================================================
-- Section 4: Add correct FK on comments → profiles
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_comments_profiles'
          AND table_name = 'comments'
          AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.comments
            ADD CONSTRAINT fk_comments_profiles
            FOREIGN KEY (user_id) REFERENCES public.profiles(id);
    END IF;
END $$;


-- ============================================================
-- Section 5: Verification query
-- Shows both new FK constraints with their referencing and referenced tables.
-- Expected: 2 rows — posts → profiles and comments → profiles.
-- ============================================================

SELECT
    rc.constraint_name,
    kcu.table_name   AS referencing_table,
    kcu.column_name  AS referencing_column,
    ccu.table_name   AS referenced_table
FROM information_schema.referential_constraints rc
JOIN information_schema.key_column_usage kcu
    ON rc.constraint_name = kcu.constraint_name
   AND kcu.table_schema = 'public'
JOIN information_schema.constraint_column_usage ccu
    ON rc.unique_constraint_name = ccu.constraint_name
   AND ccu.table_schema = 'public'
WHERE rc.constraint_name IN ('fk_posts_profiles', 'fk_comments_profiles')
ORDER BY kcu.table_name;

-- v2.0 Phase 20: interactions rebuild + profiles FK contract
-- Created: 2026-02-26
-- Safe to re-run (idempotent migration and constraint guards).

-- -----------------------------------------------------------------------------
-- 1) Remove legacy FK dependencies and rebuild interactions baseline
-- -----------------------------------------------------------------------------

DO $$
DECLARE
    fk_row RECORD;
BEGIN
    -- Drop any interactions FK that still points to user_profiles.
    FOR fk_row IN
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.referential_constraints rc
            ON rc.constraint_name = tc.constraint_name
           AND rc.constraint_schema = tc.constraint_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = rc.unique_constraint_name
           AND ccu.constraint_schema = rc.unique_constraint_schema
        WHERE tc.table_schema = 'public'
          AND tc.table_name = 'interactions'
          AND tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_schema = 'public'
          AND ccu.table_name = 'user_profiles'
    LOOP
        EXECUTE format(
            'ALTER TABLE public.interactions DROP CONSTRAINT IF EXISTS %I',
            fk_row.constraint_name
        );
    END LOOP;
END $$;

TRUNCATE TABLE public.interactions;

WITH profile_users AS (
    SELECT id
    FROM public.profiles
),
eligible_posts AS (
    SELECT p.id, p.user_id AS author_id
    FROM public.posts p
    JOIN profile_users pu ON pu.id = p.user_id
),
like_events AS (
    SELECT
        LEAST(l.user_id, ep.author_id) AS user_id_a,
        GREATEST(l.user_id, ep.author_id) AS user_id_b,
        1::INTEGER AS likes_count,
        0::INTEGER AS comments_count,
        0::INTEGER AS dm_count
    FROM public.likes l
    JOIN eligible_posts ep ON ep.id = l.post_id
    JOIN profile_users actor ON actor.id = l.user_id
    WHERE l.user_id <> ep.author_id
),
comment_events AS (
    SELECT
        LEAST(c.user_id, ep.author_id) AS user_id_a,
        GREATEST(c.user_id, ep.author_id) AS user_id_b,
        0::INTEGER AS likes_count,
        1::INTEGER AS comments_count,
        0::INTEGER AS dm_count
    FROM public.comments c
    JOIN eligible_posts ep ON ep.id = c.post_id
    JOIN profile_users actor ON actor.id = c.user_id
    WHERE c.user_id <> ep.author_id
),
aggregated AS (
    SELECT
        user_id_a,
        user_id_b,
        SUM(likes_count)::INTEGER AS likes_count,
        SUM(comments_count)::INTEGER AS comments_count,
        SUM(dm_count)::INTEGER AS dm_count
    FROM (
        SELECT * FROM like_events
        UNION ALL
        SELECT * FROM comment_events
    ) source_events
    GROUP BY user_id_a, user_id_b
)
INSERT INTO public.interactions (
    user_id_a,
    user_id_b,
    likes_count,
    comments_count,
    dm_count,
    last_updated
)
SELECT
    a.user_id_a,
    a.user_id_b,
    a.likes_count,
    a.comments_count,
    a.dm_count,
    now()
FROM aggregated a
WHERE a.user_id_a < a.user_id_b;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.interactions i
        LEFT JOIN public.profiles pa ON pa.id = i.user_id_a
        LEFT JOIN public.profiles pb ON pb.id = i.user_id_b
        WHERE pa.id IS NULL
           OR pb.id IS NULL
           OR i.user_id_a >= i.user_id_b
    ) THEN
        RAISE EXCEPTION 'Interactions rebuild integrity check failed';
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 2) Repoint interactions FKs to profiles(id) for both canonical columns
-- -----------------------------------------------------------------------------

ALTER TABLE public.interactions
    DROP CONSTRAINT IF EXISTS fk_interactions_user_a,
    DROP CONSTRAINT IF EXISTS fk_interactions_user_b,
    DROP CONSTRAINT IF EXISTS fk_interactions_user_a_profiles,
    DROP CONSTRAINT IF EXISTS fk_interactions_user_b_profiles,
    DROP CONSTRAINT IF EXISTS interactions_user_id_a_fkey,
    DROP CONSTRAINT IF EXISTS interactions_user_id_b_fkey;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'interactions'
          AND constraint_name = 'fk_interactions_user_a_profiles'
    ) THEN
        ALTER TABLE public.interactions
            ADD CONSTRAINT fk_interactions_user_a_profiles
            FOREIGN KEY (user_id_a) REFERENCES public.profiles(id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'interactions'
          AND constraint_name = 'fk_interactions_user_b_profiles'
    ) THEN
        ALTER TABLE public.interactions
            ADD CONSTRAINT fk_interactions_user_b_profiles
            FOREIGN KEY (user_id_b) REFERENCES public.profiles(id);
    END IF;
END $$;

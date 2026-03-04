-- v2.0 Phase 24: deterministic demo table contract
-- Created: 2026-02-26
-- Safe to re-run (idempotent DDL + guarded constraints).

CREATE TABLE IF NOT EXISTS public.demo_profiles (
    id UUID PRIMARY KEY,
    nickname TEXT NOT NULL,
    interests TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    age INTEGER NOT NULL,
    languages TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    education TEXT NOT NULL,
    industry TEXT NOT NULL,
    timezone TEXT NOT NULL,
    occupation TEXT,
    friends UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.demo_interactions (
    user_id_a UUID NOT NULL,
    user_id_b UUID NOT NULL,
    likes_count INTEGER NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    dm_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id_a, user_id_b)
);

CREATE TABLE IF NOT EXISTS public.demo_map_coordinates (
    user_id UUID PRIMARY KEY,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    prev_x DOUBLE PRECISION,
    prev_y DOUBLE PRECISION,
    version_date DATE NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'demo_interactions_canonical_pair_check'
    ) THEN
        ALTER TABLE public.demo_interactions
        ADD CONSTRAINT demo_interactions_canonical_pair_check
        CHECK (user_id_a < user_id_b);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_demo_interactions_user_a_demo_profiles'
    ) THEN
        ALTER TABLE public.demo_interactions
        ADD CONSTRAINT fk_demo_interactions_user_a_demo_profiles
        FOREIGN KEY (user_id_a) REFERENCES public.demo_profiles(id) ON DELETE CASCADE;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_demo_interactions_user_b_demo_profiles'
    ) THEN
        ALTER TABLE public.demo_interactions
        ADD CONSTRAINT fk_demo_interactions_user_b_demo_profiles
        FOREIGN KEY (user_id_b) REFERENCES public.demo_profiles(id) ON DELETE CASCADE;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_demo_map_coordinates_user_demo_profiles'
    ) THEN
        ALTER TABLE public.demo_map_coordinates
        ADD CONSTRAINT fk_demo_map_coordinates_user_demo_profiles
        FOREIGN KEY (user_id) REFERENCES public.demo_profiles(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_demo_profiles_nickname
    ON public.demo_profiles (nickname);

CREATE INDEX IF NOT EXISTS idx_demo_profiles_friends_gin
    ON public.demo_profiles USING GIN (friends);

CREATE INDEX IF NOT EXISTS idx_demo_interactions_pair
    ON public.demo_interactions (user_id_a, user_id_b);

CREATE INDEX IF NOT EXISTS idx_demo_map_coordinates_version_date
    ON public.demo_map_coordinates (version_date);

CREATE OR REPLACE FUNCTION public.get_demo_profiles(
    p_user_ids UUID[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    nickname TEXT,
    interests TEXT[],
    city TEXT,
    state TEXT,
    age INTEGER,
    languages TEXT[],
    education TEXT,
    industry TEXT,
    timezone TEXT,
    occupation TEXT,
    friends UUID[]
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        p.id,
        p.nickname,
        p.interests,
        p.city,
        p.state,
        p.age,
        p.languages,
        p.education,
        p.industry,
        p.timezone,
        p.occupation,
        p.friends
    FROM public.demo_profiles p
    WHERE p_user_ids IS NULL OR p.id = ANY (p_user_ids)
    ORDER BY p.id;
$$;

CREATE OR REPLACE FUNCTION public.get_demo_interactions()
RETURNS TABLE (
    user_id_a UUID,
    user_id_b UUID,
    likes_count INTEGER,
    comments_count INTEGER,
    dm_count INTEGER
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        di.user_id_a,
        di.user_id_b,
        di.likes_count,
        di.comments_count,
        di.dm_count
    FROM public.demo_interactions di
    ORDER BY di.user_id_a, di.user_id_b;
$$;

CREATE OR REPLACE FUNCTION public.get_demo_map_coordinates(
    p_version_date DATE DEFAULT NULL
)
RETURNS TABLE (
    user_id UUID,
    x DOUBLE PRECISION,
    y DOUBLE PRECISION,
    prev_x DOUBLE PRECISION,
    prev_y DOUBLE PRECISION,
    version_date DATE,
    computed_at TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        dmc.user_id,
        dmc.x,
        dmc.y,
        dmc.prev_x,
        dmc.prev_y,
        dmc.version_date,
        dmc.computed_at
    FROM public.demo_map_coordinates dmc
    WHERE p_version_date IS NULL OR dmc.version_date = p_version_date
    ORDER BY dmc.user_id;
$$;

CREATE OR REPLACE FUNCTION public.clear_demo_map_data()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    TRUNCATE TABLE public.demo_map_coordinates;
    TRUNCATE TABLE public.demo_interactions;
    TRUNCATE TABLE public.demo_profiles;
END;
$$;

REVOKE ALL ON FUNCTION public.get_demo_profiles(UUID[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_demo_interactions() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_demo_map_coordinates(DATE) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.clear_demo_map_data() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.get_demo_profiles(UUID[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_demo_interactions() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_demo_map_coordinates(DATE) TO authenticated;

GRANT EXECUTE ON FUNCTION public.get_demo_profiles(UUID[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_demo_interactions() TO service_role;
GRANT EXECUTE ON FUNCTION public.get_demo_map_coordinates(DATE) TO service_role;
GRANT EXECUTE ON FUNCTION public.clear_demo_map_data() TO service_role;

-- SixDegrees: Database Foundation
-- Run once in Supabase Dashboard > SQL Editor
-- Safe to re-run (IF NOT EXISTS on all statements)
-- Tables: user_profiles, interactions, map_coordinates
-- Index: idx_map_coordinates_center_is_current

CREATE TABLE IF NOT EXISTS public.user_profiles (
    user_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name   TEXT NOT NULL,
    interests      TEXT[] NOT NULL DEFAULT '{}',
    location_city  TEXT NOT NULL DEFAULT '',
    location_state TEXT NOT NULL DEFAULT '',
    age            INTEGER NOT NULL,
    languages      TEXT[] NOT NULL DEFAULT '{}',
    field_of_study TEXT NOT NULL DEFAULT '',
    industry       TEXT NOT NULL DEFAULT '',
    education_level TEXT NOT NULL DEFAULT '',
    timezone       TEXT NOT NULL DEFAULT 'UTC',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.interactions (
    user_id_a      UUID NOT NULL,
    user_id_b      UUID NOT NULL,
    likes_count    INTEGER NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    dm_count       INTEGER NOT NULL DEFAULT 0,
    last_updated   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id_a, user_id_b),
    CONSTRAINT canonical_pair_order CHECK (user_id_a < user_id_b)
);

CREATE TABLE IF NOT EXISTS public.map_coordinates (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    center_user_id UUID NOT NULL,
    other_user_id  UUID NOT NULL,
    x              DOUBLE PRECISION NOT NULL,
    y              DOUBLE PRECISION NOT NULL,
    tier           SMALLINT NOT NULL CHECK (tier IN (1, 2, 3)),
    computed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_current     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_map_coordinates_center_is_current
    ON public.map_coordinates (center_user_id, is_current);

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.map_coordinates ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_interactions_user_a'
    ) THEN
        ALTER TABLE public.interactions
            ADD CONSTRAINT fk_interactions_user_a
            FOREIGN KEY (user_id_a) REFERENCES public.user_profiles(user_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_interactions_user_b'
    ) THEN
        ALTER TABLE public.interactions
            ADD CONSTRAINT fk_interactions_user_b
            FOREIGN KEY (user_id_b) REFERENCES public.user_profiles(user_id);
    END IF;
END $$;

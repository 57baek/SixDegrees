-- v2.0 Phase 20: Global map_coordinates contract
-- Created: 2026-02-26
-- Safe to re-run (idempotent migration + CREATE OR REPLACE RPCs).

-- -----------------------------------------------------------------------------
-- 1) Repurpose map_coordinates to one-row-per-user global coordinates
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.map_coordinates (
    user_id UUID PRIMARY KEY,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    prev_x DOUBLE PRECISION,
    prev_y DOUBLE PRECISION,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    version_date DATE NOT NULL,
    CONSTRAINT fk_map_coordinates_user
        FOREIGN KEY (user_id) REFERENCES public.profiles(id)
);

DO $$
DECLARE
    has_legacy_shape BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND column_name IN ('center_user_id', 'other_user_id', 'is_current')
    ) INTO has_legacy_shape;

    -- The legacy table stores per-view rows and cannot be deterministically
    -- transformed into one global row per user.
    IF has_legacy_shape THEN
        TRUNCATE TABLE public.map_coordinates;
    END IF;
END $$;

ALTER TABLE public.map_coordinates
    ADD COLUMN IF NOT EXISTS user_id UUID,
    ADD COLUMN IF NOT EXISTS prev_x DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS prev_y DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS version_date DATE;

ALTER TABLE public.map_coordinates
    ALTER COLUMN computed_at SET DEFAULT now();

UPDATE public.map_coordinates
SET version_date = COALESCE(version_date, (computed_at AT TIME ZONE 'UTC')::date)
WHERE version_date IS NULL;

ALTER TABLE public.map_coordinates
    ALTER COLUMN user_id SET NOT NULL,
    ALTER COLUMN version_date SET NOT NULL;

ALTER TABLE public.map_coordinates
    DROP CONSTRAINT IF EXISTS map_coordinates_pkey;

ALTER TABLE public.map_coordinates
    DROP COLUMN IF EXISTS center_user_id,
    DROP COLUMN IF EXISTS other_user_id,
    DROP COLUMN IF EXISTS tier,
    DROP COLUMN IF EXISTS is_current,
    DROP COLUMN IF EXISTS id;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND constraint_name = 'map_coordinates_pkey'
    ) THEN
        ALTER TABLE public.map_coordinates
            ADD CONSTRAINT map_coordinates_pkey PRIMARY KEY (user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND constraint_name = 'fk_map_coordinates_user'
    ) THEN
        ALTER TABLE public.map_coordinates
            ADD CONSTRAINT fk_map_coordinates_user
            FOREIGN KEY (user_id) REFERENCES public.profiles(id);
    END IF;
END $$;

DROP INDEX IF EXISTS public.idx_map_coordinates_center_is_current;
CREATE INDEX IF NOT EXISTS idx_map_coordinates_version_date
    ON public.map_coordinates (version_date);

ALTER TABLE public.map_coordinates ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 2) Secured RPCs for global coordinate write/read paths
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.upsert_global_map_coordinates(p_rows JSONB)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_row JSONB;
BEGIN
    IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' THEN
        RAISE EXCEPTION 'p_rows must be a JSON array';
    END IF;

    FOR v_row IN
        SELECT value FROM jsonb_array_elements(p_rows)
    LOOP
        INSERT INTO public.map_coordinates AS mc (
            user_id,
            x,
            y,
            prev_x,
            prev_y,
            computed_at,
            version_date
        )
        VALUES (
            (v_row->>'user_id')::UUID,
            (v_row->>'x')::DOUBLE PRECISION,
            (v_row->>'y')::DOUBLE PRECISION,
            NULL,
            NULL,
            COALESCE((v_row->>'computed_at')::TIMESTAMPTZ, now()),
            (v_row->>'version_date')::DATE
        )
        ON CONFLICT (user_id) DO UPDATE
            SET prev_x = mc.x,
                prev_y = mc.y,
                x = EXCLUDED.x,
                y = EXCLUDED.y,
                computed_at = EXCLUDED.computed_at,
                version_date = EXCLUDED.version_date;
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION public.get_global_map_coordinates(
    p_user_ids UUID[] DEFAULT NULL,
    p_version_date DATE DEFAULT NULL
)
RETURNS TABLE (
    user_id UUID,
    x DOUBLE PRECISION,
    y DOUBLE PRECISION,
    prev_x DOUBLE PRECISION,
    prev_y DOUBLE PRECISION,
    computed_at TIMESTAMPTZ,
    version_date DATE
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        mc.user_id,
        mc.x,
        mc.y,
        mc.prev_x,
        mc.prev_y,
        mc.computed_at,
        mc.version_date
    FROM public.map_coordinates mc
    WHERE (p_user_ids IS NULL OR mc.user_id = ANY (p_user_ids))
      AND (p_version_date IS NULL OR mc.version_date = p_version_date)
    ORDER BY mc.user_id;
$$;

REVOKE ALL ON FUNCTION public.upsert_global_map_coordinates(JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_global_map_coordinates(UUID[], DATE) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.upsert_global_map_coordinates(JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION public.upsert_global_map_coordinates(JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_global_map_coordinates(UUID[], DATE) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_global_map_coordinates(UUID[], DATE) TO service_role;

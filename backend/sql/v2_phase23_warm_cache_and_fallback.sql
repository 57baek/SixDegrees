-- v2.0 Phase 23: warm-cache and last-good fallback contract
-- Created: 2026-02-27
-- Safe to re-run (idempotent table + CREATE OR REPLACE RPCs).

-- -----------------------------------------------------------------------------
-- 1) Warmed map payload storage keyed by user + served metadata
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.map_warm_payloads (
    user_id UUID PRIMARY KEY REFERENCES public.profiles(id),
    payload JSONB NOT NULL,
    version_date DATE NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_map_warm_payloads_version_date
    ON public.map_warm_payloads (version_date);

ALTER TABLE public.map_warm_payloads ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 2) Last-known-good served metadata (single global row)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.map_last_good_version (
    scope TEXT PRIMARY KEY,
    version_date DATE NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT map_last_good_version_scope_check CHECK (scope = 'global')
);

ALTER TABLE public.map_last_good_version ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 3) Secured RPCs for warm-cache write/read + fallback metadata write/read
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.upsert_warm_map_payload(
    p_user_id UUID,
    p_payload JSONB,
    p_version_date DATE,
    p_computed_at TIMESTAMPTZ
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'p_user_id is required';
    END IF;

    IF p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' THEN
        RAISE EXCEPTION 'p_payload must be a JSON object';
    END IF;

    IF p_version_date IS NULL OR p_computed_at IS NULL THEN
        RAISE EXCEPTION 'p_version_date and p_computed_at are required';
    END IF;

    INSERT INTO public.map_warm_payloads AS mwp (
        user_id,
        payload,
        version_date,
        computed_at,
        updated_at
    )
    VALUES (
        p_user_id,
        p_payload,
        p_version_date,
        p_computed_at,
        now()
    )
    ON CONFLICT (user_id) DO UPDATE
        SET payload = EXCLUDED.payload,
            version_date = EXCLUDED.version_date,
            computed_at = EXCLUDED.computed_at,
            updated_at = now();
END;
$$;

CREATE OR REPLACE FUNCTION public.get_warm_map_payload(
    p_user_id UUID
)
RETURNS TABLE (
    user_id UUID,
    payload JSONB,
    version_date DATE,
    computed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        mwp.user_id,
        mwp.payload,
        mwp.version_date,
        mwp.computed_at,
        mwp.updated_at
    FROM public.map_warm_payloads mwp
    WHERE mwp.user_id = p_user_id;
$$;

CREATE OR REPLACE FUNCTION public.record_last_good_version(
    p_version_date DATE,
    p_computed_at TIMESTAMPTZ
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF p_version_date IS NULL OR p_computed_at IS NULL THEN
        RAISE EXCEPTION 'p_version_date and p_computed_at are required';
    END IF;

    INSERT INTO public.map_last_good_version AS mlgv (
        scope,
        version_date,
        computed_at,
        recorded_at
    )
    VALUES (
        'global',
        p_version_date,
        p_computed_at,
        now()
    )
    ON CONFLICT (scope) DO UPDATE
        SET version_date = EXCLUDED.version_date,
            computed_at = EXCLUDED.computed_at,
            recorded_at = now();
END;
$$;

CREATE OR REPLACE FUNCTION public.get_last_good_version()
RETURNS TABLE (
    version_date DATE,
    computed_at TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        mlgv.version_date,
        mlgv.computed_at,
        mlgv.recorded_at
    FROM public.map_last_good_version mlgv
    WHERE mlgv.scope = 'global'
    LIMIT 1;
$$;

REVOKE ALL ON TABLE public.map_warm_payloads FROM PUBLIC;
REVOKE ALL ON TABLE public.map_last_good_version FROM PUBLIC;
REVOKE ALL ON FUNCTION public.upsert_warm_map_payload(UUID, JSONB, DATE, TIMESTAMPTZ) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_warm_map_payload(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.record_last_good_version(DATE, TIMESTAMPTZ) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_last_good_version() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.upsert_warm_map_payload(UUID, JSONB, DATE, TIMESTAMPTZ) TO service_role;
GRANT EXECUTE ON FUNCTION public.record_last_good_version(DATE, TIMESTAMPTZ) TO service_role;

GRANT EXECUTE ON FUNCTION public.get_warm_map_payload(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_warm_map_payload(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_last_good_version() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_last_good_version() TO service_role;

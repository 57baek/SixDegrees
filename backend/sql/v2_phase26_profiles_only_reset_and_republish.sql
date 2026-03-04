-- v2.0 Phase 26: profiles-only path-B reset, preflight, and safe legacy drop
-- Created: 2026-02-27
-- Safe to re-run (idempotent preflight + guarded destructive DDL).

CREATE OR REPLACE FUNCTION public.phase26_profiles_only_preflight()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    missing_publish_prerequisites TEXT[] := ARRAY[]::TEXT[];
    fk_dependency_count INTEGER := 0;
    view_dependency_count INTEGER := 0;
    function_dependency_count INTEGER := 0;
BEGIN
    IF to_regclass('public.map_coordinates') IS NULL THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing table public.map_coordinates'
        );
    END IF;

    IF to_regclass('public.profiles') IS NULL THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing table public.profiles'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND column_name = 'user_id'
    ) THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing column public.map_coordinates.user_id'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND column_name = 'x'
    ) THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing column public.map_coordinates.x'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND column_name = 'y'
    ) THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing column public.map_coordinates.y'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND column_name = 'prev_x'
    ) THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing column public.map_coordinates.prev_x'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND column_name = 'prev_y'
    ) THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing column public.map_coordinates.prev_y'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND column_name = 'version_date'
    ) THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing column public.map_coordinates.version_date'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'map_coordinates'
          AND column_name = 'computed_at'
    ) THEN
        missing_publish_prerequisites := array_append(
            missing_publish_prerequisites,
            'missing column public.map_coordinates.computed_at'
        );
    END IF;

    IF COALESCE(array_length(missing_publish_prerequisites, 1), 0) > 0 THEN
        RAISE EXCEPTION 'Phase 26 preflight blocked: publish prerequisites missing: %',
            array_to_string(missing_publish_prerequisites, '; ');
    END IF;

    IF to_regclass('public.user_profiles') IS NULL THEN
        RAISE NOTICE 'public.user_profiles does not exist; skipping dependency gate';
        RETURN;
    END IF;

    SELECT COUNT(*)
    INTO fk_dependency_count
    FROM pg_constraint
    WHERE contype = 'f'
      AND confrelid = 'public.user_profiles'::regclass;

    IF fk_dependency_count > 0 THEN
        RAISE EXCEPTION 'Phase 26 preflight blocked: % foreign-key dependencies still reference public.user_profiles', fk_dependency_count;
    END IF;

    SELECT COUNT(*)
    INTO view_dependency_count
    FROM pg_depend dep
    JOIN pg_rewrite rw ON rw.oid = dep.objid
    JOIN pg_class cls ON cls.oid = rw.ev_class
    JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
    WHERE dep.classid = 'pg_rewrite'::regclass
      AND dep.refobjid = 'public.user_profiles'::regclass
      AND nsp.nspname = 'public'
      AND cls.relkind IN ('v', 'm');

    IF view_dependency_count > 0 THEN
        RAISE EXCEPTION 'Phase 26 preflight blocked: % view dependencies still reference public.user_profiles', view_dependency_count;
    END IF;

    SELECT COUNT(*)
    INTO function_dependency_count
    FROM pg_depend dep
    JOIN pg_proc proc ON proc.oid = dep.objid
    JOIN pg_namespace nsp ON nsp.oid = proc.pronamespace
    WHERE dep.classid = 'pg_proc'::regclass
      AND dep.refobjid = 'public.user_profiles'::regclass
      AND nsp.nspname = 'public';

    IF function_dependency_count > 0 THEN
        RAISE EXCEPTION 'Phase 26 preflight blocked: % function dependencies still reference public.user_profiles', function_dependency_count;
    END IF;
END;
$$;

DO $$
BEGIN
    -- Ordering is intentional:
    --   1) fail-closed preflight, 2) reset map rows for path-B republish,
    --   3) destructive legacy drop only after gates pass.
    PERFORM public.phase26_profiles_only_preflight();

    TRUNCATE TABLE public.map_coordinates;

    RAISE NOTICE 'Phase 26 path-B reset complete: run global republish to create fresh version_date/computed_at rows';

    IF to_regclass('public.user_profiles') IS NULL THEN
        RAISE NOTICE 'public.user_profiles already absent; skipping drop';
        RETURN;
    END IF;

    DROP TABLE public.user_profiles;
END
$$;

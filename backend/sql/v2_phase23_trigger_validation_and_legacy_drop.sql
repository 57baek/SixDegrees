-- v2.0 Phase 23: trigger validation and safe legacy drop gate
-- Created: 2026-02-27
-- Safe to re-run (idempotent and fail-closed).

DO $$
DECLARE
    missing_requirements TEXT[] := ARRAY[]::TEXT[];
    fk_dependency_count INTEGER := 0;
    view_dependency_count INTEGER := 0;
    function_dependency_count INTEGER := 0;
BEGIN
    IF to_regclass('public.user_profiles') IS NULL THEN
        RAISE NOTICE 'public.user_profiles does not exist; skipping legacy drop gate';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'likes'
          AND t.tgname = 'trg_likes_insert'
          AND NOT t.tgisinternal
    ) THEN
        missing_requirements := array_append(missing_requirements, 'missing trigger public.likes.trg_likes_insert');
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'likes'
          AND t.tgname = 'trg_likes_delete'
          AND NOT t.tgisinternal
    ) THEN
        missing_requirements := array_append(missing_requirements, 'missing trigger public.likes.trg_likes_delete');
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'comments'
          AND t.tgname = 'trg_comments_insert'
          AND NOT t.tgisinternal
    ) THEN
        missing_requirements := array_append(missing_requirements, 'missing trigger public.comments.trg_comments_insert');
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'comments'
          AND t.tgname = 'trg_comments_delete'
          AND NOT t.tgisinternal
    ) THEN
        missing_requirements := array_append(missing_requirements, 'missing trigger public.comments.trg_comments_delete');
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'interactions'
          AND column_name = 'likes_count'
    ) THEN
        missing_requirements := array_append(missing_requirements, 'missing column public.interactions.likes_count');
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'interactions'
          AND column_name = 'comments_count'
    ) THEN
        missing_requirements := array_append(missing_requirements, 'missing column public.interactions.comments_count');
    END IF;

    IF COALESCE(array_length(missing_requirements, 1), 0) > 0 THEN
        RAISE EXCEPTION 'Legacy drop blocked: trigger/counter prerequisites missing: %', array_to_string(missing_requirements, '; ');
    END IF;

    SELECT COUNT(*)
    INTO fk_dependency_count
    FROM pg_constraint
    WHERE contype = 'f'
      AND confrelid = 'public.user_profiles'::regclass;

    IF fk_dependency_count > 0 THEN
        RAISE EXCEPTION 'Legacy drop blocked: % foreign-key dependencies still reference public.user_profiles', fk_dependency_count;
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
        RAISE EXCEPTION 'Legacy drop blocked: % view dependencies still reference public.user_profiles', view_dependency_count;
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
        RAISE EXCEPTION 'Legacy drop blocked: % function dependencies still reference public.user_profiles', function_dependency_count;
    END IF;

    DROP TABLE public.user_profiles;
END $$;

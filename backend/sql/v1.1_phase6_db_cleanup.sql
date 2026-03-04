-- v1.1 Phase 6: DB Schema Cleanup Migration
-- Created: 2026-02-23
-- Covers: DBCL-03 (add is_onboarded),
--         DBCL-04 (likes INSERT trigger), DBCL-05 (likes DELETE trigger),
--         DBCL-06 (comments INSERT trigger), DBCL-07 (comments DELETE trigger)
-- Safe to re-run (idempotent throughout).


-- ============================================================
-- Section 1: Add is_onboarded to profiles (DBCL-03)
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'profiles'
          AND column_name = 'is_onboarded'
    ) THEN
        ALTER TABLE public.profiles
            ADD COLUMN is_onboarded BOOLEAN NOT NULL DEFAULT false;
    END IF;
END $$;


-- ============================================================
-- Section 2: likes INSERT trigger (DBCL-04)
-- Increments interactions.likes_count when a like is created.
-- Canonical pair: LEAST/GREATEST on (liker, post_author).
-- Guards against self-likes (v_uid_a = v_uid_b).
-- ============================================================

CREATE OR REPLACE FUNCTION public.trg_likes_insert_fn()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_post_author_id UUID;
    v_uid_a UUID;
    v_uid_b UUID;
BEGIN
    SELECT user_id INTO v_post_author_id FROM public.posts WHERE id = NEW.post_id;
    IF v_post_author_id IS NULL THEN RETURN NEW; END IF;
    v_uid_a := LEAST(NEW.user_id, v_post_author_id);
    v_uid_b := GREATEST(NEW.user_id, v_post_author_id);
    IF v_uid_a = v_uid_b THEN RETURN NEW; END IF;
    PERFORM increment_interaction(v_uid_a, v_uid_b, 'likes_count');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_likes_insert ON public.likes;
CREATE TRIGGER trg_likes_insert
    AFTER INSERT ON public.likes
    FOR EACH ROW EXECUTE FUNCTION public.trg_likes_insert_fn();


-- ============================================================
-- Section 3: likes DELETE trigger (DBCL-05)
-- Decrements interactions.likes_count when a like is removed.
-- Uses GREATEST(0, count - 1) floor to prevent negative counts.
-- increment_interaction RPC only increments; inline UPDATE used here.
-- ============================================================

CREATE OR REPLACE FUNCTION public.trg_likes_delete_fn()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_post_author_id UUID;
    v_uid_a UUID;
    v_uid_b UUID;
BEGIN
    SELECT user_id INTO v_post_author_id FROM public.posts WHERE id = OLD.post_id;
    IF v_post_author_id IS NULL THEN RETURN OLD; END IF;
    v_uid_a := LEAST(OLD.user_id, v_post_author_id);
    v_uid_b := GREATEST(OLD.user_id, v_post_author_id);
    IF v_uid_a = v_uid_b THEN RETURN OLD; END IF;
    UPDATE public.interactions
    SET likes_count = GREATEST(0, likes_count - 1),
        last_updated = now()
    WHERE user_id_a = v_uid_a AND user_id_b = v_uid_b;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_likes_delete ON public.likes;
CREATE TRIGGER trg_likes_delete
    AFTER DELETE ON public.likes
    FOR EACH ROW EXECUTE FUNCTION public.trg_likes_delete_fn();


-- ============================================================
-- Section 4: comments INSERT trigger (DBCL-06)
-- Increments interactions.comments_count when a comment is created.
-- Canonical pair: LEAST/GREATEST on (commenter, post_author).
-- Guards against self-comments (v_uid_a = v_uid_b).
-- ============================================================

CREATE OR REPLACE FUNCTION public.trg_comments_insert_fn()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_post_author_id UUID;
    v_uid_a UUID;
    v_uid_b UUID;
BEGIN
    SELECT user_id INTO v_post_author_id FROM public.posts WHERE id = NEW.post_id;
    IF v_post_author_id IS NULL THEN RETURN NEW; END IF;
    v_uid_a := LEAST(NEW.user_id, v_post_author_id);
    v_uid_b := GREATEST(NEW.user_id, v_post_author_id);
    IF v_uid_a = v_uid_b THEN RETURN NEW; END IF;
    PERFORM increment_interaction(v_uid_a, v_uid_b, 'comments_count');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_comments_insert ON public.comments;
CREATE TRIGGER trg_comments_insert
    AFTER INSERT ON public.comments
    FOR EACH ROW EXECUTE FUNCTION public.trg_comments_insert_fn();


-- ============================================================
-- Section 5: comments DELETE trigger (DBCL-07)
-- Decrements interactions.comments_count when a comment is removed.
-- Uses GREATEST(0, count - 1) floor to prevent negative counts.
-- ============================================================

CREATE OR REPLACE FUNCTION public.trg_comments_delete_fn()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_post_author_id UUID;
    v_uid_a UUID;
    v_uid_b UUID;
BEGIN
    SELECT user_id INTO v_post_author_id FROM public.posts WHERE id = OLD.post_id;
    IF v_post_author_id IS NULL THEN RETURN OLD; END IF;
    v_uid_a := LEAST(OLD.user_id, v_post_author_id);
    v_uid_b := GREATEST(OLD.user_id, v_post_author_id);
    IF v_uid_a = v_uid_b THEN RETURN OLD; END IF;
    UPDATE public.interactions
    SET comments_count = GREATEST(0, comments_count - 1),
        last_updated = now()
    WHERE user_id_a = v_uid_a AND user_id_b = v_uid_b;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_comments_delete ON public.comments;
CREATE TRIGGER trg_comments_delete
    AFTER DELETE ON public.comments
    FOR EACH ROW EXECUTE FUNCTION public.trg_comments_delete_fn();

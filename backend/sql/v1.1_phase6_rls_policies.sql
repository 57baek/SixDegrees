-- v1.1 Phase 6: RLS Policy Definitions
-- Created: 2026-02-23
-- Tables: profiles, posts, likes, comments, interactions, map_coordinates
-- Architecture: Frontend hits Supabase directly (RLS-protected) for content reads/writes.
--               FastAPI uses service role key (bypasses RLS) for profile writes and algorithm ops.
-- Safe to re-run: DROP POLICY IF EXISTS before each CREATE POLICY.


-- ============================================================
-- Table 1: profiles
-- All rows readable by anyone (anon + authenticated).
-- Only own row insertable/updatable. No delete policy.
-- ============================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select_all" ON public.profiles;
CREATE POLICY "profiles_select_all"
    ON public.profiles FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
CREATE POLICY "profiles_insert_own"
    ON public.profiles FOR INSERT
    WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own"
    ON public.profiles FOR UPDATE
    USING (id = auth.uid());


-- ============================================================
-- Table 2: posts
-- All rows readable. Own rows insertable, updatable, deletable.
-- user_id must equal auth.uid() for write operations.
-- ============================================================

ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "posts_select_all" ON public.posts;
CREATE POLICY "posts_select_all"
    ON public.posts FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "posts_insert_own" ON public.posts;
CREATE POLICY "posts_insert_own"
    ON public.posts FOR INSERT
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "posts_update_own" ON public.posts;
CREATE POLICY "posts_update_own"
    ON public.posts FOR UPDATE
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "posts_delete_own" ON public.posts;
CREATE POLICY "posts_delete_own"
    ON public.posts FOR DELETE
    USING (user_id = auth.uid());


-- ============================================================
-- Table 3: likes
-- All rows readable. Own rows insertable and deletable.
-- No update policy (likes are insert/delete only — no edits).
-- ============================================================

ALTER TABLE public.likes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "likes_select_all" ON public.likes;
CREATE POLICY "likes_select_all"
    ON public.likes FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "likes_insert_own" ON public.likes;
CREATE POLICY "likes_insert_own"
    ON public.likes FOR INSERT
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "likes_delete_own" ON public.likes;
CREATE POLICY "likes_delete_own"
    ON public.likes FOR DELETE
    USING (user_id = auth.uid());


-- ============================================================
-- Table 4: comments
-- All rows readable. Own rows insertable, updatable, deletable.
-- ============================================================

ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "comments_select_all" ON public.comments;
CREATE POLICY "comments_select_all"
    ON public.comments FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "comments_insert_own" ON public.comments;
CREATE POLICY "comments_insert_own"
    ON public.comments FOR INSERT
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "comments_update_own" ON public.comments;
CREATE POLICY "comments_update_own"
    ON public.comments FOR UPDATE
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "comments_delete_own" ON public.comments;
CREATE POLICY "comments_delete_own"
    ON public.comments FOR DELETE
    USING (user_id = auth.uid());


-- ============================================================
-- Table 5: interactions
-- Read-only for authenticated users (SELECT only).
-- No INSERT/UPDATE/DELETE policies — user-JWT writes blocked by default when RLS is enabled.
-- FastAPI service role bypasses RLS for writes.
-- Postgres triggers (likes/comments) write via SECURITY DEFINER functions (see patch below).
-- ============================================================

ALTER TABLE public.interactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "interactions_select_all" ON public.interactions;
CREATE POLICY "interactions_select_all"
    ON public.interactions FOR SELECT
    USING (true);

-- NOTE: No INSERT/UPDATE/DELETE policies for interactions.
-- The absence of write policies blocks user-JWT mutations by default.


-- ============================================================
-- Table 6: map_coordinates
-- Read-only for authenticated users (SELECT only).
-- No user-JWT writes: backend pipeline writes via service role.
-- ============================================================

ALTER TABLE public.map_coordinates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "map_coordinates_select_all" ON public.map_coordinates;
CREATE POLICY "map_coordinates_select_all"
    ON public.map_coordinates FOR SELECT
    USING (true);

-- NOTE: No INSERT/UPDATE/DELETE policies for map_coordinates.
-- Algorithm pipeline runs as service role and bypasses RLS.


-- ============================================================
-- SECURITY DEFINER patch for trigger functions
-- Trigger functions must run as the function owner (not the calling user)
-- so they can write to interactions even when user-JWT cannot.
-- This replaces the definitions from v1.1_phase6_db_cleanup.sql.
-- ============================================================

CREATE OR REPLACE FUNCTION public.trg_likes_insert_fn()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
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

CREATE OR REPLACE FUNCTION public.trg_likes_delete_fn()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
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

CREATE OR REPLACE FUNCTION public.trg_comments_insert_fn()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
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

CREATE OR REPLACE FUNCTION public.trg_comments_delete_fn()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
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

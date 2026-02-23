-- Migration: add_increment_interaction_rpc
-- Applied: 2026-02-23
-- Applied via: asyncpg direct PostgreSQL connection
--
-- Creates an atomic upsert+increment function for the interactions table.
-- Why RPC not upsert: Standard .upsert() replaces the full row, resetting all counts.
-- This function uses INSERT ... ON CONFLICT DO NOTHING then UPDATE col = col + 1,
-- which is atomic and race-condition-free.

CREATE OR REPLACE FUNCTION increment_interaction(
    p_user_id_a UUID,
    p_user_id_b UUID,
    p_column    TEXT   -- 'likes_count', 'comments_count', or 'dm_count'
) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    IF p_column NOT IN ('likes_count', 'comments_count', 'dm_count') THEN
        RAISE EXCEPTION 'Invalid column: %', p_column;
    END IF;

    INSERT INTO interactions (user_id_a, user_id_b, likes_count, comments_count, dm_count)
    VALUES (p_user_id_a, p_user_id_b, 0, 0, 0)
    ON CONFLICT (user_id_a, user_id_b)
    DO NOTHING;

    EXECUTE format(
        'UPDATE interactions SET %I = %I + 1, last_updated = now() WHERE user_id_a = $1 AND user_id_b = $2',
        p_column, p_column
    ) USING p_user_id_a, p_user_id_b;
END;
$$;

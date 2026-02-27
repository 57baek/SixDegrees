-- v2.0 Phase 22: ego-map profile projection contract
-- Created: 2026-02-26
-- Safe to re-run (idempotent CREATE OR REPLACE RPC).

CREATE OR REPLACE FUNCTION public.get_ego_map_profiles(
    p_user_ids UUID[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    nickname TEXT,
    friends UUID[]
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        p.id,
        COALESCE(p.nickname, '') AS nickname,
        COALESCE(p.friends, ARRAY[]::UUID[]) AS friends
    FROM public.profiles p
    WHERE p_user_ids IS NULL OR p.id = ANY (p_user_ids)
    ORDER BY p.id;
$$;

REVOKE ALL ON FUNCTION public.get_ego_map_profiles(UUID[]) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.get_ego_map_profiles(UUID[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_ego_map_profiles(UUID[]) TO service_role;

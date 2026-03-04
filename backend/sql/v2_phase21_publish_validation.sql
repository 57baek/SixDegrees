-- v2.0 Phase 21: publish validation diagnostics contract
-- Created: 2026-02-26
-- Safe to re-run (idempotent table and CREATE OR REPLACE RPCs).

-- -----------------------------------------------------------------------------
-- 1) Run-level diagnostics storage for compute + publish validation outcomes
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.compute_run_diagnostics (
    run_id UUID PRIMARY KEY,
    requesting_user_id UUID NOT NULL REFERENCES public.profiles(id),
    version_date DATE NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    profile_count INTEGER NOT NULL,
    interaction_edge_count INTEGER NOT NULL,
    candidate_row_count INTEGER NOT NULL,
    published BOOLEAN NOT NULL,
    publish_block_reason TEXT,
    gate_input_passed BOOLEAN NOT NULL,
    gate_embedding_passed BOOLEAN NOT NULL,
    gate_persistence_passed BOOLEAN NOT NULL,
    quality_metrics JSONB NOT NULL DEFAULT '{}'::JSONB,
    stage_timings_ms JSONB NOT NULL DEFAULT '{}'::JSONB,
    gate_details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_compute_run_diagnostics_created_at
    ON public.compute_run_diagnostics (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_compute_run_diagnostics_version_date
    ON public.compute_run_diagnostics (version_date);

ALTER TABLE public.compute_run_diagnostics ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 2) Secured RPCs for diagnostics write/read paths
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.record_compute_run_diagnostics(p_payload JSONB)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' THEN
        RAISE EXCEPTION 'p_payload must be a JSON object';
    END IF;

    INSERT INTO public.compute_run_diagnostics (
        run_id,
        requesting_user_id,
        version_date,
        computed_at,
        profile_count,
        interaction_edge_count,
        candidate_row_count,
        published,
        publish_block_reason,
        gate_input_passed,
        gate_embedding_passed,
        gate_persistence_passed,
        quality_metrics,
        stage_timings_ms,
        gate_details
    )
    VALUES (
        (p_payload->>'run_id')::UUID,
        (p_payload->>'requesting_user_id')::UUID,
        (p_payload->>'version_date')::DATE,
        (p_payload->>'computed_at')::TIMESTAMPTZ,
        COALESCE((p_payload->>'profile_count')::INTEGER, 0),
        COALESCE((p_payload->>'interaction_edge_count')::INTEGER, 0),
        COALESCE((p_payload->>'candidate_row_count')::INTEGER, 0),
        COALESCE((p_payload->>'published')::BOOLEAN, FALSE),
        NULLIF(p_payload->>'publish_block_reason', ''),
        COALESCE((p_payload->>'gate_input_passed')::BOOLEAN, FALSE),
        COALESCE((p_payload->>'gate_embedding_passed')::BOOLEAN, FALSE),
        COALESCE((p_payload->>'gate_persistence_passed')::BOOLEAN, FALSE),
        COALESCE(p_payload->'quality_metrics', '{}'::JSONB),
        COALESCE(p_payload->'stage_timings_ms', '{}'::JSONB),
        COALESCE(p_payload->'gate_details', '{}'::JSONB)
    )
    ON CONFLICT (run_id) DO UPDATE
        SET requesting_user_id = EXCLUDED.requesting_user_id,
            version_date = EXCLUDED.version_date,
            computed_at = EXCLUDED.computed_at,
            profile_count = EXCLUDED.profile_count,
            interaction_edge_count = EXCLUDED.interaction_edge_count,
            candidate_row_count = EXCLUDED.candidate_row_count,
            published = EXCLUDED.published,
            publish_block_reason = EXCLUDED.publish_block_reason,
            gate_input_passed = EXCLUDED.gate_input_passed,
            gate_embedding_passed = EXCLUDED.gate_embedding_passed,
            gate_persistence_passed = EXCLUDED.gate_persistence_passed,
            quality_metrics = EXCLUDED.quality_metrics,
            stage_timings_ms = EXCLUDED.stage_timings_ms,
            gate_details = EXCLUDED.gate_details;
END;
$$;

CREATE OR REPLACE FUNCTION public.get_compute_run_diagnostics(
    p_run_id UUID DEFAULT NULL,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    run_id UUID,
    requesting_user_id UUID,
    version_date DATE,
    computed_at TIMESTAMPTZ,
    profile_count INTEGER,
    interaction_edge_count INTEGER,
    candidate_row_count INTEGER,
    published BOOLEAN,
    publish_block_reason TEXT,
    gate_input_passed BOOLEAN,
    gate_embedding_passed BOOLEAN,
    gate_persistence_passed BOOLEAN,
    quality_metrics JSONB,
    stage_timings_ms JSONB,
    gate_details JSONB,
    created_at TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        d.run_id,
        d.requesting_user_id,
        d.version_date,
        d.computed_at,
        d.profile_count,
        d.interaction_edge_count,
        d.candidate_row_count,
        d.published,
        d.publish_block_reason,
        d.gate_input_passed,
        d.gate_embedding_passed,
        d.gate_persistence_passed,
        d.quality_metrics,
        d.stage_timings_ms,
        d.gate_details,
        d.created_at
    FROM public.compute_run_diagnostics d
    WHERE p_run_id IS NULL OR d.run_id = p_run_id
    ORDER BY d.created_at DESC
    LIMIT GREATEST(COALESCE(p_limit, 50), 1);
$$;

REVOKE ALL ON TABLE public.compute_run_diagnostics FROM PUBLIC;
REVOKE ALL ON FUNCTION public.record_compute_run_diagnostics(JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_compute_run_diagnostics(UUID, INTEGER) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.record_compute_run_diagnostics(JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_compute_run_diagnostics(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_compute_run_diagnostics(UUID, INTEGER) TO service_role;

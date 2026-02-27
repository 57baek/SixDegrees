"""DB-connected pipeline orchestrator.

Chains fetch_all() -> run_pipeline() -> write_coordinates() for a full global
coordinate batch. Called by scheduler and trigger endpoint. Raises ValueError
if N < 10 or requesting_user_id not in profiles.
"""

from datetime import datetime, timezone
from time import perf_counter
from typing import cast
from uuid import uuid4

from services.map_pipeline.contracts import RawInteractionCounts


def run_pipeline_for_user(requesting_user_id: str) -> None:
    """Run the full map pipeline for a single user and persist the results.

    Fetches all profiles and interactions from Supabase, runs the full
    algorithm pipeline (interaction scoring -> combined distance -> t-SNE ->
    origin translation), and writes the resulting coordinates to map_coordinates.

    Args:
        requesting_user_id: The user who should be at (0.0, 0.0) in the output.
                            Must exist in profiles table.

    Returns:
        None. Side effect: map_coordinates table updated for requesting_user_id.

    Raises:
        ValueError: If N < 10 (propagated from tsne_projector — too few users).
        ValueError: If requesting_user_id is not in the profiles table.
    """
    from services.map_pipeline.coord_writer import write_coordinates
    from services.map_pipeline.data_fetcher import (
        fetch_all,
        fetch_global_coordinate_rows,
        fetch_prior_coordinates,
    )
    from services.map_pipeline.diagnostics import record_compute_run
    from services.map_pipeline.pipeline import run_pipeline
    from services.map_pipeline.publish_validation import validate_candidate_publish

    run_id = str(uuid4())
    computed_at = datetime.now(timezone.utc).isoformat()
    version_date = datetime.now(timezone.utc).date().isoformat()

    stage_timings_ms: dict[str, float] = {}
    users = []
    raw_interaction_counts: RawInteractionCounts = {}
    result = {"translated_results": [], "user_ids": [], "raw_coords": None}

    try:
        fetch_start = perf_counter()
        users, raw_interaction_counts = fetch_all()
        prior_coordinates = fetch_prior_coordinates()
        stage_timings_ms["fetch"] = round((perf_counter() - fetch_start) * 1000.0, 3)

        compute_start = perf_counter()
        result = run_pipeline(
            users,
            cast(RawInteractionCounts, raw_interaction_counts),
            requesting_user_id,
            prior_coordinates=prior_coordinates,
        )
        stage_timings_ms["compute"] = round((perf_counter() - compute_start) * 1000.0, 3)

        pre_validation_start = perf_counter()
        pre_validation = validate_candidate_publish(
            translated_results=result["translated_results"],
            user_ids=result["user_ids"],
            raw_coords=result["raw_coords"],
            prior_coordinates=prior_coordinates,
            expected_version_date=version_date,
            expected_computed_at=computed_at,
            check_persistence=False,
        )
        stage_timings_ms["validate_pre_publish"] = round(
            (perf_counter() - pre_validation_start) * 1000.0,
            3,
        )

        if not pre_validation.publish_allowed:
            record_compute_run(
                run_id=run_id,
                requesting_user_id=requesting_user_id,
                version_date=version_date,
                computed_at=computed_at,
                profile_count=len(users),
                interaction_edge_count=len(raw_interaction_counts),
                candidate_row_count=len(result["translated_results"]),
                published=False,
                publish_block_reason=pre_validation.publish_block_reason,
                gate_input_passed=pre_validation.gate_input_passed,
                gate_embedding_passed=pre_validation.gate_embedding_passed,
                gate_persistence_passed=False,
                quality_metrics=pre_validation.quality_metrics,
                stage_timings_ms=stage_timings_ms,
                gate_details=pre_validation.gate_details,
            )
            return

        publish_start = perf_counter()
        write_coordinates(
            result["translated_results"],
            version_date=version_date,
            computed_at=computed_at,
        )
        stage_timings_ms["publish"] = round((perf_counter() - publish_start) * 1000.0, 3)

        persistence_check_start = perf_counter()
        persisted_rows = fetch_global_coordinate_rows()
        post_validation = validate_candidate_publish(
            translated_results=result["translated_results"],
            user_ids=result["user_ids"],
            raw_coords=result["raw_coords"],
            prior_coordinates=prior_coordinates,
            persisted_rows=persisted_rows,
            expected_version_date=version_date,
            expected_computed_at=computed_at,
            check_persistence=True,
        )
        stage_timings_ms["validate_persistence"] = round(
            (perf_counter() - persistence_check_start) * 1000.0,
            3,
        )

        record_compute_run(
            run_id=run_id,
            requesting_user_id=requesting_user_id,
            version_date=version_date,
            computed_at=computed_at,
            profile_count=len(users),
            interaction_edge_count=len(raw_interaction_counts),
            candidate_row_count=len(result["translated_results"]),
            published=post_validation.publish_allowed,
            publish_block_reason=post_validation.publish_block_reason,
            gate_input_passed=post_validation.gate_input_passed,
            gate_embedding_passed=post_validation.gate_embedding_passed,
            gate_persistence_passed=post_validation.gate_persistence_passed,
            quality_metrics=post_validation.quality_metrics,
            stage_timings_ms=stage_timings_ms,
            gate_details=post_validation.gate_details,
        )

        if not post_validation.publish_allowed:
            raise RuntimeError("Published coordinates failed persistence validation")

    except Exception:
        if "failed" not in stage_timings_ms:
            stage_timings_ms["failed"] = 1.0
        record_compute_run(
            run_id=run_id,
            requesting_user_id=requesting_user_id,
            version_date=version_date,
            computed_at=computed_at,
            profile_count=len(users),
            interaction_edge_count=len(raw_interaction_counts),
            candidate_row_count=len(result.get("translated_results", [])),
            published=False,
            publish_block_reason="pipeline_exception",
            gate_input_passed=False,
            gate_embedding_passed=False,
            gate_persistence_passed=False,
            quality_metrics={},
            stage_timings_ms=stage_timings_ms,
            gate_details={},
        )
        raise

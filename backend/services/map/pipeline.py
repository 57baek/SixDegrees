"""Pipeline entry point — run global coordinate recompute."""
import time
from services.map.fetcher import fetch
from services.map.distance import build_combined_distance
from services.map.projector import project
from services.map.validation import validate_output
from services.map.writer import write
from services.map.diagnostics import record_run
from services.map.contracts import PipelineInput, PipelineResult


def run() -> PipelineResult:
    start = time.time()
    data: PipelineInput | None = None
    try:
        data = fetch()
        matrix = build_combined_distance(data)
        coords = project(matrix)
        validate_output(coords, data.user_ids)
        write(data.user_ids, coords)
        duration_ms = int((time.time() - start) * 1000)
        edge_count = sum(
            1 for r in data.interactions
            if (r.get("likes_count") or 0) + (r.get("comments_count") or 0) + (r.get("dm_count") or 0) > 0
        )
        result = PipelineResult(
            user_ids=data.user_ids,
            coords=coords,
            edge_count=edge_count,
            duration_ms=duration_ms,
        )
        record_run(
            status="success",
            user_count=len(data.user_ids),
            edge_count=edge_count,
            duration_ms=duration_ms,
            error=None,
        )
        return result
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        record_run(
            status="failed",
            user_count=len(data.user_ids) if data else 0,
            edge_count=0,
            duration_ms=duration_ms,
            error=str(e),
        )
        raise


def run_pipeline_for_user(user_id: str) -> None:
    """Compatibility shim — calls the global pipeline."""
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id must be a non-empty string")
    run()

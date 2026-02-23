"""DB-connected pipeline orchestrator.

Chains fetch_all() -> run_pipeline() -> write_coordinates() for a single user.
Called by Phase 4 scheduler and trigger endpoint.
Raises ValueError if N < 10 or requesting_user_id not in user_profiles.
"""

from services.map_pipeline.data_fetcher import fetch_all
from services.map_pipeline.pipeline import run_pipeline
from services.map_pipeline.coord_writer import write_coordinates


def run_pipeline_for_user(requesting_user_id: str) -> None:
    """Run the full map pipeline for a single user and persist the results.

    Fetches all user profiles and interactions from Supabase, runs the full
    algorithm pipeline (interaction scoring -> combined distance -> t-SNE ->
    origin translation), and writes the resulting coordinates to map_coordinates.

    Args:
        requesting_user_id: The user who should be at (0.0, 0.0) in the output.
                            Must exist in user_profiles table.

    Returns:
        None. Side effect: map_coordinates table updated for requesting_user_id.

    Raises:
        ValueError: If N < 10 (propagated from tsne_projector — too few users).
        ValueError: If requesting_user_id is not in the user_profiles table.
    """
    # Step 1: Fetch all users and interactions from Supabase
    users, raw_interaction_counts = fetch_all()

    # Step 2: Run the pure-computation pipeline
    result = run_pipeline(users, raw_interaction_counts, requesting_user_id)

    # Step 3: Persist coordinates to map_coordinates table
    write_coordinates(requesting_user_id, result["translated_results"])

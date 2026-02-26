from unittest.mock import MagicMock, patch

from services.map_pipeline.diagnostics import record_compute_run


def test_record_compute_run_persists_expected_payload_shape():
    mock_sb = MagicMock()

    with patch("services.map_pipeline.diagnostics.get_supabase_client", return_value=mock_sb):
        record_compute_run(
            run_id="b7beeb09-1111-4444-8888-0a6db86fd243",
            requesting_user_id="9de8d420-1111-4444-8888-5fb9a9e35253",
            version_date="2026-02-26",
            computed_at="2026-02-26T12:00:00+00:00",
            profile_count=12,
            interaction_edge_count=32,
            candidate_row_count=12,
            published=True,
            publish_block_reason=None,
            gate_input_passed=True,
            gate_embedding_passed=True,
            gate_persistence_passed=True,
            quality_metrics={"spread_x": 1.2, "spread_y": 1.8},
            stage_timings_ms={"fetch": 4.3, "compute": 22.1},
            gate_details={"persisted_row_count": 12},
        )

    mock_sb.rpc.assert_called_once()
    rpc_name, rpc_payload = mock_sb.rpc.call_args.args
    assert rpc_name == "record_compute_run_diagnostics"
    assert "p_payload" in rpc_payload
    assert rpc_payload["p_payload"]["run_id"] == "b7beeb09-1111-4444-8888-0a6db86fd243"
    assert rpc_payload["p_payload"]["published"] is True
    assert rpc_payload["p_payload"]["gate_input_passed"] is True

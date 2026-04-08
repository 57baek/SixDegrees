"""Tests for POST /interactions/{like,comment,dm} endpoints.

Basic status/response tests and no-JWT/self-interaction tests are already
covered in tests/test_contracts.py. This file adds the canonical pair ordering
tests not covered there:

  - acting_user_id < target_user_id  → uid_a=acting, uid_b=target
  - target_user_id < acting_user_id  → uid_a=target, uid_b=acting

The conftest `client` fixture sets acting_user_id = "test-user-uuid".
"""


# ── Canonical ordering: acting < target ───────────────────────────────────

def test_like_canonical_order_acting_less_than_target(client, mock_sb):
    """POST /interactions/like sets uid_a=acting, uid_b=target when acting < target."""
    # "test-user-uuid" < "zzz-user-uuid" lexicographically
    response = client.post("/interactions/like", json={"target_user_id": "zzz-user-uuid"})
    assert response.status_code == 200

    increment_calls = [
        call
        for call in mock_sb.rpc.call_args_list
        if call.args and call.args[0] == "increment_interaction"
    ]
    assert increment_calls, "Expected increment_interaction RPC call"

    payload = increment_calls[-1].args[1]
    assert payload["p_user_id_a"] == "test-user-uuid"
    assert payload["p_user_id_b"] == "zzz-user-uuid"
    assert payload["p_user_id_a"] < payload["p_user_id_b"], (
        "uid_a must be strictly less than uid_b (canonical ordering)"
    )


def test_comment_canonical_order_acting_less_than_target(client, mock_sb):
    """POST /interactions/comment sets uid_a=acting, uid_b=target when acting < target."""
    response = client.post("/interactions/comment", json={"target_user_id": "zzz-user-uuid"})
    assert response.status_code == 200

    increment_calls = [
        call
        for call in mock_sb.rpc.call_args_list
        if call.args and call.args[0] == "increment_interaction"
    ]
    assert increment_calls, "Expected increment_interaction RPC call"

    payload = increment_calls[-1].args[1]
    assert payload["p_user_id_a"] == "test-user-uuid"
    assert payload["p_user_id_b"] == "zzz-user-uuid"
    assert payload["p_user_id_a"] < payload["p_user_id_b"]


def test_dm_canonical_order_acting_less_than_target(client, mock_sb):
    """POST /interactions/dm sets uid_a=acting, uid_b=target when acting < target."""
    response = client.post("/interactions/dm", json={"target_user_id": "zzz-user-uuid"})
    assert response.status_code == 200

    increment_calls = [
        call
        for call in mock_sb.rpc.call_args_list
        if call.args and call.args[0] == "increment_interaction"
    ]
    assert increment_calls, "Expected increment_interaction RPC call"

    payload = increment_calls[-1].args[1]
    assert payload["p_user_id_a"] == "test-user-uuid"
    assert payload["p_user_id_b"] == "zzz-user-uuid"
    assert payload["p_user_id_a"] < payload["p_user_id_b"]


# ── Canonical ordering: target < acting ───────────────────────────────────

def test_like_canonical_order_target_less_than_acting(client, mock_sb):
    """POST /interactions/like sets uid_a=target, uid_b=acting when target < acting."""
    # "aaa-user-uuid" < "test-user-uuid" lexicographically
    response = client.post("/interactions/like", json={"target_user_id": "aaa-user-uuid"})
    assert response.status_code == 200

    increment_calls = [
        call
        for call in mock_sb.rpc.call_args_list
        if call.args and call.args[0] == "increment_interaction"
    ]
    assert increment_calls, "Expected increment_interaction RPC call"

    payload = increment_calls[-1].args[1]
    assert payload["p_user_id_a"] == "aaa-user-uuid"
    assert payload["p_user_id_b"] == "test-user-uuid"
    assert payload["p_user_id_a"] < payload["p_user_id_b"], (
        "uid_a must be strictly less than uid_b (canonical ordering)"
    )


def test_dm_canonical_order_target_less_than_acting(client, mock_sb):
    """POST /interactions/dm sets uid_a=target, uid_b=acting when target < acting."""
    response = client.post("/interactions/dm", json={"target_user_id": "aaa-user-uuid"})
    assert response.status_code == 200

    increment_calls = [
        call
        for call in mock_sb.rpc.call_args_list
        if call.args and call.args[0] == "increment_interaction"
    ]
    assert increment_calls, "Expected increment_interaction RPC call"

    payload = increment_calls[-1].args[1]
    assert payload["p_user_id_a"] == "aaa-user-uuid"
    assert payload["p_user_id_b"] == "test-user-uuid"
    assert payload["p_user_id_a"] < payload["p_user_id_b"]

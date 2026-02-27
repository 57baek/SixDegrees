import pytest

from services.map_pipeline.contracts import EgoCoordinateRow, EgoProfileRow
from services.map_pipeline.ego_map import build_ego_map


def _coordinate_rows() -> list[EgoCoordinateRow]:
    return [
        EgoCoordinateRow(
            user_id="requester",
            x=10.0,
            y=5.0,
            computed_at="2026-02-26T00:00:00Z",
            version_date="2026-02-26",
        ),
        EgoCoordinateRow(
            user_id="mutual-a",
            x=14.0,
            y=11.0,
            computed_at="2026-02-26T00:00:00Z",
            version_date="2026-02-26",
        ),
        EgoCoordinateRow(
            user_id="mutual-b",
            x=7.0,
            y=9.0,
            computed_at="2026-02-26T00:00:00Z",
            version_date="2026-02-26",
        ),
        EgoCoordinateRow(
            user_id="one-way",
            x=20.0,
            y=8.0,
            computed_at="2026-02-26T00:00:00Z",
            version_date="2026-02-26",
        ),
        EgoCoordinateRow(
            user_id="suggestion-a",
            x=11.0,
            y=6.0,
            computed_at="2026-02-26T00:00:00Z",
            version_date="2026-02-26",
        ),
        EgoCoordinateRow(
            user_id="suggestion-b",
            x=9.5,
            y=5.5,
            computed_at="2026-02-26T00:00:00Z",
            version_date="2026-02-26",
        ),
    ]


def _profile_rows() -> list[EgoProfileRow]:
    return [
        EgoProfileRow(id="requester", nickname="Requester", friends=["mutual-a", "mutual-b"]),
        EgoProfileRow(id="mutual-a", nickname="Mutual A", friends=["requester"]),
        EgoProfileRow(id="mutual-b", nickname="Mutual B", friends=["requester"]),
        EgoProfileRow(id="one-way", nickname="One Way", friends=[]),
        EgoProfileRow(id="suggestion-a", nickname="Suggestion A", friends=[]),
        EgoProfileRow(id="suggestion-b", nickname="Suggestion B", friends=[]),
    ]


def test_requester_is_forced_to_origin():
    nodes = build_ego_map("requester", _coordinate_rows(), _profile_rows())

    requester = next(node for node in nodes if node.user_id == "requester")
    assert requester.x == pytest.approx(0.0, abs=1e-12)
    assert requester.y == pytest.approx(0.0, abs=1e-12)
    assert requester.is_suggestion is False


def test_filters_to_mutual_friends_only():
    nodes = build_ego_map("requester", _coordinate_rows(), _profile_rows(), max_suggestions=0)

    included_ids = {node.user_id for node in nodes}
    assert included_ids == {"requester", "mutual-a", "mutual-b"}


def test_coordinates_are_translated_relative_to_requester():
    nodes = build_ego_map("requester", _coordinate_rows(), _profile_rows(), max_suggestions=0)
    node_map = {node.user_id: node for node in nodes}

    assert node_map["mutual-a"].x == pytest.approx(4.0)
    assert node_map["mutual-a"].y == pytest.approx(6.0)
    assert node_map["mutual-b"].x == pytest.approx(-3.0)
    assert node_map["mutual-b"].y == pytest.approx(4.0)


def test_adds_bounded_suggestions_when_mutuals_sparse():
    sparse_profiles = [
        EgoProfileRow(id="requester", nickname="Requester", friends=[]),
        EgoProfileRow(id="mutual-a", nickname="Mutual A", friends=["requester"]),
        EgoProfileRow(id="mutual-b", nickname="Mutual B", friends=["requester"]),
        EgoProfileRow(id="one-way", nickname="One Way", friends=[]),
        EgoProfileRow(id="suggestion-a", nickname="Suggestion A", friends=[]),
        EgoProfileRow(id="suggestion-b", nickname="Suggestion B", friends=[]),
    ]
    nodes = build_ego_map("requester", _coordinate_rows(), sparse_profiles, max_suggestions=2)

    suggestion_nodes = [node for node in nodes if node.is_suggestion]
    assert len(suggestion_nodes) == 2
    assert all(node.user_id != "requester" for node in suggestion_nodes)


def test_suggestions_are_deterministically_ordered():
    sparse_profiles = [
        EgoProfileRow(id="requester", nickname="Requester", friends=[]),
        EgoProfileRow(id="mutual-a", nickname="Mutual A", friends=[]),
        EgoProfileRow(id="mutual-b", nickname="Mutual B", friends=[]),
        EgoProfileRow(id="one-way", nickname="One Way", friends=[]),
        EgoProfileRow(id="suggestion-a", nickname="Suggestion A", friends=[]),
        EgoProfileRow(id="suggestion-b", nickname="Suggestion B", friends=[]),
    ]
    nodes = build_ego_map("requester", _coordinate_rows(), sparse_profiles, max_suggestions=3)

    suggestion_ids = [node.user_id for node in nodes if node.is_suggestion]
    assert suggestion_ids == ["suggestion-b", "suggestion-a", "mutual-b"]

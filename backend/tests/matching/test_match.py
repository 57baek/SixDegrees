"""Tests for GET /match endpoint."""

import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

from tests.conftest import TEST_USER_ID

import numpy as np
from models.user import UserProfile
from services.matching.scoring import get_top_matches, build_similarity_matrix, apply_weights, similarity_to_distance


@pytest.fixture(autouse=True)
def mock_embed_profiles(monkeypatch):
    """Patch embed_profiles in scoring.py for all tests in this file.

    Returns np.zeros((N, 384)) where N matches the number of profiles passed.
    This prevents the real sentence-transformer model from loading during tests.
    """
    def _zero_embed(profiles):
        return np.zeros((len(profiles), 384), dtype=np.float32)

    monkeypatch.setattr("services.matching.scoring.embed_profiles", _zero_embed)


# Two extra users that will appear in the profiles table alongside the acting user
OTHER_USER_ID_1 = "other-user-uuid-1"
OTHER_USER_ID_2 = "other-user-uuid-2"

_FULL_PROFILE_ROWS = [
    {
        "id": TEST_USER_ID,
        "nickname": "Test User",
        "age": 25,
        "city": "SF",
        "state": "CA",
        "interests": ["coding", "music"],
        "languages": ["English"],
        "education": "CS",
        "industry": "Tech",
        "occupation": "Engineer",
        "bio": None,
        "avatar_url": None,
        "profile_tier": 1,
        "is_admin": False,
    },
    {
        "id": OTHER_USER_ID_1,
        "nickname": "Alice",
        "age": 27,
        "city": "SF",
        "state": "CA",
        "interests": ["coding", "gaming"],
        "languages": ["English"],
        "education": "CS",
        "industry": "Tech",
        "occupation": "Designer",
        "bio": None,
        "avatar_url": None,
        "profile_tier": 1,
        "is_admin": False,
    },
    {
        "id": OTHER_USER_ID_2,
        "nickname": "Bob",
        "age": 40,
        "city": "NYC",
        "state": "NY",
        "interests": ["sports"],
        "languages": ["Spanish"],
        "education": "Biology",
        "industry": "Healthcare",
        "occupation": "Doctor",
        "bio": None,
        "avatar_url": None,
        "profile_tier": 2,
        "is_admin": False,
    },
]


def _make_client_with_profiles(rows: list[dict]):
    """Build a TestClient whose profiles table mock returns the given rows."""
    from app import app
    from routes.deps import get_current_user

    mock_sb = MagicMock()

    profiles_tbl = MagicMock()
    profiles_tbl.select.return_value.execute.return_value.data = rows

    def _table_side_effect(table_name):
        if table_name == "profiles":
            return profiles_tbl
        tbl = MagicMock()
        tbl.select.return_value.execute.return_value.data = []
        return tbl

    mock_sb.table.side_effect = _table_side_effect

    with patch("config.settings._client", mock_sb):
        with patch("services.map.scheduler.setup_scheduler", return_value=MagicMock()):
            app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID
            with TestClient(app, raise_server_exceptions=False) as tc:
                yield tc
            app.dependency_overrides.clear()


# --- Tests ---

def test_match_happy_path():
    """Returns 200 with matches list; each item has the required keys."""
    for tc in _make_client_with_profiles(_FULL_PROFILE_ROWS):
        resp = tc.get("/match")
    assert resp.status_code == 200
    body = resp.json()
    assert "matches" in body
    matches = body["matches"]
    assert len(matches) >= 1
    for m in matches:
        assert "user_id" in m
        assert "nickname" in m
        assert "similarity_score" in m
        assert isinstance(m["similarity_score"], float)


def test_match_self_excluded():
    """The acting user must not appear in the matches list."""
    for tc in _make_client_with_profiles(_FULL_PROFILE_ROWS):
        resp = tc.get("/match")
    assert resp.status_code == 200
    user_ids = [m["user_id"] for m in resp.json()["matches"]]
    assert TEST_USER_ID not in user_ids


def test_match_404_no_profiles():
    """Returns 404 when the profiles table is empty."""
    for tc in _make_client_with_profiles([]):
        resp = tc.get("/match")
    assert resp.status_code == 404
    assert "No profiles found" in resp.json()["detail"]


def test_match_404_profile_not_found():
    """Returns 404 when profiles exist but the acting user is absent."""
    rows_without_current = [r for r in _FULL_PROFILE_ROWS if r["id"] != TEST_USER_ID]
    for tc in _make_client_with_profiles(rows_without_current):
        resp = tc.get("/match")
    assert resp.status_code == 404
    assert "profile was not found" in resp.json()["detail"]


def test_match_401_no_auth(client_no_auth):
    """Returns 401 when no JWT is supplied."""
    resp = client_no_auth.get("/match")
    assert resp.status_code == 401


def test_match_top_n_negative_returns_422():
    """GET /match?top_n=-1 must return 422 (FastAPI query validation)."""
    for tc in _make_client_with_profiles(_FULL_PROFILE_ROWS):
        resp = tc.get("/match?top_n=-1")
    assert resp.status_code == 422


# --- Embedding-based scoring unit tests ---
# Test scoring.py directly, using mock embeddings to avoid model load.

def _user(uid: str, interests: list[str], bio: str | None = None) -> UserProfile:
    return UserProfile(id=uid, nickname=uid, interests=interests, bio=bio)


def test_embedding_fields_config_fallback_to_jaccard(monkeypatch):
    """When EMBEDDING_FIELDS=[], get_top_matches uses Jaccard and never calls embed_profiles."""
    from unittest.mock import MagicMock
    monkeypatch.setattr("config.settings.EMBEDDING_FIELDS", [])

    mock_embed = MagicMock()
    monkeypatch.setattr("services.matching.scoring.embed_profiles", mock_embed)

    current = _user("me", interests=["coding", "music"])
    other = _user("u1", interests=["coding", "music"])
    results = get_top_matches(current, [other], top_n=1)

    mock_embed.assert_not_called()
    assert len(results) == 1
    # Jaccard of identical interests = 1.0 * 0.4 weight = 0.4 (at minimum)
    assert results[0]["similarity_score"] > 0.0


def test_semantic_similarity_scores_higher_than_jaccard(monkeypatch):
    """Embedding cosine sim for related interests beats Jaccard.

    'hiking' and 'trail running' share zero tokens → Jaccard = 0.0.
    We inject vectors with cosine_sim ≈ 0.9 to simulate the model
    correctly identifying them as semantically related.
    """
    current = _user("me", interests=["hiking"])
    other = _user("u1", interests=["trail running"])

    # Baseline: Jaccard (EMBEDDING_FIELDS disabled)
    monkeypatch.setattr("config.settings.EMBEDDING_FIELDS", [])
    jaccard_score = get_top_matches(current, [other], top_n=1)[0]["similarity_score"]

    # Embedding: inject vectors where cosine_sim("me", "u1") ≈ 0.9
    # get_top_matches calls embed_profiles(all_users + [current_user])
    # = embed_profiles([other, current]) — other is index 0, current is index 1
    v_other = np.zeros(384, dtype=np.float32)
    v_other[0] = 0.9
    v_other[1] = float(np.sqrt(1.0 - 0.9**2))  # unit vector, cos with v_current ≈ 0.9

    v_current = np.zeros(384, dtype=np.float32)
    v_current[0] = 1.0  # unit vector along dim 0

    def _embed_with_vectors(profiles):
        result = np.zeros((len(profiles), 384), dtype=np.float32)
        for i, p in enumerate(profiles):
            if p.id == "u1":
                result[i] = v_other
            elif p.id == "me":
                result[i] = v_current
        return result

    monkeypatch.setattr("config.settings.EMBEDDING_FIELDS", ["interests", "bio"])
    monkeypatch.setattr("services.matching.scoring.embed_profiles", _embed_with_vectors)

    embedding_score = get_top_matches(current, [other], top_n=1)[0]["similarity_score"]

    assert embedding_score > jaccard_score, (
        f"Expected embedding score ({embedding_score}) > jaccard score ({jaccard_score})"
    )


# --- build_similarity_matrix, apply_weights, similarity_to_distance direct tests ---

def _make_user(uid: str) -> UserProfile:
    return UserProfile(
        id=uid, nickname=uid,
        interests=["coding"], languages=["English"],
        city="SF", state="CA", age=25,
        education="CS", industry="Tech",
    )


def test_build_similarity_matrix_shape(monkeypatch):
    """build_similarity_matrix returns (N, N, F) shape."""
    monkeypatch.setattr("config.settings.EMBEDDING_FIELDS", [])
    users = [_make_user("u1"), _make_user("u2"), _make_user("u3")]
    matrix = build_similarity_matrix(users)
    assert matrix.shape == (3, 3, 6)


def test_build_similarity_matrix_with_embeddings_none_and_fields_set(monkeypatch):
    """build_similarity_matrix computes embeddings internally when embeddings=None and EMBEDDING_FIELDS non-empty."""
    monkeypatch.setattr("config.settings.EMBEDDING_FIELDS", ["interests"])
    def _zero_embed(profiles):
        return np.zeros((len(profiles), 384), dtype=np.float32)
    monkeypatch.setattr("services.matching.scoring.embed_profiles", _zero_embed)
    users = [_make_user("u1"), _make_user("u2")]
    matrix = build_similarity_matrix(users, embeddings=None)
    assert matrix.shape == (2, 2, 6)


def test_apply_weights_returns_NxN(monkeypatch):
    """apply_weights collapses (N, N, F) to (N, N) via dot product."""
    monkeypatch.setattr("config.settings.EMBEDDING_FIELDS", [])
    users = [_make_user("u1"), _make_user("u2")]
    matrix = build_similarity_matrix(users)
    weighted = apply_weights(matrix)
    assert weighted.shape == (2, 2)
    assert np.all(weighted >= 0.0) and np.all(weighted <= 1.0)


def test_similarity_to_distance_diagonal_zero(monkeypatch):
    """similarity_to_distance diagonal is always 0."""
    monkeypatch.setattr("config.settings.EMBEDDING_FIELDS", [])
    users = [_make_user("u1"), _make_user("u2"), _make_user("u3")]
    matrix = build_similarity_matrix(users)
    weighted = apply_weights(matrix)
    dist = similarity_to_distance(weighted)
    assert dist.shape == (3, 3)
    assert np.all(np.diag(dist) == 0.0)


def test_tiered_categorical_same_category_returns_half():
    """Two values in the same category but not identical → 0.5."""
    from services.matching.similarity import tiered_categorical, FIELD_OF_STUDY_CATEGORIES
    cat_map = FIELD_OF_STUDY_CATEGORIES
    by_cat: dict[str, list[str]] = {}
    for k, v in cat_map.items():
        by_cat.setdefault(v, []).append(k)
    same_cat_pair = next((vals for vals in by_cat.values() if len(vals) >= 2), None)
    assert same_cat_pair is not None, "No same-category pair found in FIELD_OF_STUDY_CATEGORIES"
    a, b = same_cat_pair[0], same_cat_pair[1]
    score = tiered_categorical(a, b, cat_map)
    assert score == 0.5

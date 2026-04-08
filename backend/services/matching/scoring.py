import numpy as np
from models.user import UserProfile
from config.settings import PROFILE_WEIGHTS
import config.settings as _cfg
from services.matching.embedder import embed_profiles, cosine_sim, _FALLBACK_DIM
from services.matching.similarity import (
    jaccard,
    tiered_location,
    tiered_categorical,
    inverse_distance_age,
    FIELD_OF_STUDY_CATEGORIES,
    INDUSTRY_CATEGORIES,
)

FEATURE_COLS = list(PROFILE_WEIGHTS.keys())


def _build_embeddings(profiles: list[UserProfile]) -> dict[str, np.ndarray]:
    """Embed profiles and return a dict keyed by user ID. Only called when EMBEDDING_FIELDS is non-empty."""
    raw = embed_profiles(profiles)
    return {profiles[i].id: raw[i] for i in range(len(profiles))}


def _text_score(u1: UserProfile, u2: UserProfile, embeddings: dict[str, np.ndarray]) -> float:
    """Cosine sim (embedding) or Jaccard fallback depending on EMBEDDING_FIELDS."""
    if _cfg.EMBEDDING_FIELDS:
        return cosine_sim(embeddings[u1.id], embeddings[u2.id])
    return jaccard(u1.interests, u2.interests, stem=True)


def _similarity_vector(
    u1: UserProfile,
    u2: UserProfile,
    embeddings: dict[str, np.ndarray],
) -> list[float]:
    """Compute raw [0,1] similarity score per field for a user pair."""
    return [
        _text_score(u1, u2, embeddings),
        tiered_location(u1.city, u1.state, u2.city, u2.state),
        jaccard(u1.languages, u2.languages),
        tiered_categorical(u1.education, u2.education, FIELD_OF_STUDY_CATEGORIES),
        tiered_categorical(u1.industry, u2.industry, INDUSTRY_CATEGORIES),
        inverse_distance_age(u1.age, u2.age),
    ]


def _profile_similarity(
    u1: UserProfile,
    u2: UserProfile,
    embeddings: dict[str, np.ndarray],
) -> float:
    """Weighted similarity score in [0, 1] between two users."""
    scores = _similarity_vector(u1, u2, embeddings)
    weights = [
        PROFILE_WEIGHTS["interests"],
        PROFILE_WEIGHTS["location"],
        PROFILE_WEIGHTS["languages"],
        PROFILE_WEIGHTS["education"],
        PROFILE_WEIGHTS["industry"],
        PROFILE_WEIGHTS["age"],
    ]
    return sum(s * w for s, w in zip(scores, weights))


def get_top_matches(
    current_user: UserProfile,
    all_users: list[UserProfile],
    top_n: int = 10,
) -> list[dict]:
    """Return top_n most similar users sorted by descending similarity score.

    all_users must NOT include current_user.
    Returns list of {"user": UserProfile, "similarity_score": float}.
    When EMBEDDING_FIELDS is empty, embed_profiles is never called.
    """
    all_profiles = all_users + [current_user]
    if _cfg.EMBEDDING_FIELDS:
        embeddings = _build_embeddings(all_profiles)
    else:
        embeddings = {p.id: np.zeros(_FALLBACK_DIM, dtype=np.float32) for p in all_profiles}

    scored = [
        {"user": u, "similarity_score": round(_profile_similarity(current_user, u, embeddings), 4)}
        for u in all_users
    ]
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:top_n]


def build_similarity_matrix(
    users: list[UserProfile],
    embeddings: dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    """Build an (N x N x F) matrix of per-field similarity scores.

    Returns shape (N, N, F). If embeddings is None, computes internally.
    """
    if embeddings is None:
        if _cfg.EMBEDDING_FIELDS:
            embeddings = _build_embeddings(users)
        else:
            embeddings = {p.id: np.zeros(_FALLBACK_DIM, dtype=np.float32) for p in users}

    n = len(users)
    f = len(FEATURE_COLS)
    matrix = np.zeros((n, n, f))
    for i in range(n):
        for j in range(i + 1, n):
            vec = _similarity_vector(users[i], users[j], embeddings)
            matrix[i][j] = vec
            matrix[j][i] = vec
    return matrix


def apply_weights(
    sim_matrix: np.ndarray,
    weights: dict[str, float] = PROFILE_WEIGHTS,
) -> np.ndarray:
    """Dot-multiply each feature dimension by its weight. Returns (N, N)."""
    weight_vec = np.array([weights[col] for col in FEATURE_COLS])
    return np.dot(sim_matrix, weight_vec)


def similarity_to_distance(weighted_scores: np.ndarray) -> np.ndarray:
    """Convert similarity to distance: 1 - similarity. Returns (N, N)."""
    dist = 1.0 - weighted_scores
    np.fill_diagonal(dist, 0.0)
    return dist

import numpy as np

from models.user import UserProfile
from services.map_pipeline.contracts import SparseEmbeddingInput
from services.map_pipeline.sparse_embedding import build_sparse_profile_embedding


def _make_user(uid: str, i: int) -> UserProfile:
    return UserProfile(
        id=uid,
        nickname=uid,
        interests=["coding", f"interest-{i % 5}"],
        languages=["English", "Spanish" if i % 2 else "French"],
        city=f"City-{i % 4}",
        state=f"ST-{i % 3}",
        education="Computer Science" if i % 2 else "Design",
        occupation="Engineer" if i % 3 else "Artist",
        industry="Technology" if i % 2 else "Media",
        age=20 + i,
        timezone="UTC",
    )


def test_sparse_embedding_returns_sparse_edge_set_and_coordinates():
    users = [_make_user(f"u{i:02d}", i) for i in range(20)]

    result = build_sparse_profile_embedding(
        SparseEmbeddingInput(users=users, neighbor_count=4, random_state=42)
    )

    assert result.coordinates.shape == (20, 2)
    assert len(result.user_ids) == 20
    dense_edge_count = 20 * 19 // 2
    assert len(result.profile_edges) < dense_edge_count
    assert all(0.0 <= edge.final_weight <= 1.0 for edge in result.profile_edges)


def test_sparse_embedding_is_deterministic_with_fixed_seed():
    users = [_make_user(f"u{i:02d}", i) for i in range(15)]

    run_a = build_sparse_profile_embedding(
        SparseEmbeddingInput(users=users, neighbor_count=5, random_state=42)
    )
    run_b = build_sparse_profile_embedding(
        SparseEmbeddingInput(users=users, neighbor_count=5, random_state=42)
    )

    assert run_a.user_ids == run_b.user_ids
    assert np.allclose(run_a.coordinates, run_b.coordinates)

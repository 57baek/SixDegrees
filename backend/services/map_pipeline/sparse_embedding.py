"""Sparse profile-manifold embedding stage."""

from __future__ import annotations

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction import DictVectorizer
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize

from models.user import UserProfile
from services.map_pipeline.contracts import (
    SparseEdge,
    SparseEmbeddingInput,
    SparseEmbeddingResult,
)


def build_sparse_profile_embedding(input_data: SparseEmbeddingInput) -> SparseEmbeddingResult:
    """Build initial 2D coordinates without dense NxN precomputation."""
    users = input_data.users
    n_users = len(users)
    if n_users < 10:
        raise ValueError(
            f"Sparse embedding requires at least 10 users; received {n_users}."
        )

    user_ids = [user.id for user in users]
    vectorizer = DictVectorizer(sparse=True)
    profile_matrix = vectorizer.fit_transform(_profile_feature_rows(users))
    profile_matrix = normalize(profile_matrix, norm="l2", axis=1)

    projection = TruncatedSVD(n_components=2, random_state=input_data.random_state)
    coordinates = projection.fit_transform(profile_matrix)
    coordinates = coordinates - coordinates.mean(axis=0, keepdims=True)

    neighbor_count = min(max(2, input_data.neighbor_count), n_users - 1)
    neighbors = NearestNeighbors(n_neighbors=neighbor_count + 1, metric="cosine")
    neighbors.fit(profile_matrix)
    distance_graph = neighbors.kneighbors_graph(profile_matrix, mode="distance")
    distance_graph = distance_graph.maximum(distance_graph.T)
    profile_edges = _graph_to_edges(user_ids, distance_graph)

    return SparseEmbeddingResult(
        user_ids=user_ids,
        coordinates=coordinates.astype(float),
        profile_edges=profile_edges,
    )


def _profile_feature_rows(users: list[UserProfile]) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for user in users:
        row: dict[str, float] = {
            f"city:{user.city.lower()}": 1.0,
            f"state:{user.state.lower()}": 1.0,
            f"education:{user.education.lower()}": 1.0,
            f"industry:{user.industry.lower()}": 1.0,
            f"timezone:{user.timezone.lower()}": 1.0,
            f"occupation:{(user.occupation or '').lower()}": 1.0,
            f"age_bucket:{_age_bucket(user.age)}": 1.0,
        }
        for interest in user.interests:
            row[f"interest:{interest.lower()}"] = 1.0
        for language in user.languages:
            row[f"language:{language.lower()}"] = 1.0
        rows.append(row)
    return rows


def _age_bucket(age: int) -> str:
    lower = int(age / 5) * 5
    return f"{lower}-{lower + 4}"


def _graph_to_edges(user_ids: list[str], distance_graph) -> list[SparseEdge]:
    graph_coo = distance_graph.tocoo()
    edge_map: dict[tuple[int, int], float] = {}

    for row_idx, col_idx, distance in zip(
        graph_coo.row,
        graph_coo.col,
        graph_coo.data,
    ):
        if row_idx == col_idx:
            continue
        a_idx, b_idx = (row_idx, col_idx) if row_idx < col_idx else (col_idx, row_idx)
        similarity = float(np.clip(1.0 - float(distance), 0.0, 1.0))
        current = edge_map.get((a_idx, b_idx), 0.0)
        if similarity > current:
            edge_map[(a_idx, b_idx)] = similarity

    return [
        SparseEdge(
            user_id_a=user_ids[a_idx],
            user_id_b=user_ids[b_idx],
            interaction_weight=weight,
            recency_weight=1.0,
            final_weight=weight,
        )
        for (a_idx, b_idx), weight in edge_map.items()
    ]

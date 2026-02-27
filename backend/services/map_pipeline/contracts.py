"""Typed contracts for sparse map compute stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

import numpy as np

from models.user import UserProfile


Coordinate = tuple[float, float]
RawInteractionCounts = dict[tuple[str, str], dict[str, int | float]]


@dataclass(frozen=True)
class SparseEdge:
    """Canonical sparse edge between two users."""

    user_id_a: str
    user_id_b: str
    interaction_weight: float
    recency_weight: float
    final_weight: float
    weighted_interactions: float = 0.0
    sensitivity_multiplier: float = 1.0


@dataclass(frozen=True)
class InteractionSensitivity:
    strength_scale: float = 1.0
    curve_exponent: float = 0.65
    normalizer: float = 8.0
    max_weight: float = 0.92


@dataclass(frozen=True)
class SparseEmbeddingInput:
    users: list[UserProfile]
    neighbor_count: int = 8
    random_state: int = 42


@dataclass(frozen=True)
class SparseEmbeddingResult:
    user_ids: list[str]
    coordinates: np.ndarray
    profile_edges: list[SparseEdge]


@dataclass(frozen=True)
class RefinementInput:
    user_ids: list[str]
    base_coordinates: np.ndarray
    profile_edges: list[SparseEdge]
    raw_interaction_counts: RawInteractionCounts
    step_size: float = 0.08
    iterations: int = 12
    interaction_sensitivity: InteractionSensitivity | None = None


@dataclass(frozen=True)
class RefinementResult:
    user_ids: list[str]
    coordinates: np.ndarray
    interaction_edges: list[SparseEdge]


class StabilityMetrics(TypedDict):
    moved_count: int
    mean_delta: float
    p95_delta: float
    max_delta: float


@dataclass(frozen=True)
class StabilityInput:
    user_ids: list[str]
    candidate_coordinates: np.ndarray
    prior_coordinates: dict[str, Coordinate] | None
    max_delta: float


@dataclass(frozen=True)
class StabilityResult:
    user_ids: list[str]
    coordinates: np.ndarray
    metrics: StabilityMetrics


@dataclass(frozen=True)
class EgoCoordinateRow:
    user_id: str
    x: float
    y: float
    computed_at: str
    version_date: str


@dataclass(frozen=True)
class EgoProfileRow:
    id: str
    nickname: str
    friends: list[str]


@dataclass(frozen=True)
class EgoMapNode:
    user_id: str
    x: float
    y: float
    tier: int
    nickname: str
    is_suggestion: bool = False

"""Typed contracts for sparse map compute stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

import numpy as np

from models.user import UserProfile


Coordinate = tuple[float, float]
RawInteractionCounts = dict[tuple[str, str], dict[str, int | float]]
InteractionSensitivityMode = Literal["natural", "strong-bounded", "uncapped"]


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
    mode: InteractionSensitivityMode = "natural"
    strength_scale: float | None = None
    curve_exponent: float | None = None
    normalizer: float | None = None
    max_weight: float | None = None


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

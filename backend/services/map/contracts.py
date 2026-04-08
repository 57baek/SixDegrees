from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from models.user import UserProfile


@dataclass
class PipelineInput:
    profiles: list[UserProfile]
    interactions: list[dict]   # rows from interactions table

    @property
    def user_ids(self) -> list[str]:
        return [p.id for p in self.profiles]


@dataclass
class PipelineResult:
    user_ids: list[str]        # ordered list, index matches coords rows
    coords: np.ndarray         # shape (N, 2)
    edge_count: int            # number of non-zero interaction pairs
    duration_ms: int


@dataclass
class EgoMapNode:
    user_id: str
    nickname: str
    avatar_url: str | None
    x: float
    y: float
    tier: int


@dataclass
class EgoMapResponse:
    coordinates: list[EgoMapNode]
    computed_at: str           # ISO 8601 timestamp

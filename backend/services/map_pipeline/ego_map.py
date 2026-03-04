from __future__ import annotations

from math import hypot
from typing import Iterable

from services.map_pipeline.contracts import EgoCoordinateRow, EgoMapNode, EgoProfileRow


def _normalize_coordinate_rows(rows: Iterable[EgoCoordinateRow | dict]) -> list[EgoCoordinateRow]:
    normalized: list[EgoCoordinateRow] = []
    for row in rows:
        if isinstance(row, EgoCoordinateRow):
            normalized.append(row)
            continue
        normalized.append(
            EgoCoordinateRow(
                user_id=str(row["user_id"]),
                x=float(row["x"]),
                y=float(row["y"]),
                computed_at=str(row.get("computed_at", "")),
                version_date=str(row.get("version_date", "")),
            )
        )
    return normalized


def _normalize_profile_rows(rows: Iterable[EgoProfileRow | dict]) -> list[EgoProfileRow]:
    normalized: list[EgoProfileRow] = []
    for row in rows:
        if isinstance(row, EgoProfileRow):
            normalized.append(row)
            continue
        friends = row.get("friends") or []
        normalized.append(
            EgoProfileRow(
                id=str(row["id"]),
                nickname=str(row.get("nickname", "")),
                friends=[str(friend_id) for friend_id in friends],
            )
        )
    return normalized


def build_ego_map(
    requesting_user_id: str,
    coordinate_rows: Iterable[EgoCoordinateRow | dict],
    profile_rows: Iterable[EgoProfileRow | dict],
    max_suggestions: int = 3,
) -> list[EgoMapNode]:
    normalized_coordinates = _normalize_coordinate_rows(coordinate_rows)
    normalized_profiles = _normalize_profile_rows(profile_rows)

    if not normalized_coordinates:
        raise ValueError("coordinate rows are required")

    coordinate_map = {row.user_id: row for row in normalized_coordinates}
    if requesting_user_id not in coordinate_map:
        raise ValueError("requesting user coordinate row is missing")

    profile_map = {row.id: row for row in normalized_profiles}
    profile_friend_sets = {row.id: set(row.friends) for row in normalized_profiles}
    requester_profile = profile_map.get(requesting_user_id)
    requester_friends = profile_friend_sets.get(requesting_user_id, set())

    requester_coordinate = coordinate_map[requesting_user_id]

    mutual_ids: set[str] = set()
    for friend_id in requester_friends:
        if friend_id not in profile_map:
            continue
        if requesting_user_id not in profile_friend_sets.get(friend_id, set()):
            continue
        if friend_id in coordinate_map:
            mutual_ids.add(friend_id)

    nodes: list[EgoMapNode] = [
        EgoMapNode(
            user_id=requesting_user_id,
            x=0.0,
            y=0.0,
            tier=1,
            nickname=requester_profile.nickname if requester_profile else "",
            is_suggestion=False,
        )
    ]

    for mutual_id in sorted(mutual_ids):
        row = coordinate_map[mutual_id]
        profile = profile_map.get(mutual_id)
        nodes.append(
            EgoMapNode(
                user_id=mutual_id,
                x=row.x - requester_coordinate.x,
                y=row.y - requester_coordinate.y,
                tier=1,
                nickname=profile.nickname if profile else "",
                is_suggestion=False,
            )
        )

    if max_suggestions <= 0:
        return nodes

    candidate_suggestions: list[tuple[float, str, EgoMapNode]] = []
    for user_id, row in coordinate_map.items():
        if user_id == requesting_user_id or user_id in mutual_ids:
            continue
        profile = profile_map.get(user_id)
        translated_x = row.x - requester_coordinate.x
        translated_y = row.y - requester_coordinate.y
        distance = hypot(translated_x, translated_y)
        candidate_suggestions.append(
            (
                distance,
                user_id,
                EgoMapNode(
                    user_id=user_id,
                    x=translated_x,
                    y=translated_y,
                    tier=2,
                    nickname=profile.nickname if profile else "",
                    is_suggestion=True,
                ),
            )
        )

    candidate_suggestions.sort(key=lambda entry: (entry[0], entry[1]))
    nodes.extend(node for _, _, node in candidate_suggestions[:max_suggestions])
    return nodes

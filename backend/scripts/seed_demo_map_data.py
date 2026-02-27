"""Deterministic seed utilities for Phase 24 demo map data."""

import math
import os
import sys
from datetime import UTC, date, datetime
from uuid import NAMESPACE_DNS, uuid5

# Allow running from any directory (not just backend/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DEMO_USER_COUNT = 100
ELEANOR_ID = "aa834b27-6e25-52c6-86de-e105a0bfc2f1"
WINSTON_ID = "afec5144-e6a3-511f-9dc2-02f8ec57d8ac"

_FIRST_NAMES = [
    "Avery",
    "Parker",
    "Jordan",
    "Quinn",
    "Morgan",
    "Taylor",
    "Riley",
    "Hayden",
    "Cameron",
    "Reese",
]
_LAST_NAMES = [
    "Anderson",
    "Bennett",
    "Cruz",
    "Diaz",
    "Ellis",
    "Foster",
    "Grant",
    "Hayes",
    "Ingram",
    "Jordan",
]
_CITIES = [
    ("Denver", "CO", "America/Denver"),
    ("Seattle", "WA", "America/Los_Angeles"),
    ("Austin", "TX", "America/Chicago"),
    ("Boston", "MA", "America/New_York"),
    ("London", "", "Europe/London"),
]
_INTEREST_GROUPS = [
    ["hiking", "photography", "camping"],
    ["music", "painting", "film"],
    ["gaming", "programming", "anime"],
    ["cooking", "travel", "yoga"],
    ["running", "soccer", "fitness"],
]
_EDUCATION = ["biology", "computer science", "design", "business", "psychology"]
_INDUSTRY = ["research", "technology", "media", "finance", "healthcare"]


def canonical_pair(uid_a: str, uid_b: str) -> tuple[str, str]:
    return (uid_a, uid_b) if uid_a < uid_b else (uid_b, uid_a)


def _demo_user_id(index: int) -> str:
    if index == 0:
        return ELEANOR_ID
    if index == 1:
        return WINSTON_ID
    return str(uuid5(NAMESPACE_DNS, f"phase24-demo-user-{index}"))


def build_demo_profiles() -> list[dict]:
    profiles: list[dict] = []

    for index in range(DEMO_USER_COUNT):
        user_id = _demo_user_id(index)
        city, state, timezone = _CITIES[index % len(_CITIES)]
        interests = _INTEREST_GROUPS[index % len(_INTEREST_GROUPS)]

        if index == 0:
            nickname = "Eleanor Colvin"
            occupation = "Field Biologist"
        elif index == 1:
            nickname = "Winston Churchill"
            occupation = "Historian"
        else:
            first_name = _FIRST_NAMES[index % len(_FIRST_NAMES)]
            last_name = _LAST_NAMES[(index // len(_FIRST_NAMES)) % len(_LAST_NAMES)]
            nickname = f"{first_name} {last_name}"
            occupation = "Product Analyst" if index % 2 == 0 else "Software Engineer"

        profiles.append(
            {
                "id": user_id,
                "nickname": nickname,
                "interests": interests,
                "city": city,
                "state": state,
                "age": 22 + (index % 19),
                "languages": ["English"] if index % 4 else ["English", "Spanish"],
                "education": _EDUCATION[index % len(_EDUCATION)],
                "industry": _INDUSTRY[index % len(_INDUSTRY)],
                "timezone": timezone,
                "occupation": occupation,
                "friends": [],
            }
        )

    eleanor_friend_ids = [profiles[i]["id"] for i in range(1, 21)]

    for index, profile in enumerate(profiles):
        if profile["id"] == ELEANOR_ID:
            profile["friends"] = eleanor_friend_ids
            continue

        ring_neighbors = [
            profiles[(index + 1) % DEMO_USER_COUNT]["id"],
            profiles[(index + 2) % DEMO_USER_COUNT]["id"],
            profiles[(index - 1) % DEMO_USER_COUNT]["id"],
        ]
        if profile["id"] in eleanor_friend_ids:
            ring_neighbors.append(ELEANOR_ID)

        deduped = sorted(set(ring_neighbors))
        profile["friends"] = deduped

    return profiles


def build_demo_interactions(profiles: list[dict]) -> list[dict]:
    by_id = {profile["id"]: profile for profile in profiles}
    interaction_by_pair: dict[tuple[str, str], dict] = {}

    for profile in profiles:
        source_id = profile["id"]
        for friend_id in profile["friends"]:
            if friend_id not in by_id or friend_id == source_id:
                continue

            user_id_a, user_id_b = canonical_pair(source_id, friend_id)
            pair_key = (user_id_a, user_id_b)
            if pair_key in interaction_by_pair:
                continue

            seed_value = int(user_id_a[:4], 16) + int(user_id_b[:4], 16)
            interaction_by_pair[pair_key] = {
                "user_id_a": user_id_a,
                "user_id_b": user_id_b,
                "likes_count": 2 + (seed_value % 9),
                "comments_count": 1 + (seed_value % 5),
                "dm_count": seed_value % 4,
            }

    eleanor_pair = canonical_pair(ELEANOR_ID, WINSTON_ID)
    interaction_by_pair[eleanor_pair] = {
        "user_id_a": eleanor_pair[0],
        "user_id_b": eleanor_pair[1],
        "likes_count": 18,
        "comments_count": 11,
        "dm_count": 5,
    }

    return sorted(
        interaction_by_pair.values(),
        key=lambda row: (row["user_id_a"], row["user_id_b"]),
    )


def build_demo_map_coordinates(profiles: list[dict]) -> list[dict]:
    version_date = date(2026, 2, 26)
    computed_at = datetime(2026, 2, 26, 0, 0, tzinfo=UTC).isoformat()
    coords: list[dict] = []

    for index, profile in enumerate(profiles):
        angle = 2.0 * math.pi * (index / DEMO_USER_COUNT)
        radius = 0.85 + (index % 5) * 0.1
        x = round(radius * math.cos(angle), 6)
        y = round(radius * math.sin(angle), 6)
        coords.append(
            {
                "user_id": profile["id"],
                "x": x,
                "y": y,
                "prev_x": x,
                "prev_y": y,
                "version_date": version_date.isoformat(),
                "computed_at": computed_at,
            }
        )

    return coords


def build_demo_dataset() -> tuple[list[dict], list[dict], list[dict]]:
    profiles = build_demo_profiles()
    interactions = build_demo_interactions(profiles)
    coordinates = build_demo_map_coordinates(profiles)
    return profiles, interactions, coordinates


def seed_demo_map_data(supabase=None) -> dict[str, int]:
    client = supabase
    if client is None:
        from config.supabase import get_supabase_client

        client = get_supabase_client()
    profiles, interactions, coordinates = build_demo_dataset()

    client.table("demo_profiles").upsert(profiles, on_conflict="id").execute()
    client.table("demo_interactions").upsert(
        interactions,
        on_conflict="user_id_a,user_id_b",
    ).execute()
    client.table("demo_map_coordinates").upsert(
        coordinates,
        on_conflict="user_id",
    ).execute()

    return {
        "profiles": len(profiles),
        "interactions": len(interactions),
        "coordinates": len(coordinates),
    }


def main() -> None:
    seeded = seed_demo_map_data()
    print("Seeded deterministic demo map data")
    print(
        f"  demo_profiles={seeded['profiles']}, "
        f"demo_interactions={seeded['interactions']}, "
        f"demo_map_coordinates={seeded['coordinates']}"
    )


if __name__ == "__main__":
    main()

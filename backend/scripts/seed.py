"""Seed 100 deterministic users into profiles + interactions.

Run with:
    cd backend && source venv/bin/activate
    python -m scripts.seed
"""
import random
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_supabase_client

# Deterministic UUID namespace
_NS = uuid.UUID("12345678-1234-5678-1234-567812345678")

def _uid(i: int) -> str:
    return str(uuid.uuid5(_NS, f"sixdegrees-user-{i}"))

ELEANOR_ID = _uid(0)
BRITA_ID = _uid(1)
FRIEND_IDS = [_uid(i) for i in range(2, 7)]  # friend_01 to friend_05

_INTEREST_POOL = [
    "art", "music", "film", "sports", "finance", "cooking", "coding",
    "hiking", "travel", "gaming", "reading", "yoga", "photography",
    "fashion", "design", "science", "politics", "history", "animals",
    "gardening",
]
_CITIES = ["NYC", "LA", "Austin", "Chicago", "Seattle", "Boston", "Denver", "Miami"]
_STATES = ["NY", "CA", "TX", "IL", "WA", "MA", "CO", "FL"]
_EDUCATIONS = ["bachelor", "master", "phd", "associate", "high school"]
_INDUSTRIES = ["tech", "media", "health", "finance", "education", "retail", "government"]
_LANGUAGES = ["english", "spanish", "french", "german", "mandarin", "japanese", "portuguese"]
_OCCUPATIONS = ["engineer", "designer", "manager", "analyst", "teacher", "doctor", "artist", "writer"]


def _build_profiles() -> list[dict]:
    profiles = []

    # Eleanor (index 0)
    profiles.append({
        "id": ELEANOR_ID,
        "nickname": "Eleanor",
        "age": 28,
        "city": "NYC",
        "state": "NY",
        "interests": ["art", "music", "film"],
        "education": "bachelor",
        "industry": "media",
        "languages": ["english"],
        "occupation": "artist",
        "profile_tier": 6,
        "is_admin": False,
    })

    # Brita (index 1)
    profiles.append({
        "id": BRITA_ID,
        "nickname": "Brita",
        "age": 45,
        "city": "Austin",
        "state": "TX",
        "interests": ["sports", "finance", "cooking"],
        "education": "phd",
        "industry": "tech",
        "languages": ["german", "spanish"],
        "occupation": "engineer",
        "profile_tier": 6,
        "is_admin": False,
    })

    # friend_01 to friend_05 (index 2–6)
    for i, fid in enumerate(FRIEND_IDS, start=1):
        rng = random.Random(i + 1000)
        profiles.append({
            "id": fid,
            "nickname": f"friend_{i:02d}",
            "age": rng.randint(22, 50),
            "city": rng.choice(_CITIES),
            "state": rng.choice(_STATES),
            "interests": rng.sample(_INTEREST_POOL, k=rng.randint(2, 5)),
            "education": rng.choice(_EDUCATIONS),
            "industry": rng.choice(_INDUSTRIES),
            "languages": rng.sample(_LANGUAGES, k=rng.randint(1, 3)),
            "occupation": rng.choice(_OCCUPATIONS),
            "profile_tier": 6,
            "is_admin": False,
        })

    # remaining 93 users (index 7–99)
    for i in range(7, 100):
        rng = random.Random(i)
        city_idx = rng.randint(0, len(_CITIES) - 1)
        profiles.append({
            "id": _uid(i),
            "nickname": f"user_{i:03d}",
            "age": rng.randint(18, 65),
            "city": _CITIES[city_idx],
            "state": _STATES[city_idx],
            "interests": rng.sample(_INTEREST_POOL, k=rng.randint(1, 6)),
            "education": rng.choice(_EDUCATIONS),
            "industry": rng.choice(_INDUSTRIES),
            "languages": rng.sample(_LANGUAGES, k=rng.randint(1, 3)),
            "occupation": rng.choice(_OCCUPATIONS),
            "profile_tier": 6,
            "is_admin": False,
        })

    return profiles


def _build_interactions(profiles: list[dict]) -> list[dict]:
    interactions = []
    eleanor_id = ELEANOR_ID

    # friend_01–friend_05: heavy interactions with Eleanor
    for fid in FRIEND_IDS:
        uid_a, uid_b = (eleanor_id, fid) if eleanor_id < fid else (fid, eleanor_id)
        interactions.append({
            "user_id_a": uid_a,
            "user_id_b": uid_b,
            "likes_count": 30,
            "comments_count": 20,
            "dm_count": 10,
        })

    # ~50 sparse random interactions among other users (exclude Eleanor-Brita)
    rng = random.Random(42)
    all_ids = [p["id"] for p in profiles]
    pairs_seen = {(min(eleanor_id, BRITA_ID), max(eleanor_id, BRITA_ID))}
    # Also exclude already-added pairs
    for fid in FRIEND_IDS:
        pairs_seen.add((min(eleanor_id, fid), max(eleanor_id, fid)))

    attempts = 0
    while len(interactions) < 55 and attempts < 1000:
        attempts += 1
        a, b = rng.sample(all_ids, 2)
        key = (min(a, b), max(a, b))
        if key in pairs_seen:
            continue
        pairs_seen.add(key)
        interactions.append({
            "user_id_a": key[0],
            "user_id_b": key[1],
            "likes_count": rng.randint(0, 15),
            "comments_count": rng.randint(0, 10),
            "dm_count": rng.randint(0, 5),
        })

    return interactions


def seed(sb=None) -> dict:
    if sb is None:
        sb = get_supabase_client()
    profiles = _build_profiles()
    interactions = _build_interactions(profiles)

    sb.table("profiles").insert(profiles).execute()
    sb.table("interactions").upsert(interactions, on_conflict="user_id_a,user_id_b").execute()

    return {"profiles": len(profiles), "interactions": len(interactions)}


if __name__ == "__main__":
    result = seed()
    print(f"Seeded {result['profiles']} profiles, {result['interactions']} interactions")

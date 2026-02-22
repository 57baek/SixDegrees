"""
SixDegrees Seed Script
======================
Inserts 20 diverse mock users into user_profiles and seeded interaction pairs
into interactions. Designed for idempotent re-runs via upsert.

Usage:
    cd /Users/BAEK/Code/sixDegrees/backend
    source venv/bin/activate
    python scripts/seed_db.py
"""

import os
import sys

# Allow running from any directory (not just backend/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.supabase import get_supabase_client  # noqa: E402


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def canonical_pair(uid_a: str, uid_b: str) -> tuple:
    """Return (smaller_uuid, larger_uuid) for canonical pair ordering."""
    return (uid_a, uid_b) if uid_a < uid_b else (uid_b, uid_a)


# ---------------------------------------------------------------------------
# User data — 5 clusters of 4 users each
# UUIDs are hardcoded so re-runs produce identical primary keys (idempotent upsert)
# ---------------------------------------------------------------------------

USER_DATA = [
    # ---- CLUSTER 1: Outdoors ----
    {
        "user_id": "3561ceb0-d433-437d-8a4f-08da002dff50",
        "display_name": "Alex Rivera",
        "interests": ["hiking", "photography", "rock climbing"],
        "city": "Denver",
        "state": "CO",
        "age": 31,
        "languages": ["English", "Spanish"],
        "field_of_study": "biology",
        "industry": "research",
        "education_level": "masters",
        "timezone": "America/Denver",
    },
    {
        "user_id": "14b4d3d7-0b1d-4e88-b67c-aec53e4c50a5",
        "display_name": "Sam Park",
        "interests": ["camping", "hiking", "photography"],
        "city": "Portland",
        "state": "OR",
        "age": 26,
        "languages": ["English", "Korean"],
        "field_of_study": "biology",
        "industry": "research",
        "education_level": "bachelors",
        "timezone": "America/Los_Angeles",
    },
    {
        "user_id": "920dda2e-b9c9-4df6-ae87-02db94d2c4a7",
        "display_name": "Jordan Lee",
        "interests": ["rock climbing", "camping", "hiking"],
        "city": "Salt Lake City",
        "state": "UT",
        "age": 34,
        "languages": ["English"],
        "field_of_study": "computer science",
        "industry": "technology",
        "education_level": "bachelors",
        "timezone": "America/Denver",
    },
    {
        "user_id": "c05707c3-592c-47c0-b9e4-acb4038940ff",
        "display_name": "Morgan Chen",
        "interests": ["photography", "camping", "travel"],
        "city": "Seattle",
        "state": "WA",
        "age": 29,
        "languages": ["English", "Mandarin"],
        "field_of_study": "graphic design",
        "industry": "media",
        "education_level": "bachelors",
        "timezone": "America/Los_Angeles",
    },
    # ---- CLUSTER 2: Creative ----
    {
        "user_id": "47c3be75-ade4-47e6-91ed-8be53a49fe19",
        "display_name": "Taylor Kim",
        "interests": ["music", "concerts", "painting"],
        "city": "Nashville",
        "state": "TN",
        "age": 24,
        "languages": ["English", "Korean"],
        "field_of_study": "music",
        "industry": "entertainment",
        "education_level": "bachelors",
        "timezone": "America/Chicago",
    },
    {
        "user_id": "d2af91cb-f81c-4fdc-9533-e4208a76e81f",
        "display_name": "Casey Brown",
        "interests": ["film", "music", "painting"],
        "city": "Austin",
        "state": "TX",
        "age": 27,
        "languages": ["English"],
        "field_of_study": "graphic design",
        "industry": "media",
        "education_level": "bachelors",
        "timezone": "America/Chicago",
    },
    {
        "user_id": "6e58b856-4fca-4ad2-b28d-c6bd259cf3b6",
        "display_name": "Avery Johnson",
        "interests": ["concerts", "music", "film"],
        "city": "New Orleans",
        "state": "LA",
        "age": 32,
        "languages": ["English", "French"],
        "field_of_study": "music",
        "industry": "entertainment",
        "education_level": "masters",
        "timezone": "America/Chicago",
    },
    {
        "user_id": "98c81b5a-491b-4837-a319-17a5852cba3f",
        "display_name": "Riley Davis",
        "interests": ["painting", "film", "concerts"],
        "city": "Chicago",
        "state": "IL",
        "age": 22,
        "languages": ["English"],
        "field_of_study": "graphic design",
        "industry": "entertainment",
        "education_level": "bachelors",
        "timezone": "America/Chicago",
    },
    # ---- CLUSTER 3: Tech/Gaming ----
    {
        "user_id": "04906e80-7ae8-4567-8e8b-c99df7176fb3",
        "display_name": "Quinn Wilson",
        "interests": ["gaming", "programming", "anime"],
        "city": "San Jose",
        "state": "CA",
        "age": 25,
        "languages": ["English", "Japanese"],
        "field_of_study": "computer science",
        "industry": "software",
        "education_level": "bachelors",
        "timezone": "America/Los_Angeles",
    },
    {
        "user_id": "4ebea0ef-acaa-41e1-83ce-cb58b83e7fbf",
        "display_name": "Drew Martinez",
        "interests": ["programming", "gaming", "sci-fi"],
        "city": "San Francisco",
        "state": "CA",
        "age": 28,
        "languages": ["English", "Spanish"],
        "field_of_study": "software engineering",
        "industry": "software",
        "education_level": "masters",
        "timezone": "America/Los_Angeles",
    },
    {
        "user_id": "af17902c-723d-4a32-a5a1-93d9fb7777ee",
        "display_name": "Skyler Thompson",
        "interests": ["anime", "gaming", "programming"],
        "city": "Tokyo",
        "state": "",
        "age": 23,
        "languages": ["English", "Japanese"],
        "field_of_study": "computer science",
        "industry": "technology",
        "education_level": "bachelors",
        "timezone": "Asia/Tokyo",
    },
    {
        "user_id": "18517002-7104-4d50-93d0-b2202a6df7ab",
        "display_name": "Cameron White",
        "interests": ["sci-fi", "programming", "anime"],
        "city": "Austin",
        "state": "TX",
        "age": 30,
        "languages": ["English"],
        "field_of_study": "data science",
        "industry": "technology",
        "education_level": "masters",
        "timezone": "America/Chicago",
    },
    # ---- CLUSTER 4: Social/Food ----
    {
        "user_id": "98915ae3-bba5-4ada-978a-b5a7234c2900",
        "display_name": "Jamie Garcia",
        "interests": ["cooking", "travel", "wine"],
        "city": "New York",
        "state": "NY",
        "age": 35,
        "languages": ["English", "Spanish"],
        "field_of_study": "business administration",
        "industry": "retail",
        "education_level": "bachelors",
        "timezone": "America/New_York",
    },
    {
        "user_id": "34e7f6ed-9832-4e1a-b212-16199030900d",
        "display_name": "Logan Anderson",
        "interests": ["yoga", "cooking", "travel"],
        "city": "Miami",
        "state": "FL",
        "age": 28,
        "languages": ["English", "Portuguese"],
        "field_of_study": "psychology",
        "industry": "healthcare",
        "education_level": "masters",
        "timezone": "America/New_York",
    },
    {
        "user_id": "50c83c5a-acab-4605-924b-ddc8cad17293",
        "display_name": "Peyton Harris",
        "interests": ["wine", "cooking", "yoga"],
        "city": "Boston",
        "state": "MA",
        "age": 33,
        "languages": ["English", "French"],
        "field_of_study": "business administration",
        "industry": "finance",
        "education_level": "masters",
        "timezone": "America/New_York",
    },
    {
        "user_id": "387ffb29-4e9e-49d0-8c82-f229e8c42932",
        "display_name": "Reese Jackson",
        "interests": ["travel", "yoga", "cooking"],
        "city": "London",
        "state": "",
        "age": 27,
        "languages": ["English", "French"],
        "field_of_study": "marketing",
        "industry": "retail",
        "education_level": "bachelors",
        "timezone": "Europe/London",
    },
    # ---- CLUSTER 5: Sports ----
    {
        "user_id": "3dd5a0fc-4486-4d8c-adbc-5f3eac37c483",
        "display_name": "Blake Robinson",
        "interests": ["soccer", "fitness", "running"],
        "city": "Boston",
        "state": "MA",
        "age": 22,
        "languages": ["English"],
        "field_of_study": "business administration",
        "industry": "healthcare",
        "education_level": "bachelors",
        "timezone": "America/New_York",
    },
    {
        "user_id": "050d9f56-ec96-406a-bb21-76bc63ce9b7d",
        "display_name": "Parker Lewis",
        "interests": ["basketball", "fitness", "soccer"],
        "city": "Atlanta",
        "state": "GA",
        "age": 26,
        "languages": ["English"],
        "field_of_study": "psychology",
        "industry": "healthcare",
        "education_level": "bachelors",
        "timezone": "America/New_York",
    },
    {
        "user_id": "a6019e32-26d1-44a7-9302-bacfc30b5874",
        "display_name": "Hayden Walker",
        "interests": ["running", "fitness", "basketball"],
        "city": "London",
        "state": "",
        "age": 31,
        "languages": ["English", "Spanish"],
        "field_of_study": "biology",
        "industry": "healthcare",
        "education_level": "masters",
        "timezone": "Europe/London",
    },
    {
        "user_id": "0d3e5ff2-83b2-4851-87eb-6186878927f1",
        "display_name": "Emery Hall",
        "interests": ["soccer", "running", "travel"],
        "city": "Chicago",
        "state": "IL",
        "age": 24,
        "languages": ["English", "German"],
        "field_of_study": "business administration",
        "industry": "finance",
        "education_level": "bachelors",
        "timezone": "America/Chicago",
    },
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_users(supabase) -> list:
    """Upsert all users and return list of inserted user_ids."""
    print(f"Seeding {len(USER_DATA)} users...")
    response = supabase.table("user_profiles").upsert(
        USER_DATA, on_conflict="user_id"
    ).execute()
    print(f"  Seeded {len(response.data)} user_profiles rows")
    return [u["user_id"] for u in USER_DATA]


def build_interactions(user_ids_by_cluster: dict) -> list:
    """Build interaction records with canonical pair ordering."""
    interactions = []

    def add(uid_a, uid_b, likes, comments, dms):
        a, b = canonical_pair(uid_a, uid_b)
        interactions.append({
            "user_id_a": a,
            "user_id_b": b,
            "likes_count": likes,
            "comments_count": comments,
            "dm_count": dms,
        })

    # Within-cluster interactions (high counts — algorithm should pull these users close)

    # Outdoors cluster
    outdoors = user_ids_by_cluster["outdoors"]
    add(outdoors[0], outdoors[1], 12, 7, 3)   # Alex <-> Sam
    add(outdoors[0], outdoors[2], 9, 5, 1)    # Alex <-> Jordan
    add(outdoors[0], outdoors[3], 8, 4, 2)    # Alex <-> Morgan
    add(outdoors[1], outdoors[2], 11, 6, 2)   # Sam <-> Jordan
    add(outdoors[1], outdoors[3], 7, 3, 1)    # Sam <-> Morgan
    add(outdoors[2], outdoors[3], 10, 5, 1)   # Jordan <-> Morgan

    # Creative cluster
    creative = user_ids_by_cluster["creative"]
    add(creative[0], creative[1], 14, 8, 3)
    add(creative[0], creative[2], 10, 6, 2)
    add(creative[0], creative[3], 9, 4, 1)
    add(creative[1], creative[2], 13, 7, 2)
    add(creative[1], creative[3], 8, 5, 1)
    add(creative[2], creative[3], 11, 6, 2)

    # Tech/Gaming cluster
    tech = user_ids_by_cluster["tech"]
    add(tech[0], tech[1], 15, 9, 4)    # Power pair — tests 95th-pct clipping in Phase 2
    add(tech[0], tech[2], 12, 7, 3)
    add(tech[0], tech[3], 10, 5, 2)
    add(tech[1], tech[2], 13, 8, 3)
    add(tech[1], tech[3], 11, 6, 2)
    add(tech[2], tech[3], 9, 5, 1)

    # Social/Food cluster
    social = user_ids_by_cluster["social"]
    add(social[0], social[1], 11, 7, 3)
    add(social[0], social[2], 9, 5, 2)
    add(social[0], social[3], 8, 4, 1)
    add(social[1], social[2], 12, 6, 2)
    add(social[1], social[3], 7, 4, 1)
    add(social[2], social[3], 10, 5, 2)

    # Sports cluster
    sports = user_ids_by_cluster["sports"]
    add(sports[0], sports[1], 10, 6, 2)
    add(sports[0], sports[2], 8, 4, 1)
    add(sports[0], sports[3], 9, 5, 2)
    add(sports[1], sports[2], 11, 7, 2)
    add(sports[1], sports[3], 7, 3, 1)
    add(sports[2], sports[3], 8, 4, 1)

    # Sparse cross-cluster interactions (low counts — algorithm keeps these further apart)
    add(outdoors[0], tech[0], 2, 1, 0)      # hiker who codes
    add(outdoors[3], creative[0], 3, 1, 0)  # photographer <-> musician
    add(tech[1], social[0], 1, 0, 0)        # programmer <-> foodie
    add(creative[3], sports[0], 2, 1, 0)    # film fan <-> runner
    add(sports[3], social[3], 3, 2, 0)      # traveler bridge

    return interactions


def seed_interactions(supabase, user_ids_by_cluster: dict):
    """Upsert all interaction pairs."""
    interactions = build_interactions(user_ids_by_cluster)
    print(f"Seeding {len(interactions)} interaction pairs...")
    response = supabase.table("interactions").upsert(
        interactions, on_conflict="user_id_a,user_id_b"
    ).execute()
    print(f"  Seeded {len(response.data)} interaction rows")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    supabase = get_supabase_client()
    print("=== SixDegrees Seed Script ===")

    # Seed users
    seed_users(supabase)

    # Build cluster index for interaction seeding
    user_ids = [u["user_id"] for u in USER_DATA]
    user_ids_by_cluster = {
        "outdoors": user_ids[0:4],
        "creative": user_ids[4:8],
        "tech":     user_ids[8:12],
        "social":   user_ids[12:16],
        "sports":   user_ids[16:20],
    }

    # Seed interactions
    seed_interactions(supabase, user_ids_by_cluster)

    # Verify
    print("\nVerification:")
    r1 = supabase.table("user_profiles").select("*").execute()
    r2 = supabase.table("interactions").select("*").execute()
    user_count = len(r1.data)
    interaction_count = len(r2.data)
    print(f"  user_profiles: {user_count} rows")
    print(f"  interactions:  {interaction_count} rows")

    # Timezone coverage check
    r3 = supabase.table("user_profiles").select("timezone").execute()
    timezones = set(row["timezone"] for row in r3.data)
    print(f"  Distinct timezones: {sorted(timezones)}")

    assert len(timezones) >= 4, f"Expected >= 4 timezones, got {len(timezones)}"
    assert user_count >= 15, f"Expected >= 15 users, got {user_count}"
    assert interaction_count >= 30, f"Expected >= 30 interaction pairs, got {interaction_count}"

    print("\nSeed complete. All assertions passed.")


if __name__ == "__main__":
    main()

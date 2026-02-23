#!/usr/bin/env python3
"""
scripts/test_map.py — People Map algorithm demo against live Supabase data.

Usage (from project root):
    cd /path/to/sixDegrees
    source backend/venv/bin/activate
    python scripts/test_map.py
"""
import os
import sys
import math

# ── Make backend importable ────────────────────────────────────────────────
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

# ── Load environment (backend/.env has SUPABASE_URL and SUPABASE_KEY) ─────
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(BACKEND_DIR, ".env"))

# ── Validate env before doing anything ────────────────────────────────────
if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in backend/.env")
    print("       Copy backend/.env.example to backend/.env and fill in your credentials.")
    sys.exit(1)

import matplotlib
matplotlib.use("MacOSX")   # Interactive window on macOS; change to "Agg" for headless
import matplotlib.pyplot as plt

from services.map_pipeline import run_pipeline_for_user
from config.supabase import get_supabase_client

# ── Constants ──────────────────────────────────────────────────────────────
# Alex Rivera (Outdoors cluster) — center user for demo
DEMO_CENTER_USER = "3561ceb0-d433-437d-8a4f-08da002dff50"
# Skyler Thompson (Tech/Gaming cluster) — far from Alex in baseline
BUMP_USER_A = "3561ceb0-d433-437d-8a4f-08da002dff50"   # Alex Rivera
BUMP_USER_B = "af17902c-723d-4a32-a5a1-93d9fb7777ee"   # Skyler Thompson
BUMP_LIKES = 60   # Inflated interaction count for sensitivity demo

TIER_COLORS = {1: "#e74c3c", 2: "#3498db", 3: "#95a5a6"}
TIER_NAMES  = {1: "Tier 1 (closest)", 2: "Tier 2", 3: "Tier 3 (outer)"}


# ── Helpers ────────────────────────────────────────────────────────────────
def fetch_coords(center_user_id: str) -> list[dict]:
    """Run full pipeline and return current map_coordinates for center user."""
    print(f"  Running pipeline for {center_user_id} ...")
    run_pipeline_for_user(center_user_id)

    sb = get_supabase_client()
    # Fetch current coordinate rows
    rows = (
        sb.table("map_coordinates")
        .select("other_user_id, x, y, tier")
        .eq("center_user_id", center_user_id)
        .eq("is_current", True)
        .execute()
    ).data

    # Enrich with display_name
    profile_rows = sb.table("user_profiles").select("user_id, display_name").execute().data
    names = {r["user_id"]: r["display_name"] for r in profile_rows}

    return [
        {
            "user_id": r["other_user_id"],
            "x": r["x"],
            "y": r["y"],
            "tier": r["tier"],
            "display_name": names.get(r["other_user_id"], r["other_user_id"][:8]),
        }
        for r in rows
    ]


def get_likes(uid_a: str, uid_b: str) -> int:
    """Return current likes_count for a canonical user pair."""
    uid_a, uid_b = min(uid_a, uid_b), max(uid_a, uid_b)
    sb = get_supabase_client()
    rows = (
        sb.table("interactions")
        .select("likes_count")
        .eq("user_id_a", uid_a)
        .eq("user_id_b", uid_b)
        .execute()
    ).data
    return rows[0]["likes_count"] if rows else 0


def set_likes(uid_a: str, uid_b: str, count: int) -> None:
    """Directly set likes_count for a pair (upsert on canonical key)."""
    uid_a, uid_b = min(uid_a, uid_b), max(uid_a, uid_b)
    get_supabase_client().table("interactions").upsert(
        {"user_id_a": uid_a, "user_id_b": uid_b, "likes_count": count},
        on_conflict="user_id_a,user_id_b",
    ).execute()


def euclidean(coords: list[dict], uid_a: str, uid_b: str) -> float | None:
    """Return euclidean distance between two users in a coordinate set."""
    lookup = {c["user_id"]: c for c in coords}
    if uid_a not in lookup or uid_b not in lookup:
        return None
    a, b = lookup[uid_a], lookup[uid_b]
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)


def plot_map(coords: list[dict], title: str, ax) -> None:
    """Plot a coordinate set on the given matplotlib axes."""
    for tier in [1, 2, 3]:
        pts = [c for c in coords if c["tier"] == tier]
        if not pts:
            continue
        ax.scatter(
            [p["x"] for p in pts],
            [p["y"] for p in pts],
            c=TIER_COLORS[tier],
            label=TIER_NAMES[tier],
            s=80,
            alpha=0.8,
        )
        for p in pts:
            ax.annotate(
                p["display_name"],
                (p["x"], p["y"]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=7,
            )
    # Mark center at origin
    ax.scatter(0, 0, c="black", marker="*", s=200, label="Alex Rivera (you)", zorder=5)
    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.4)
    ax.axvline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.4)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8)
    ax.set_xlabel("t-SNE dim 1")
    ax.set_ylabel("t-SNE dim 2")


# ── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("People Map — Algorithm Demo")
    print("=" * 60)

    # ── Step 1: Baseline ───────────────────────────────────────────────────
    print("\n[1/3] Baseline run (existing seed data):")
    baseline_coords = fetch_coords(DEMO_CENTER_USER)
    baseline_dist = euclidean(baseline_coords, BUMP_USER_A, BUMP_USER_B)
    print(f"      Coordinates computed: {len(baseline_coords)} users")
    if baseline_dist is not None:
        print(f"      Distance(Alex, Skyler) = {baseline_dist:.4f}  [baseline]")

    # Save original likes so we can restore
    original_likes = get_likes(BUMP_USER_A, BUMP_USER_B)
    print(f"\n[2/3] Bumping Alex-Skyler likes_count: {original_likes} -> {BUMP_LIKES}")
    set_likes(BUMP_USER_A, BUMP_USER_B, BUMP_LIKES)

    try:
        # ── Step 2: Bumped run ─────────────────────────────────────────────
        print("\n      Re-running pipeline with bumped interaction:")
        bumped_coords = fetch_coords(DEMO_CENTER_USER)
        bumped_dist = euclidean(bumped_coords, BUMP_USER_A, BUMP_USER_B)
        if bumped_dist is not None:
            print(f"      Distance(Alex, Skyler) = {bumped_dist:.4f}  [after bump]")
            if baseline_dist is not None:
                delta = baseline_dist - bumped_dist
                direction = "CLOSER" if delta > 0 else "farther"
                print(f"\n      Sensitivity result: distance changed by {delta:+.4f} ({direction})")
                if delta > 0:
                    print("      Algorithm sensitivity confirmed: higher interaction -> closer position")

        # ── Step 3: Plot side-by-side ──────────────────────────────────────
        print("\n[3/3] Rendering scatter plots ...")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
        plot_map(baseline_coords, "Baseline: Alex's People Map", ax1)
        plot_map(
            bumped_coords,
            f"After bumping Alex-Skyler likes to {BUMP_LIKES}",
            ax2,
        )
        plt.suptitle("People Map: Sensitivity Demonstration", fontsize=14, fontweight="bold")
        plt.tight_layout()
        plt.show()

    finally:
        # ── Restore original counts ────────────────────────────────────────
        print(f"\nRestoring likes_count to {original_likes} ...")
        set_likes(BUMP_USER_A, BUMP_USER_B, original_likes)
        print("Done. Supabase interaction counts restored to seed state.")

"""Standalone script to regenerate the UMAP regression snapshot.

Run from backend/ directory:
    python tests/fixtures/generate_snapshot.py

When to regenerate:
- After upgrading umap-learn (version pinned: 0.5.11)
- Never needed for logic changes — if the test fails, that's the point.

The snapshot captures projector.project() output on a fixed 20x20
symmetric distance matrix built with seed=0. Distances are in [0, 1].
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "umap_regression_snapshot.npy")
N = 20
SEED = 0


def _build_fixed_distance_matrix() -> np.ndarray:
    rng = np.random.default_rng(SEED)
    raw = rng.random((N, N))
    sym = (raw + raw.T) / 2
    np.fill_diagonal(sym, 0.0)
    return sym.clip(0.0, 1.0)


if __name__ == "__main__":
    from services.map.projector import project
    dist = _build_fixed_distance_matrix()
    coords = project(dist)
    np.save(OUTPUT_PATH, coords)
    print(f"Snapshot saved to {OUTPUT_PATH}  shape={coords.shape}")

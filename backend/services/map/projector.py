import numpy as np
import umap
from config.settings import UMAP_N_NEIGHBORS, UMAP_MIN_DIST, UMAP_RANDOM_STATE


def project(distance_matrix: np.ndarray) -> np.ndarray:
    n = len(distance_matrix)
    if n < 2:
        raise ValueError(f"Cannot project fewer than 2 users (got {n})")
    n_neighbors = min(UMAP_N_NEIGHBORS, n - 1)
    return umap.UMAP(
        n_components=2,
        metric="precomputed",
        n_neighbors=n_neighbors,
        min_dist=UMAP_MIN_DIST,
        random_state=UMAP_RANDOM_STATE,
    ).fit_transform(distance_matrix)

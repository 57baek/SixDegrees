import numpy as np


def validate_output(coords: np.ndarray, user_ids: list[str]) -> None:
    if coords.shape != (len(user_ids), 2):
        raise ValueError(f"Shape mismatch: {coords.shape} vs ({len(user_ids)}, 2)")
    if np.any(np.isnan(coords)) or np.any(np.isinf(coords)):
        raise ValueError("Coordinates contain NaN or Inf values")

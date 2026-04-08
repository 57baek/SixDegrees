import numpy as np
import pytest
from services.map.validation import validate_output


def _user_ids(n: int) -> list[str]:
    return [f"user-{i}" for i in range(n)]


def test_valid_coords_no_exception() -> None:
    coords = np.zeros((5, 2), dtype=float)
    validate_output(coords, _user_ids(5))  # should not raise


def test_shape_mismatch_raises() -> None:
    coords = np.zeros((5, 2), dtype=float)
    with pytest.raises(ValueError, match="Shape mismatch"):
        validate_output(coords, _user_ids(6))


def test_nan_raises() -> None:
    coords = np.zeros((5, 2), dtype=float)
    coords[2, 1] = float("nan")
    with pytest.raises(ValueError, match="NaN"):
        validate_output(coords, _user_ids(5))


def test_inf_raises() -> None:
    coords = np.zeros((5, 2), dtype=float)
    coords[0, 0] = float("inf")
    with pytest.raises(ValueError, match="NaN|Inf"):
        validate_output(coords, _user_ids(5))

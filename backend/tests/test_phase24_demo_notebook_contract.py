"""Contract smoke tests for the Phase 24 demo notebook content."""

from __future__ import annotations

import json
from pathlib import Path


def _load_notebook() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    notebook_path = repo_root / "demo" / "phase24_clustering_dimensionality_reduction_demo.ipynb"
    assert notebook_path.exists(), f"Missing notebook: {notebook_path}"
    return json.loads(notebook_path.read_text(encoding="utf-8"))


def _cell_text(cell: dict) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def test_phase24_notebook_contains_required_sections() -> None:
    notebook = _load_notebook()
    markdown_text = "\n".join(
        _cell_text(cell)
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "markdown"
    )

    required_sections = [
        "Global map (100 users)",
        "Eleanor Colvin ego subset (20 friends)",
        "Eleanor-centered coordinate shift",
        "Side-by-side before/after Eleanor map",
    ]

    for section in required_sections:
        assert section in markdown_text


def test_phase24_notebook_loads_expected_demo_artifacts() -> None:
    notebook = _load_notebook()
    source_text = "\n".join(_cell_text(cell) for cell in notebook.get("cells", []))

    expected_artifacts = [
        "phase24_global_before.csv",
        "phase24_global_after.csv",
        "phase24_eleanor_ego_before.csv",
        "phase24_eleanor_ego_after.csv",
        "phase24_eleanor_shift.csv",
        "phase24_eleanor_side_by_side.json",
    ]

    assert "DATA_DIR = Path('data')" in source_text
    for artifact in expected_artifacts:
        assert artifact in source_text


def test_phase24_notebook_has_side_by_side_before_after_visual() -> None:
    notebook = _load_notebook()
    source_text = "\n".join(_cell_text(cell) for cell in notebook.get("cells", []))

    assert "plt.subplots(1, 2" in source_text
    assert "Before amplification" in source_text
    assert "After amplification" in source_text
    assert "Eleanor Colvin" in source_text
    assert "Winston Churchill" in source_text

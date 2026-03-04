"""Contract smoke tests for Phase 25 notebook and demo guidance content."""

from __future__ import annotations

import json
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_notebook() -> dict:
    notebook_path = _repo_root() / "demo" / "phase24_clustering_dimensionality_reduction_demo.ipynb"
    assert notebook_path.exists(), f"Missing notebook: {notebook_path}"
    return json.loads(notebook_path.read_text(encoding="utf-8"))


def _load_readme() -> str:
    readme_path = _repo_root() / "demo" / "README.md"
    assert readme_path.exists(), f"Missing README: {readme_path}"
    return readme_path.read_text(encoding="utf-8")


def _cell_text(cell: dict) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def test_phase25_notebook_contains_dynamic_tuning_sections() -> None:
    notebook = _load_notebook()
    markdown_text = "\n".join(
        _cell_text(cell)
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "markdown"
    )

    required_sections = [
        "Distance trend across amplification levels",
        "Rank and force diagnostics across amplification levels",
        "Safeguards and interpretation notes for non-technical review",
    ]
    required_terms = [
        "non-technical",
        "effective pull",
        "movement clipping",
    ]

    for section in required_sections:
        assert section in markdown_text
    for term in required_terms:
        assert term in markdown_text


def test_phase25_notebook_references_dynamic_diagnostics_artifacts() -> None:
    notebook = _load_notebook()
    source_text = "\n".join(_cell_text(cell) for cell in notebook.get("cells", []))

    required_references = [
        "phase24_eleanor_winston_distance_curve.csv",
        "nearest_neighbor_rank",
        "rank_delta_from_baseline",
        "effective_pull",
        "effective_pull_delta_from_baseline",
        "movement_explanation",
    ]

    for reference in required_references:
        assert reference in source_text


def test_phase25_readme_documents_presets_and_safeguards() -> None:
    readme_text = _load_readme()

    required_phrases = [
        "Production-safe default",
        "Demo-strong sensitivity",
        "--amplification-likes",
        "--amplification-comments",
        "movement clipping",
    ]

    for phrase in required_phrases:
        assert phrase in readme_text

    assert (
        "distance + rank + force" in readme_text
        or "distance, rank, and force" in readme_text
    )

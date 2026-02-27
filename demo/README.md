# Phase 24 Demo Workflow

This directory contains deterministic artifacts and a notebook for the Phase 24 clustering/dimensionality-reduction walkthrough.

## Generate Demo Artifacts

Run from repository root:

```bash
cd backend
./venv/bin/python scripts/seed_demo_map_data.py
./venv/bin/python scripts/run_phase24_demo_pipeline.py
```

If local Supabase demo tables are unavailable, generate fixture-backed artifacts:

```bash
cd backend
./venv/bin/python scripts/run_phase24_demo_pipeline.py --use-fixture-data
```

Expected outputs are written to `demo/data/`:

- `phase24_global_before.csv`
- `phase24_global_after.csv`
- `phase24_eleanor_ego_before.csv`
- `phase24_eleanor_ego_after.csv`
- `phase24_eleanor_shift.csv`
- `phase24_eleanor_side_by_side.json`

## Open Notebook

From repository root:

```bash
jupyter notebook demo/phase24_clustering_dimensionality_reduction_demo.ipynb
```

Notebook sections:

1. Global map (100 users)
2. Eleanor Colvin ego subset (20 friends)
3. Eleanor-centered coordinate shift
4. Side-by-side before/after Eleanor map after Eleanor/Winston interaction amplification

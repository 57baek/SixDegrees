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

## Phase 25 Sensitivity Presets

Use these two presets for reproducible before/after discussions.

### Production-safe default (recommended baseline)

```bash
cd backend
./venv/bin/python scripts/run_phase24_demo_pipeline.py --use-fixture-data
```

- Keeps default interaction sensitivity configuration from backend settings.
- Keeps movement clipping safeguards enabled in the pipeline.
- Use this first when validating stability and expected day-to-day behavior.

### Demo-strong sensitivity (stakeholder walkthrough)

```bash
cd backend
./venv/bin/python scripts/run_phase24_demo_pipeline.py --use-fixture-data --amplification-likes 5000 --amplification-comments 4000
```

- Intentionally exaggerates interaction deltas to make movement signals easier to see in a meeting.
- Does not disable clipping/stability controls; only interaction amplification inputs are stronger.
- Compare this run against the production-safe run to explain distance, rank, and force changes.

Expected outputs are written to `demo/data/`:

- `phase24_global_before.csv`
- `phase24_global_after.csv`
- `phase24_eleanor_ego_before.csv`
- `phase24_eleanor_ego_after.csv`
- `phase24_eleanor_shift.csv`
- `phase24_eleanor_winston_distance_curve.csv`
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
5. Euclidean distance proof (Eleanor vs Winston)
6. Distance trend across amplification levels
7. Rank and force diagnostics across amplification levels
8. Safeguards and interpretation notes for non-technical review

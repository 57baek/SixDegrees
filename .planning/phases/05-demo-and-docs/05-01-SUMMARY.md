---
phase: 05-demo-and-docs
plan: "01"
subsystem: demo
tags: [matplotlib, python-dotenv, scatter-plot, sensitivity-demo, pipeline-validation]

# Dependency graph
requires:
  - phase: 03-pipeline-integration
    provides: run_pipeline_for_user() in services.map_pipeline — the orchestrator called by the demo script
  - phase: 01-database-foundation
    provides: user_profiles, interactions, and map_coordinates tables with seeded data
provides:
  - scripts/test_map.py — standalone matplotlib scatter plot demo with algorithm sensitivity comparison
  - matplotlib>=3.10 in backend/requirements.txt under Demo deliverables section
affects: [05-02-notebook, docs, future-demo-viewers]

# Tech tracking
tech-stack:
  added: [matplotlib 3.10.8]
  patterns:
    - "sys.path.insert(0, BACKEND_DIR) pattern for importing backend modules from scripts/"
    - "load_dotenv(dotenv_path=os.path.join(BACKEND_DIR, '.env')) for env loading in scripts"
    - "try/finally for guaranteed Supabase state restoration after demo mutations"
    - "Canonical pair ordering (min/max) enforced in Python before Supabase upsert"

key-files:
  created:
    - scripts/test_map.py
  modified:
    - backend/requirements.txt

key-decisions:
  - "matplotlib.use('MacOSX') called before import matplotlib.pyplot — order is mandatory"
  - "euclidean() returns None if either user missing from coordinates — graceful non-crash"
  - "BUMP_USER_A same UUID as DEMO_CENTER_USER (Alex Rivera) — center user is one side of the sensitivity pair"
  - "original_likes saved before mutation so try/finally can restore exact seed value"

patterns-established:
  - "Demo scripts live in scripts/ at project root, import from backend/ via sys.path.insert"
  - "Any demo mutation to Supabase must be wrapped in try/finally for restoration"

requirements-completed: [DEMO-01, DEMO-03, DEMO-04]

# Metrics
duration: 2min
completed: 2026-02-23
---

# Phase 5 Plan 01: Demo Script Summary

**Standalone matplotlib scatter plot demo running full t-SNE pipeline against live Supabase data, proving algorithm sensitivity by comparing Alex–Skyler euclidean distance before and after bumping likes_count to 60**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-23T20:22:43Z
- **Completed:** 2026-02-23T20:24:28Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `scripts/test_map.py` (193 lines) — runs full pipeline twice (baseline then bumped), prints distance comparison, renders side-by-side scatter plots
- Installed matplotlib 3.10.8 into backend venv and declared `matplotlib>=3.10` in requirements.txt under `# Demo deliverables`
- Script validates SUPABASE_URL/SUPABASE_KEY at startup and exits cleanly with a descriptive error if missing
- `try/finally` block guarantees interaction count restoration to seed state even if pipeline raises

## Task Commits

Each task was committed atomically:

1. **Task 1: Install demo dependencies and update requirements.txt** - `b78a2f7` (chore)
2. **Task 2: Create scripts/test_map.py with scatter plot and sensitivity demo** - `313f9a4` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `scripts/test_map.py` — Standalone People Map demo: runs pipeline twice, prints euclidean distance before/after bump, renders side-by-side matplotlib scatter plots with tier color-coding and display_name labels
- `backend/requirements.txt` — Added `# Demo deliverables` section with `matplotlib>=3.10`

## Decisions Made

- `matplotlib.use("MacOSX")` must be called before `import matplotlib.pyplot as plt` — already ordered correctly in the script. For headless environments, change to `"Agg"`.
- `euclidean()` returns `None` if either user is not present in the coordinate set rather than crashing — lets the script handle gracefully without try/except noise.
- UUIDs hardcoded from `backend/scripts/seed_db.py`: Alex Rivera = `3561ceb0-d433-437d-8a4f-08da002dff50`, Skyler Thompson = `af17902c-723d-4a32-a5a1-93d9fb7777ee` — verified against seed data before writing.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

The script requires `backend/.env` to be populated with `SUPABASE_URL` and `SUPABASE_KEY` (service role key). The script will exit with a descriptive error if these are missing:

```
ERROR: SUPABASE_URL and SUPABASE_KEY must be set in backend/.env
       Copy backend/.env.example to backend/.env and fill in your credentials.
```

To run the demo:
```bash
cd /path/to/sixDegrees
source backend/venv/bin/activate
python scripts/test_map.py
```

## Next Phase Readiness

- `scripts/test_map.py` is ready to run against any live Supabase instance with seeded data
- Plan 05-02 (Jupyter notebook) can import `run_pipeline_for_user` using the same `sys.path.insert` pattern established here
- matplotlib is now available in the venv for any subsequent notebook or plotting work

---
*Phase: 05-demo-and-docs*
*Completed: 2026-02-23*

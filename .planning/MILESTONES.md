# Milestones

## v1.0 People Map Algorithm Backend (Shipped: 2026-02-23)

**Phases completed:** 5 phases, 15 plans
**Files changed:** 113 | **Insertions:** ~20,500 | **LOC:** ~3,863 (Python/TS/Vue)
**Timeline:** 2026-02-01 → 2026-02-23 (22 days)

**Key accomplishments:**
- Three Supabase tables (user_profiles, interactions, map_coordinates) with indexes, RLS, and 20 seeded mock users across 5 interest clusters
- Pure t-SNE algorithm pipeline: interaction scoring with 95th-pct normalization + combined distance matrix (α×profile + β×interaction) → 2D coordinates
- DB-connected orchestrator (`run_pipeline_for_user`) wiring algorithm to live Supabase — fetch → compute → write in a single call
- FastAPI: `GET /map`, `POST /map/trigger`, three `/interactions/*` write endpoints, `PUT /profile` — all with Supabase JWT validation
- APScheduler with per-timezone CronTrigger at 19:00, started via `asynccontextmanager` lifespan
- Demo deliverables: `test_map.py` scatter plot, `people_map_demo.ipynb` notebook, `docs/API_CONTRACT.md`, `docs/DB_SCHEMA.md`

**Tech debt carried forward:**
- `POST /interactions/dm` response string: `"dm recorded"` vs spec `"dms recorded"` (1-char fix)
- `DB_SCHEMA.md` documents wrong env var `SUPABASE_SERVICE_ROLE_KEY` (should be `SUPABASE_KEY`)
- `routes/auth.py` dead-code stub (pre-existing, not registered in app.py)

---


# Coding Conventions

**Analysis Date:** 2026-02-26

## Naming Patterns

**Files:**
- Use `snake_case.py` for backend modules (for example `backend/routes/interactions.py`, `backend/services/map_pipeline/tsne_projector.py`).
- Use `PascalCase.vue` for Vue SFC components/views (for example `frontend/src/components/CreatePost.vue`, `frontend/src/views/ProfileSetup.vue`).
- Use lowercase directory names by domain (`backend/routes/`, `backend/services/matching/`, `frontend/src/lib/`).

**Functions:**
- Use `snake_case` in Python (`get_current_user` in `backend/routes/deps.py`, `build_combined_distance_matrix` in `backend/services/map_pipeline/scoring.py`).
- Use `camelCase` in Vue/JS (`handleLogin` in `frontend/src/views/Login.vue`, `fetchIncomingRequests` in `frontend/src/views/Home.vue`).
- Prefix UI event handlers with `handle` and data loaders with `load`/`fetch` (`frontend/src/components/CreatePost.vue`, `frontend/src/views/Profile.vue`).

**Variables:**
- Use `snake_case` in Python for locals and payload keys (`acting_user_id`, `raw_interaction_counts` in `backend/routes/profile.py`, `backend/services/map_pipeline/pipeline.py`).
- Use `camelCase` in Vue script blocks for refs and locals (`showChecklist`, `selectedTier` in `frontend/src/views/SignUp.vue`, `frontend/src/components/CreatePost.vue`).
- Use `UPPER_SNAKE_CASE` for constants (`INTERACTION_WEIGHTS` in `backend/config/algorithm.py`, `TEST_USER_ID` in `backend/tests/conftest.py`).

**Types:**
- Use `PascalCase` for Pydantic models (`UserProfile` in `backend/models/user.py`, `ProfileBody` in `backend/routes/profile.py`).
- Use explicit Python type hints on new/edited backend code (`list[UserProfile]`, `dict[str, float]` in `backend/services/matching/scoring.py`).

## Code Style

**Formatting:**
- Formatting tool: Not detected (`.eslintrc*`, `.prettierrc*`, `eslint.config.*`, `pyproject.toml` not present in repo root/apps).
- Keep style local to file: backend uses 4-space indentation and typed signatures (`backend/services/map_pipeline/interaction.py`); frontend uses existing quote/semicolon style per file (`frontend/src/router/index.js` vs `frontend/src/main.js`).
- Preserve current multiline dict/list formatting instead of reflowing unrelated lines (see `DEFAULT_WEIGHTS` in `backend/services/matching/scoring.py`).

**Linting:**
- Lint tool: Not detected in `frontend/package.json` and backend config files.
- Enforce consistency by following neighboring code conventions in each touched file.

## Import Organization

**Order:**
1. Standard library imports first (`import logging` in `backend/services/map_pipeline/scheduler.py`, `import math` in `backend/services/map_pipeline/tsne_projector.py`).
2. Third-party imports second (`from fastapi import APIRouter...` in `backend/routes/map.py`, `from sklearn.manifold import TSNE` in `backend/services/map_pipeline/tsne_projector.py`).
3. Local app imports last (`from services.map_pipeline import run_pipeline_for_user` in `backend/routes/map.py`).

**Path Aliases:**
- Not detected; use relative imports in frontend (`../lib/supabase` in `frontend/src/views/Login.vue`) and module-path imports rooted in backend app directory (`from routes.deps import get_current_user` in `backend/routes/profile.py`).

## Error Handling

**Patterns:**
- For backend HTTP endpoints, raise `HTTPException` with explicit status and detail (`backend/routes/interactions.py`, `backend/routes/match.py`).
- Convert domain `ValueError` to API status at route boundary (`backend/routes/map.py` maps pipeline `ValueError` to 422).
- For auth failures, always return 401 with `WWW-Authenticate: Bearer` (`backend/routes/deps.py`).
- In frontend async flows, wrap Supabase calls in `try/catch`, set UI error state, and log details (`frontend/src/views/Login.vue`, `frontend/src/views/Profile.vue`).

## Logging

**Framework:** logging + console

**Patterns:**
- Use Python `logging` in backend services where recurring jobs run (`logger.info`/`logger.error` in `backend/services/map_pipeline/scheduler.py`).
- Use `console.error` in frontend for async failure diagnostics (`frontend/src/components/Post.vue`, `frontend/src/views/Home.vue`).
- Keep user-facing messages separate from logs (`error.value = ...` in `frontend/src/components/CreatePost.vue`).

## Comments

**When to Comment:**
- Add module/function docstrings to capture constraints and contracts (`backend/services/map_pipeline/pipeline.py`, `backend/services/map_pipeline/coord_writer.py`).
- Keep milestone/contract tags when they anchor behavior (`INT-01`, `DIST-04`, `ORIG-02` in `backend/services/map_pipeline/*.py` and `backend/tests/map_pipeline/*.py`).
- Use inline comments for non-obvious side effects only (dependency overrides and scheduler patching in `backend/tests/conftest.py`).

**JSDoc/TSDoc:**
- Backend uses Python docstrings heavily for public functions.
- Frontend uses lightweight JSDoc-style comments for selected helpers (`formatDate` in `frontend/src/components/Post.vue`), but usage is not universal.

## Function Design

**Size:**
- Prefer small helpers for reusable route/service logic (`_record_interaction` in `backend/routes/interactions.py`, `_fetch_map_response` in `backend/routes/map.py`).
- Keep pure computation isolated from I/O (`run_pipeline` in `backend/services/map_pipeline/pipeline.py` is computation-only; DB work is in `backend/services/map_pipeline/data_fetcher.py` and `backend/services/map_pipeline/coord_writer.py`).

**Parameters:**
- Use typed structured parameters over untyped blobs in backend (`raw_counts: dict[tuple[str, str], dict[str, int]]` in `backend/services/map_pipeline/interaction.py`).
- In Vue components, pass a single object prop and derive view state with refs/computed (`post` prop in `frontend/src/components/Post.vue`).

**Return Values:**
- Return explicit JSON/dict shapes from routes/services (`{"detail": ...}` in `backend/routes/profile.py`, `{"matches": ...}` in `backend/routes/match.py`).
- Return arrays/objects with stable keys for UI rendering (`translated_results` entries with `user_id`, `x`, `y`, `tier` in `backend/services/map_pipeline/pipeline.py`).

## Module Design

**Exports:**
- Use one `APIRouter` per backend domain file (`backend/routes/profile.py`, `backend/routes/interactions.py`, `backend/routes/map.py`, `backend/routes/match.py`).
- Keep module public API minimal and explicit (single entry `run_pipeline_for_user` in `backend/services/map_pipeline/__init__.py`).

**Barrel Files:**
- Present in backend map pipeline package (`backend/services/map_pipeline/__init__.py`) to compose fetch/compute/write pipeline.
- Not used in frontend; import components/utilities directly from file paths (`frontend/src/views/Home.vue`, `frontend/src/main.js`).

---

*Convention analysis: 2026-02-26*

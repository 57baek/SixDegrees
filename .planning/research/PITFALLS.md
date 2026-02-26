# Pitfalls Research

**Domain:** milestone v2.0 global coordinate map engine migration (backend-only)
**Researched:** 2026-02-26
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Mixed Semantics in `map_coordinates` During Cutover

**What goes wrong:**
Old per-viewer rows and new global rows coexist, so read paths return duplicate/wrong nodes, row count explodes, and compatibility endpoints become nondeterministic.

**Why it happens:**
Teams add new columns but do not hard-reset old row semantics or keep transitional SQL/RPC logic that still assumes `center_user_id`/`other_user_id` style data.

**How to avoid:**
Treat V2-02 as a semantic reset: archive old rows, enforce one-row-per-user contract, and switch all map read/write RPCs atomically to global semantics.

**Warning signs:**
- `map_coordinates` row count is far above active user count
- Any runtime query still references per-view columns/flags
- Same user appears multiple times with conflicting current coordinates

**Phase to address:**
V2-02 (DB Migration - Global Coordinates)

**Acceptance checks:**
- DB check: `count(map_coordinates)` is within a tight bound of `count(profiles)`
- Constraint check: one coordinate row per `user_id` is enforced
- Contract test: map read path returns one coordinate per user source row

---

### Pitfall 2: Hidden `user_profiles` Dependency in Runtime Path

**What goes wrong:**
Global compute or API path still calls SQL objects referencing `user_profiles`, causing production failures only in certain environments.

**Why it happens:**
Naming drift already exists in the repo; SQL scripts, RPCs, and docs are partially split between `profiles` and `user_profiles`.

**How to avoid:**
Run dependency inventory before migration, then enforce a hard rule: runtime V2 paths may only read/write canonical `profiles` references.

**Warning signs:**
- Grep finds `user_profiles` in active SQL/RPC files used by map runtime
- Staging works only with legacy compatibility views
- FK errors mention missing `user_profiles` keys during map jobs

**Phase to address:**
V2-01 (Context + Inventory Lock), V2-03 (Interaction FK Realignment), V2-07 (Legacy Cleanup)

**Acceptance checks:**
- Static scan: zero `user_profiles` references in runtime map code path
- FK audit: `interactions` points to `profiles.id` only
- Integration run: global job + map API succeed without legacy shims

---

### Pitfall 3: Reintroducing O(N^2) Compute via Precomputed Distance Matrices

**What goes wrong:**
Pipeline stalls or crashes as users grow because full pairwise matrices are rebuilt in memory; daily job misses window.

**Why it happens:**
Legacy pipeline patterns are familiar, and `metric='precomputed'` workflows are easy to copy even though they require full pairwise distance input.

**How to avoid:**
Use vector-input manifold embedding (UMAP on profile features) plus sparse interaction refinement; ban full NxN matrix construction in production pipeline.

**Warning signs:**
- Profiling shows memory/time growth near quadratic with user count
- Batch job time rises superlinearly after moderate data growth
- Code introduces all-pairs loops as required preprocessing

**Phase to address:**
V2-04 (Global Embedding Engine)

**Acceptance checks:**
- Performance benchmark at representative N shows no NxN materialization
- Code review gate: no full pairwise matrix object in hot path
- Daily recompute completes within agreed SLA window

---

### Pitfall 4: Coordinate Jitter Breaking User Trust

**What goes wrong:**
Users appear to jump unpredictably between daily runs, making map feel random/unreliable even if algorithm is technically valid.

**Why it happens:**
Unconstrained refinement updates and stochastic embedding variance are not bounded; no continuity guardrails are enforced.

**How to avoid:**
Clamp per-run movement, store `prev_x/prev_y`, and enforce drift thresholds as release gates before writing final coordinates.

**Warning signs:**
- High day-over-day displacement percentile for unchanged users
- Cluster structures rotate/flip dramatically between runs
- QA reports "map feels shuffled" despite stable inputs

**Phase to address:**
V2-04 (Global Embedding Engine)

**Acceptance checks:**
- Stability test: p95 coordinate movement stays under configured threshold
- Determinism test: fixed seed/input yields bounded variance
- Regression dashboard tracks displacement and flags spikes automatically

---

### Pitfall 5: Mutual-Friend Filter Drift from Product Rule

**What goes wrong:**
Ego maps include non-mutual or asymmetric friend entries, violating locked visibility policy and confusing users.

**Why it happens:**
Developers implement "friend in A.friends" only, forgetting reciprocal condition (`A in B.friends`) or null/array edge cases.

**How to avoid:**
Implement a single canonical mutuality resolver used by all map endpoints; include asymmetric, missing-profile, and self-edge tests.

**Warning signs:**
- Viewer sees someone who has not reciprocated friendship
- Different endpoints return different friend sets for same viewer
- Empty/partial friend arrays cause inconsistent map counts

**Phase to address:**
V2-05 (Ego Extraction + Compatibility API)

**Acceptance checks:**
- Contract test matrix for symmetric/asymmetric/empty arrays passes
- Route parity test: compatibility endpoint and canonical service return identical node IDs
- Security test: no non-mutual node appears unless marked suggestion

---

### Pitfall 6: Origin Translation Inconsistency (Viewer Not Fixed at 0,0)

**What goes wrong:**
Frontend receives translated coordinates with viewer offset drift, causing broken map centering and subtle UI regressions without frontend code changes.

**Why it happens:**
Translation is duplicated across handlers or applied before selecting viewer row; float precision and missing-viewer handling are inconsistent.

**How to avoid:**
Centralize translation logic in one service, always resolve viewer global coordinate first, and fail fast if viewer coordinate missing.

**Warning signs:**
- Viewer coordinate not exactly `(0,0)` in API payload
- Same request produces different relative positions across endpoints
- Sparse maps return malformed center node behavior

**Phase to address:**
V2-05 (Ego Extraction + Compatibility API)

**Acceptance checks:**
- API invariant test: viewer node is exactly `(0,0)`
- Snapshot tests: relative distances remain unchanged after translation
- Error-path test: missing viewer coordinate returns intentional status, not silent fallback

---

### Pitfall 7: Suggestions Path Becomes Data-Leak Side Channel

**What goes wrong:**
Suggestion fallback reveals users outside allowed visibility intent, or returns unbounded profile details for non-friends.

**Why it happens:**
Fallback is implemented as nearest-neighbor over full user set without strict payload minimization and explicit `is_suggestion` semantics.

**How to avoid:**
Define strict suggestion contract: bounded top-N, minimal safe fields, explicit flagging, and no privileged attributes beyond existing frontend-safe payload.

**Warning signs:**
- Suggestion payload contains extra profile internals not present in friend nodes
- Users can enumerate many non-friends by repeated calls
- Suggestion count is unbounded or inconsistent per request

**Phase to address:**
V2-05 (Ego Extraction + Compatibility API)

**Acceptance checks:**
- Contract test: every fallback node has `is_suggestion=true`
- Payload schema test: suggestion fields are allowlisted
- Abuse test: repeated requests cannot page through unrestricted global roster

---

### Pitfall 8: Authorization Gap on Map Read Endpoint

**What goes wrong:**
Authenticated users can fetch another user's personalized payload (`/map/{user_id}` style access), violating privacy expectations.

**Why it happens:**
Route-level JWT check is present, but subject-level authorization (`acting_user == requested_user` or explicit policy) is missing.

**How to avoid:**
Enforce self-access or explicit policy gate on compatibility endpoint, and document this as non-optional for V2 rollout.

**Warning signs:**
- Manual test with user A token can read user B map
- Logs show frequent cross-user map ID requests
- Security review flags endpoint as IDOR-like pattern

**Phase to address:**
V2-05 (Ego Extraction + Compatibility API)

**Acceptance checks:**
- AuthZ tests: cross-user request returns 403/404 by policy
- Positive test: self-request succeeds
- Audit log review confirms denied cross-user attempts are recorded

---

### Pitfall 9: Unsafe SECURITY DEFINER/RLS Configuration in New RPCs

**What goes wrong:**
Privileged functions can be hijacked via `search_path` object shadowing or exposed schema placement, expanding blast radius of a SQL bug.

**Why it happens:**
Teams add fast migration RPCs under pressure and skip secure function hardening (`SET search_path`, schema isolation, least-privilege grants).

**How to avoid:**
For every SECURITY DEFINER function: set explicit `search_path`, keep functions out of exposed schemas, and restrict execute grants.

**Warning signs:**
- SECURITY DEFINER functions defined without `SET search_path`
- Function lives in publicly exposed schema
- Execute privilege left broadly open by default

**Phase to address:**
V2-02 (DB Migration), V2-03 (FK realignment), V2-05 (new ego RPCs if added)

**Acceptance checks:**
- SQL lint/audit confirms explicit `SET search_path` for definer functions
- Permission audit confirms least-privilege `GRANT EXECUTE`
- RLS integration tests verify expected access boundaries with anon/authenticated/service roles

---

### Pitfall 10: Scheduler Duplication and Misfire Storms

**What goes wrong:**
Global compute and cache warm jobs run multiple times, causing repeated writes, race conditions, and inconsistent `version_date` snapshots.

**Why it happens:**
FastAPI deployment with multiple worker processes triggers app startup per worker; APScheduler instances duplicate jobs when not singletons.

**How to avoid:**
Keep single-worker app runtime for in-process scheduler (as already constrained), use stable job IDs, and configure misfire/coalescing behavior explicitly.

**Warning signs:**
- Duplicate scheduler startup logs with same job names
- Multiple coordinate writes for same `version_date`
- Sudden write amplification around restart windows

**Phase to address:**
V2-06 (Timezone Delivery + Cache Warm), plus deployment guard in V2 rollout checklist

**Acceptance checks:**
- Runtime check: exactly one scheduler instance active in production topology
- Restart test: no duplicate jobs after redeploy
- Job metrics: each daily/global and timezone warm job runs once per schedule window

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep compatibility by duplicating map logic in route handlers | Fast delivery | Divergent behavior and translation bugs | Never; use one shared ego extraction service |
| Skip migration audits and "fix prod if broken" | Saves planning time | Runtime outages from hidden legacy dependencies | Never |
| Tune embedding by intuition only | Faster iteration | Unstable maps and trust erosion | Only in offline experimentation, never in write path |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Supabase RPC + RLS | Assuming JWT auth alone enforces row-level access | Validate endpoint authZ and DB policy behavior together with contract tests |
| APScheduler + FastAPI | Running multi-worker app with in-process scheduler | Keep single worker or move scheduler externally before scaling worker count |
| UMAP pipeline | Feeding precomputed full distance matrix for convenience | Use feature vectors + sparse graph refinement to avoid NxN memory |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-user full recompute loops | Batch duration grows with user count and misses window | Single global daily compute + request-time translation | Early (already visible in current architecture) |
| Unindexed friend/suggestion lookups | `/map` latency spikes and DB CPU increases | Add/query-safe indexes for join/filter columns used by ego extraction | Medium scale (thousands of users) |
| Cache warm jobs doing hidden recompute | 7pm jobs cause heavy CPU and write load | Enforce "delivery only" warm jobs and versioned cache payloads | As timezone cohorts grow |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Cross-user map fetch allowed | Privacy breach and user enumeration | Enforce subject authZ at route/service layer and test 403 path |
| SECURITY DEFINER without hardened `search_path` | Privilege abuse via object shadowing | Set `search_path` explicitly and schema-qualify called objects |
| Suggestion payload overexposes profile data | Unintended data disclosure to non-friends | Allowlist minimal fields and cap top-N suggestions |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| High coordinate jitter | "Map feels random" and trust drops | Enforce movement clamps and stability gates before publish |
| Empty map with no guidance | Users think feature is broken | Provide bounded nearest suggestions with explicit labeling |
| Version-incoherent payloads | Map appears to change on refresh unpredictably | Include `version_date`/`computed_at` consistently across responses |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Global coordinates migration:** one-row-per-user invariant enforced in DB, not only in app logic
- [ ] **Ego map endpoint:** viewer is exactly `(0,0)` for every successful response
- [ ] **Mutual-friend rule:** asymmetric friend-array tests pass for all route variants
- [ ] **Scheduler rollout:** single active scheduler instance verified in deployed topology
- [ ] **Security hardening:** SECURITY DEFINER functions have explicit `search_path` and restricted grants
- [ ] **Compatibility window:** no frontend changes required; legacy endpoint contract tests pass

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Mixed map semantics after cutover | HIGH | Freeze writes, snapshot/backup, truncate/restore `map_coordinates` to last valid global version, rerun global compute, re-enable traffic after invariants pass |
| Unauthorized map access discovered | HIGH | Hotfix authZ gate, rotate/review access logs, notify stakeholders per incident policy, add regression test before reopen |
| Duplicate scheduler executions | MEDIUM | Disable redundant workers/jobs, clean duplicate writes for affected `version_date`, add singleton guard and restart with monitored rollout |
| Unstable coordinate run published | MEDIUM | Roll back to prior snapshot (`prev_x/prev_y` + previous version), tighten movement thresholds, rerun pipeline with validated parameters |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Mixed `map_coordinates` semantics | V2-02 | Row-count/invariant checks plus contract tests show one row per user |
| Hidden `user_profiles` dependency | V2-01, V2-03, V2-07 | Static scan + FK audit + successful end-to-end runtime path |
| O(N^2) compute regression | V2-04 | Benchmark and code audit confirm no full pairwise matrix in production path |
| Coordinate jitter | V2-04 | Stability metrics (p95 drift threshold) pass before publish |
| Mutual-friend filter drift | V2-05 | Asymmetry/edge-case tests enforce reciprocal rule |
| Origin translation inconsistency | V2-05 | API invariant test confirms viewer always `(0,0)` |
| Suggestion data leakage | V2-05 | Payload allowlist and bounded top-N abuse tests pass |
| Cross-user map access | V2-05 | AuthZ tests deny non-self access by default |
| SECURITY DEFINER hardening gaps | V2-02/V2-03/V2-05 | SQL security audit validates `search_path` and execute grants |
| Scheduler duplication/misfires | V2-06 | Deployment + restart test confirms single execution per schedule window |

## Sources

- Internal milestone constraints and phase plan: `.planning/PROJECT.md` (HIGH)
- Locked V2 architecture decisions: `.planning/milestones/v2-NOTES.md` (HIGH)
- Existing codebase risk inventory: `.planning/codebase/CONCERNS.md` (HIGH)
- Current testing patterns and coverage gaps: `.planning/codebase/TESTING.md` (HIGH)
- PostgreSQL docs, `CREATE FUNCTION` security-definer hardening (`SET search_path`): https://www.postgresql.org/docs/current/sql-createfunction.html (HIGH)
- Supabase Row Level Security guidance (RLS, service-role, security-definer cautions): https://supabase.com/docs/guides/database/postgres/row-level-security (HIGH)
- UMAP docs (`metric='precomputed'` requires distance matrix input): https://umap-learn.readthedocs.io/en/latest/parameters.html (MEDIUM)
- APScheduler user guide (single scheduler expectation, job store cautions): https://apscheduler.readthedocs.io/en/stable/userguide.html (HIGH)
- FastAPI deployment workers docs (startup runs per worker process): https://fastapi.tiangolo.com/deployment/server-workers/ (HIGH)

---
*Pitfalls research for: v2.0 global coordinate map engine migration*
*Researched: 2026-02-26*

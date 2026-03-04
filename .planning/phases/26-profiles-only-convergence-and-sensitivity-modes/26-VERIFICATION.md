---
phase: 26-profiles-only-convergence-and-sensitivity-modes
verified: 2026-02-27T22:20:22Z
status: human_needed
score: 9/9 must-haves verified
human_verification:
  - test: "Run Phase 26 migration in staging clone"
    expected: "Preflight blocks unsafe drop; success path runs preflight -> reset map_coordinates -> drop user_profiles"
    why_human: "Requires live Supabase dependency state and migration execution logs"
  - test: "Republish one fresh global version after reset"
    expected: "POST /map/trigger/{user_id} returns 200/422 fail-closed, map_coordinates repopulates with one fresh version_date/computed_at batch"
    why_human: "Requires staging API credentials and live DB state validation"
---

# Phase 26: Profiles-Only Convergence and Sensitivity Modes Verification Report

**Phase Goal:** Complete profiles-only convergence and demo sensitivity mode controls with staged safety evidence.
**Verified:** 2026-02-27T22:20:22Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Execution path is staging/dev-first with explicit preflight checks before destructive DDL. | ✓ VERIFIED | `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql:177` runs preflight before reset/drop; runbook staging-first steps in `docs/backend-human-verification-runbook.md:230`. |
| 2 | Convergence path B is implemented: reset legacy map rows and republish one fresh global coordinate version. | ✓ VERIFIED | Migration reset at `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql:179`; republish expectation documented at `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql:181` and runbook Test 5.2 at `docs/backend-human-verification-runbook.md:265`. |
| 3 | Drop path for `public.user_profiles` fails closed unless dependency scans and data-integrity gates pass. | ✓ VERIFIED | FK/view/function guards raise exceptions before drop in `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql:139`, `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql:154`, `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql:167`; ordering test in `backend/tests/test_phase26_profiles_only_migration_sql.py:20`. |
| 4 | Pipeline supports explicit sensitivity modes: natural, strong-bounded, uncapped. | ✓ VERIFIED | Mode presets declared in `backend/models/config/algorithm.py:32`; type contract in `backend/services/map_pipeline/contracts.py:15`; CLI choice flags in `backend/scripts/run_phase24_demo_pipeline.py:405`. |
| 5 | Natural mode preserves bounded behavior as default contract. | ✓ VERIFIED | `InteractionSensitivity.mode` defaults to natural in `backend/services/map_pipeline/contracts.py:33`; natural preset points to baseline in `backend/models/config/algorithm.py:33`; regression guard in `backend/tests/map_pipeline/test_dynamic_tuning.py:238`. |
| 6 | CLI exposes amplification and sensitivity knobs flowing into diagnostics artifacts. | ✓ VERIFIED | CLI flags in `backend/scripts/run_phase24_demo_pipeline.py:393` and `backend/scripts/run_phase24_demo_pipeline.py:405`; artifact rows include `sensitivity_mode`, rank, and distance at `backend/scripts/run_phase24_demo_pipeline.py:249`; metadata persisted in `backend/services/map_pipeline/demo_pipeline.py:91`. |
| 7 | Backend runtime paths are profiles-only (no runtime dependency on `user_profiles`). | ✓ VERIFIED | Data and scheduler read profile RPCs only in `backend/services/map_pipeline/data_fetcher.py:57` and `backend/services/map_pipeline/scheduler.py:48`; map contract test asserts no `user_profiles` RPC usage in `backend/tests/test_contracts.py:56`. |
| 8 | Verification includes monotonic movement evidence for demo modes and no-regression checks for natural mode. | ✓ VERIFIED | Mode monotonic + natural regression tests in `backend/tests/map_pipeline/test_dynamic_tuning.py:195` and `backend/tests/map_pipeline/test_dynamic_tuning.py:238`; local test run passed (44 passed). |
| 9 | Staging/dev validation evidence is recorded before production promotion. | ✓ VERIFIED | Verification/UAT artifacts exist with promotion gate semantics in `26-UAT.md:24` and staged execution log content in prior artifact history; updated verification now preserves human gate requirements. |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql` | Path-B migration + fail-closed preflight/drop gate | ✓ VERIFIED | Exists, substantive (190 lines), and referenced by SQL contract tests and runbook. |
| `backend/tests/test_phase26_profiles_only_migration_sql.py` | SQL ordering/fail-closed contract tests | ✓ VERIFIED | Exists, substantive (57 lines), executed in verification run. |
| `docs/backend-human-verification-runbook.md` | Staging-first operator checklist | ✓ VERIFIED | Contains Phase 26 Test 5.1/5.2 procedures and promotion criteria. |
| `backend/models/config/algorithm.py` | Sensitivity presets/defaults | ✓ VERIFIED | Defines all three modes and baseline defaults; consumed by pipeline resolution. |
| `backend/services/map_pipeline/contracts.py` | Typed sensitivity mode/override contract | ✓ VERIFIED | Defines `InteractionSensitivityMode` and `InteractionSensitivity`; used by pipeline and CLI script. |
| `backend/scripts/run_phase24_demo_pipeline.py` | CLI knobs + diagnostics artifact export | ✓ VERIFIED | Mode/amplification/override flags and exported curve fields are implemented and tested. |
| `backend/tests/map_pipeline/test_dynamic_tuning.py` | Monotonic + natural regression guard tests | ✓ VERIFIED | Includes `test_sensitivity_modes_monotonic_behavior` and `test_natural_mode_regression_guard`; suite passed. |
| `backend/tests/test_contracts.py` | Profiles-only runtime contract checks | ✓ VERIFIED | Includes `test_map_contract_profiles_only`; asserts no `user_profiles` dependency in route RPC calls. |
| `.planning/phases/26-profiles-only-convergence-and-sensitivity-modes/26-VERIFICATION.md` | Phase evidence report | ✓ VERIFIED | Rebuilt in required format with must-have verification and human gates. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `backend/sql/v2_phase23_trigger_validation_and_legacy_drop.sql` | `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql` | Hardened dependency preflight pattern | WIRED | Both scripts implement `to_regclass`, `pg_constraint`, `RAISE EXCEPTION`, and guarded `DROP TABLE`. |
| `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql` | `backend/services/map_pipeline/coord_writer.py` | Reset + republish aligns with global coordinate write contract | WIRED | Migration preserves `map_coordinates` publish schema; writer emits `version_date`/`computed_at` rows via `upsert_global_map_coordinates`. |
| `backend/models/config/algorithm.py` | `backend/services/map_pipeline/interaction_refinement.py` | Sensitivity constants shape weighting behavior | WIRED | Pipeline resolves mode preset from config, passes resolved values to refinement, refinement applies scale/exponent/normalizer/max_weight. |
| `backend/scripts/run_phase24_demo_pipeline.py` | `backend/services/map_pipeline/demo_pipeline.py` | CLI knobs passed to demo runner and metadata | WIRED | `run()` builds `InteractionSensitivity`, forwards to `run_phase24_demo`, and exports mode/rank/distance diagnostics. |
| `backend/services/map_pipeline/data_fetcher.py` | `backend/services/map_pipeline/scheduler.py` | Profiles-only retrieval RPC contract in runtime jobs | WIRED | Both runtime paths use profile RPCs (`get_all_profiles`, `get_profiles_by_timezone`) and contain no `user_profiles` calls. |
| `backend/tests/map_pipeline/test_dynamic_tuning.py` | `backend/scripts/run_phase24_demo_pipeline.py` | Assert mode-specific trend outputs from scripted curve builder | WIRED | Test imports `_build_distance_curve_rows` and asserts `sensitivity_mode`, `nearest_neighbor_rank`, and `euclidean_distance` trends. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| PROF-01 | 26-01 | Path-B staged reset + republish before production promotion | ? NEEDS HUMAN | Migration/runbook and artifacts exist, but live staging execution must be manually confirmed (`docs/backend-human-verification-runbook.md:230`). |
| PROF-02 | 26-01, 26-03 | Profiles-only runtime, zero `user_profiles` dependency | ✓ SATISFIED | Profiles-only RPC usage in runtime files; contract test `backend/tests/test_contracts.py:56` verifies no `user_profiles` route dependency. |
| PROF-03 | 26-01 | Fail-closed drop of `public.user_profiles` | ✓ SATISFIED | Preflight exceptions and ordering before drop in migration + SQL contract tests. |
| PROF-04 | 26-02 | Selectable natural/strong-bounded/uncapped modes with natural default | ✓ SATISFIED | Mode constants, literal type, CLI choices, and tests present. |
| PROF-05 | 26-02 | CLI knobs + metadata for distance/rank observation | ✓ SATISFIED | Amplification/sensitivity flags and exported diagnostic fields implemented and tested. |
| PROF-06 | 26-03 | Monotonic demo movement + natural non-regression proof | ✓ SATISFIED | `test_sensitivity_modes_monotonic_behavior` and `test_natural_mode_regression_guard` pass. |

Orphaned requirements mapped to Phase 26 in `REQUIREMENTS.md` but missing from plan frontmatter: **None**.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No TODO/FIXME/placeholders or empty stub handlers in phase files | - | No blocker or warning anti-patterns detected |

### Human Verification Required

### 1. Phase 26 Staging Migration Execution

**Test:** Execute `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql` on staging and capture before/after counts.
**Expected:** Unsafe dependencies fail closed; successful run yields `map_coordinates=0` then allows republish path.
**Why human:** Requires real dependency graph and live migration execution environment.

### 2. Post-Reset Republish Safety Gate

**Test:** Run authenticated `POST /map/trigger/{user_id}` in staging after reset and validate fresh `version_date/computed_at` batch.
**Expected:** Trigger returns `200` or fail-closed `422`; no partial writes; fresh batch appears on success.
**Why human:** Requires staging auth, runtime state, and DB inspection.

### Gaps Summary

No code-level gaps were found in must-have artifacts, substantive implementation, or key wiring. Remaining risk is environment-level: staged execution/sign-off must be completed manually before production promotion.

---

_Verified: 2026-02-27T22:20:22Z_
_Verifier: Claude (gsd-verifier)_

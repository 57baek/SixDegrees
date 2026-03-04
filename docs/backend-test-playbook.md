# Backend Test Playbook

Last updated: 2026-02-27

Use this playbook for repeatable backend validation in local/staging.

## 1) Setup

```bash
cd backend
source venv/bin/activate
```

## 2) Fast sanity suite (recommended first)

```bash
./venv/bin/python -m pytest -q tests/test_contracts.py tests/test_profile.py
```

What this covers:

- endpoint status/shape contracts
- auth guard behavior
- profile update/read baseline

## 3) Phase-focused automated suites

### Phase 21 (compute + publish validation)

```bash
./venv/bin/python -m pytest -q \
  tests/map_pipeline/test_sparse_embedding.py \
  tests/map_pipeline/test_interaction_refinement.py \
  tests/map_pipeline/test_stability.py \
  tests/map_pipeline/test_publish_validation.py
```

### Phase 22 (ego map contract)

```bash
./venv/bin/python -m pytest -q \
  tests/test_phase22_ego_profile_projection_sql.py \
  tests/map_pipeline/test_ego_map.py \
  tests/test_contracts.py
```

### Phase 23 (scheduler + warm cache + SQL guards)

```bash
./venv/bin/python -m pytest -q \
  tests/map_pipeline/test_scheduler.py \
  tests/map_pipeline/test_warm_cache.py \
  tests/test_phase23_warm_cache_sql.py \
  tests/test_phase23_trigger_and_legacy_drop_sql.py
```

### Phase 20 targeted regression checks

```bash
./venv/bin/python -m pytest -q \
  tests/test_phase20_interactions_integrity_sql.py \
  tests/map_pipeline/test_coord_writer_global_contract.py \
  -k "not run_pipeline_for_user_passes_global_write_signature"
```

Note:

- The deselected test is environment-sensitive if live Supabase RPCs are not present.

## 4) Full backend suite

```bash
./venv/bin/python -m pytest -q
```

If one failure appears in `test_coord_writer_global_contract.py` about missing RPCs in schema cache:

- This usually indicates local/staging DB does not yet include required migration functions.
- Check these RPCs exist in Supabase schema cache:
  - `get_global_map_coordinates`
  - `record_compute_run_diagnostics`

## 5) Live endpoint smoke tests (manual)

Keep API running:

```bash
uvicorn app:app --reload
```

In another terminal:

```bash
API="http://127.0.0.1:8000"
SELF_USER_ID="<self_uuid>"
OTHER_USER_ID="<other_uuid>"
JWT_SELF="<jwt>"

curl -i "$API/map/$SELF_USER_ID" -H "Authorization: Bearer $JWT_SELF"
curl -i "$API/map/$OTHER_USER_ID" -H "Authorization: Bearer $JWT_SELF"
curl -i -X POST "$API/map/trigger/$SELF_USER_ID" -H "Authorization: Bearer $JWT_SELF"
```

Expected:

- self map: `200`
- cross-user map: `403`
- self trigger: `200` or `422` (never `500`)

## 6) Deferred human checks

For intentionally deferred environment checks, see:

- `docs/milestone-closeout-deferred-verification.md`
- `docs/backend-human-verification-runbook.md`

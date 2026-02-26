# Testing Patterns

**Analysis Date:** 2026-02-26

## Test Framework

**Runner:**
- `pytest` (declared in `backend/requirements.txt` as `pytest>=8.0`).
- Config: Not detected (`backend/pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg` are absent).

**Assertion Library:**
- Native `assert` + `pytest` helpers (`pytest.raises`, `pytest.approx`) in `backend/tests/map_pipeline/test_pipeline.py` and `backend/tests/map_pipeline/test_tsne_projector.py`.
- NumPy assertions for matrix behavior (`np.testing.assert_allclose`, `assert_array_equal`) in `backend/tests/map_pipeline/test_scoring.py` and `backend/tests/map_pipeline/test_interaction.py`.

**Run Commands:**
```bash
cd backend && pytest              # Run all backend tests
cd backend && pytest -q           # Quiet mode
cd backend && pytest -x           # Stop on first failure
```

## Test File Organization

**Location:**
- Backend tests live under `backend/tests/`.
- API/contract tests are top-level (`backend/tests/test_profile.py`, `backend/tests/test_contracts.py`).
- Algorithm tests are grouped by subsystem under `backend/tests/map_pipeline/`.
- Frontend tests are not present (`frontend/` has no `*.test.*` or `*.spec.*`).

**Naming:**
- Use `test_*.py` files and `test_*` functions (for example `backend/tests/map_pipeline/test_origin_translator.py`).

**Structure:**
```
backend/tests/
backend/tests/test_profile.py
backend/tests/test_contracts.py
backend/tests/conftest.py
backend/tests/map_pipeline/test_pipeline.py
backend/tests/map_pipeline/test_interaction.py
backend/tests/map_pipeline/test_scoring.py
backend/tests/map_pipeline/test_tsne_projector.py
backend/tests/map_pipeline/test_origin_translator.py
```

## Test Structure

**Suite Organization:**
```python
def test_get_profile_authenticated(client):
    response = client.get("/profile")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data

def test_get_profile_no_jwt(client_no_auth):
    response = client_no_auth.get("/profile")
    assert response.status_code == 401
```
Source: `backend/tests/test_profile.py`

**Patterns:**
- Setup pattern: shared fixtures in `backend/tests/conftest.py` provide `client`, `client_no_auth`, and `mock_sb`.
- Teardown pattern: fixture context managers and `app.dependency_overrides.clear()` guarantee reset in `backend/tests/conftest.py`.
- Assertion pattern: validate status code first, then key payload shape/fields (`backend/tests/test_contracts.py`).

## Mocking

**Framework:** `unittest.mock` (`MagicMock`, `patch`) + pytest fixtures.

**Patterns:**
```python
@pytest.fixture
def client(mock_sb):
    with patch("services.map_pipeline.scheduler.setup_scheduler", return_value=MagicMock()):
        app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID
        with TestClient(app, raise_server_exceptions=False) as tc:
            yield tc
        app.dependency_overrides.clear()
```
Source: `backend/tests/conftest.py`

```python
mock_sb.rpc.side_effect = None
mock_sb.rpc.return_value.execute.return_value.data = [_ACTING_USER_ROW, _OTHER_USER_ROW]
response = client.get("/match")
assert response.status_code == 200
```
Source: `backend/tests/test_contracts.py`

**What to Mock:**
- Mock Supabase client calls and RPC chain responses (`backend/tests/conftest.py`).
- Mock scheduler startup in app lifespan to keep tests deterministic (`backend/tests/conftest.py`).
- Override auth dependency for authenticated endpoint coverage (`backend/tests/conftest.py`).

**What NOT to Mock:**
- Do not mock pure algorithm functions when verifying numerical invariants; call real implementations (`backend/tests/map_pipeline/test_scoring.py`, `backend/tests/map_pipeline/test_interaction.py`).

## Fixtures and Factories

**Test Data:**
```python
def make_user(uid: str, interests: list[str], age: int = 25) -> UserProfile:
    return UserProfile(
        id=uid,
        nickname=uid,
        interests=interests,
        languages=["English"],
        city="San Francisco",
        state="CA",
        education="Computer Science",
        occupation="Engineer",
        industry="Technology",
        age=age,
        timezone="UTC",
    )
```
Source: `backend/tests/map_pipeline/test_pipeline.py`

**Location:**
- Global/shared fixtures live in `backend/tests/conftest.py`.
- Per-module factory helpers (`make_users`, `make_distance_matrix`, `canonical_pair`) live alongside relevant tests in `backend/tests/map_pipeline/`.

## Coverage

**Requirements:** None enforced (no coverage config/threshold files detected).

**View Coverage:**
```bash
Not configured in repository (no pytest-cov command or config detected).
```

## Test Types

**Unit Tests:**
- Pure function and matrix-property tests for map pipeline internals (`backend/tests/map_pipeline/test_interaction.py`, `backend/tests/map_pipeline/test_scoring.py`, `backend/tests/map_pipeline/test_tsne_projector.py`, `backend/tests/map_pipeline/test_origin_translator.py`).

**Integration Tests:**
- HTTP contract tests with FastAPI `TestClient` plus mocked Supabase (`backend/tests/test_contracts.py`, `backend/tests/test_profile.py`).

**E2E Tests:**
- Not used (no browser/integration framework in `frontend/package.json`, no e2e test directories detected).

## Common Patterns

**Async Testing:**
```python
response = client.post("/map/trigger/test-user-uuid")
assert response.status_code in (200, 422)
assert response.status_code != 500
```
Pattern: async FastAPI routes are tested synchronously through `TestClient` in `backend/tests/test_contracts.py`.

**Error Testing:**
```python
with pytest.raises(ValueError, match="10"):
    run_pipeline(users, {}, requesting_user_id="u00")

response = client_no_auth.get("/profile")
assert response.status_code == 401
```
Sources: `backend/tests/map_pipeline/test_pipeline.py`, `backend/tests/test_profile.py`

---

*Testing analysis: 2026-02-26*

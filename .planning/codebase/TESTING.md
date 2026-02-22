# Testing Patterns

**Analysis Date:** 2026-02-22

## Test Framework

**Status:** Not configured

**Current State:**
- No test framework installed in either frontend or backend
- No test files present in codebase
- No testing configuration files (Jest, Vitest, Pytest, etc.)
- No test scripts in `package.json`

**Backend (Python):**
- Frameworks available in ecosystem: `pytest`, `unittest`
- Not integrated; no requirements in `backend/requirements.txt`
- FastAPI supports testing via `TestClient` from `fastapi.testclient`

**Frontend (Vue 3):**
- Frameworks available in ecosystem: `Vitest`, `Jest` + `@vue/test-utils`
- Not integrated; no dev dependencies in `frontend/package.json`

## Recommendation for Implementation

**Backend Testing Stack:**
- Framework: `pytest` (lightweight, fixture-based, matches Python conventions)
- Fixtures: Use `conftest.py` for shared test data and Supabase mocks
- Run command: `pytest` or `pytest -v --cov`

**Frontend Testing Stack:**
- Framework: `Vitest` (Vite-native, fast, matches existing build setup)
- Component testing: `@vue/test-utils` for Vue 3 components
- Run commands: `npm run test`, `npm run test:watch`, `npm run test:coverage`

## Test File Organization

**Backend (Proposed):**
- Location: Co-located with source modules in `tests/` directory or alongside source
- Naming: `test_<module>.py` (e.g., `tests/test_similarity.py`, `tests/test_match_routes.py`)
- Structure: Test directory mirrors `backend/` structure
  ```
  backend/
  ├── app.py
  ├── config/
  │   ├── supabase.py
  ├── models/
  ├── routes/
  ├── services/
  │   └── matching/
  └── tests/
      ├── test_app.py
      ├── conftest.py
      ├── config/
      │   └── test_supabase.py
      ├── services/
      │   └── matching/
      │       ├── test_similarity.py
      │       ├── test_scoring.py
      │       ├── test_clustering.py
      │       └── test_visualization.py
      └── routes/
          └── test_match.py
  ```

**Frontend (Proposed):**
- Location: Co-located with components in same directory or `tests/` parallel structure
- Naming: `<Component>.test.js` or `<Component>.spec.js`
- Structure:
  ```
  frontend/src/
  ├── components/
  │   ├── Post.vue
  │   ├── Post.test.js
  │   ├── CreatePost.vue
  │   └── CreatePost.test.js
  ├── views/
  │   ├── Home.vue
  │   ├── Home.test.js
  │   ├── Login.vue
  │   └── Login.test.js
  └── __tests__/
      ├── lib/
      │   └── supabase.test.js
      └── router/
          └── index.test.js
  ```

## Test Structure Pattern (Proposed)

**Backend Pattern (Pytest):**
```python
# tests/services/matching/test_similarity.py
import pytest
from backend.services.matching.similarity import (
    jaccard,
    tiered_location,
    tiered_categorical,
)

class TestSimilarity:
    """Test similarity calculation functions"""

    def test_jaccard_identical_lists(self):
        """Jaccard of identical lists should be 1.0"""
        result = jaccard(['a', 'b'], ['a', 'b'])
        assert result == 1.0

    def test_jaccard_disjoint_sets(self):
        """Jaccard of disjoint sets should be 0.0"""
        result = jaccard(['a', 'b'], ['c', 'd'])
        assert result == 0.0

    def test_tiered_location_same_city(self):
        """Same city location should return 1.0"""
        result = tiered_location('San Francisco', 'CA', 'San Francisco', 'CA')
        assert result == 1.0

    def test_tiered_location_same_state(self):
        """Same state, different city should return 0.5"""
        result = tiered_location('San Francisco', 'CA', 'Los Angeles', 'CA')
        assert result == 0.5
```

**Frontend Pattern (Vitest + @vue/test-utils):**
```javascript
// src/components/__tests__/Post.test.js
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import Post from '../Post.vue'

describe('Post Component', () => {
  let wrapper
  const mockPost = {
    id: 1,
    user_id: 'user-123',
    content: 'Test post content',
    tier: 'inner_circle',
    created_at: new Date().toISOString(),
    profiles: { username: 'TestUser' },
    like_count: 5,
    comment_count: 2
  }

  beforeEach(() => {
    wrapper = mount(Post, {
      props: {
        post: mockPost
      }
    })
  })

  it('renders post content', () => {
    expect(wrapper.text()).toContain('Test post content')
  })

  it('displays username from post data', () => {
    expect(wrapper.text()).toContain('TestUser')
  })

  it('shows like count', () => {
    expect(wrapper.text()).toContain('5')
  })

  it('emits like event on like button click', async () => {
    await wrapper.find('.action-btn').trigger('click')
    expect(wrapper.emitted()).toBeDefined()
  })
})
```

## Mocking Strategy

**Backend (Pytest):**
- Framework: `pytest` with built-in fixtures and `unittest.mock`
- Mock Supabase client in `conftest.py`:

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, patch
from backend.models.user import UserProfile

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing"""
    return MagicMock()

@pytest.fixture
def sample_users():
    """Sample user data for testing"""
    return [
        UserProfile(
            id='user-1',
            interests=['reading', 'coding'],
            languages=['english'],
            city='San Francisco',
            state='CA',
            education_level='bachelors',
            field_of_study='Computer Science',
            occupation='Engineer',
            industry='Technology',
            age=25
        ),
        UserProfile(
            id='user-2',
            interests=['reading', 'gaming'],
            languages=['english', 'spanish'],
            city='Los Angeles',
            state='CA',
            education_level='masters',
            field_of_study='Computer Science',
            occupation='Scientist',
            industry='Technology',
            age=28
        )
    ]

@pytest.fixture
def mock_get_supabase_client(mock_supabase):
    """Mock the get_supabase_client function"""
    with patch('backend.config.supabase.get_supabase_client', return_value=mock_supabase):
        yield mock_supabase
```

**Frontend (Vitest):**
- Mock Supabase client in test utilities:

```javascript
// src/__tests__/mocks/supabase.js
import { vi } from 'vitest'

export const mockSupabase = {
  auth: {
    signInWithPassword: vi.fn().mockResolvedValue({
      data: { session: { access_token: 'test-token' } },
      error: null
    }),
    signUp: vi.fn().mockResolvedValue({
      data: { user: { id: 'user-123' } },
      error: null
    }),
    signOut: vi.fn().mockResolvedValue({ error: null }),
    getUser: vi.fn().mockResolvedValue({
      data: { user: { id: 'user-123' } },
      error: null
    }),
    getSession: vi.fn().mockResolvedValue({
      data: { session: { access_token: 'test-token' } },
      error: null
    })
  },
  from: vi.fn().mockReturnValue({
    select: vi.fn().mockReturnThis(),
    insert: vi.fn().mockReturnThis(),
    delete: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    execute: vi.fn().mockResolvedValue({ data: [], error: null }),
    then: vi.fn()
  })
}

export const mockSupabaseModule = {
  supabase: mockSupabase,
  isAuthenticated: vi.fn().mockResolvedValue(true),
  getCurrentUser: vi.fn().mockResolvedValue({ id: 'user-123' }),
  signOut: vi.fn().mockResolvedValue(undefined)
}
```

**What to Mock:**
- External API calls (Supabase auth, database queries)
- Date/time functions in tests requiring deterministic behavior
- Network requests (for component integration tests)

**What NOT to Mock:**
- Pure utility functions (similarity calculations, Jaccard, etc.)
- Vue built-in functions (ref, computed, onMounted)
- Router and navigation
- Component internal state (test through props and emitted events)

## Coverage Targets (Proposed)

**Backend:**
- Statement coverage: ≥ 80% for core algorithms
- Branch coverage: ≥ 70% for matching pipeline
- Target files: `services/matching/*`, `models/user.py`, `routes/match.py`
- Lower priority: `config/supabase.py`, `app.py` (thin wrappers)

**Frontend:**
- Statement coverage: ≥ 60% for components
- Branch coverage: ≥ 50% for conditional rendering
- Target files: `components/*.vue`, `lib/supabase.js`, `router/index.js`
- Lower priority: views (depend heavily on Supabase real-time behavior)

**Run Coverage:**
```bash
# Backend
pytest --cov=backend --cov-report=html

# Frontend
npm run test -- --coverage
```

## Test Types (Proposed)

**Unit Tests:**

*Backend:*
- Test individual similarity functions with known inputs
- Test matrix building with sample data
- Test KNN ranking logic independently
- Validate Pydantic model parsing

Example scope: `test_similarity.py`, `test_scoring.py`, `test_clustering.py`

*Frontend:*
- Test component rendering with props
- Test computed properties with different state
- Test event emission on user interaction
- Test helper functions (formatDate, tierLabel)

Example scope: `Post.test.js`, `CreatePost.test.js`, `supabase.test.js`

**Integration Tests (Proposed):**

*Backend:*
- Test `/match/users/{user_id}/matches` endpoint with mock Supabase data
- Test cache invalidation flow (`/match/invalidate-cache`)
- Test full pipeline: fetch users → build matrix → rank matches
- Mock Supabase responses for realistic data flows

*Frontend:*
- Test Login.vue → Home.vue navigation flow with mocked auth
- Test Post component loading and displaying mocked data
- Test CreatePost emitting event to parent component
- Test router guards with token presence/absence

**E2E Tests:**
- Not currently used; could add with Playwright/Cypress for full user flows
- Lower priority given frontend relies on Supabase directly

## Async Testing Pattern (Proposed)

**Backend (pytest-asyncio):**
```python
import pytest

@pytest.mark.asyncio
async def test_get_matches_async(mock_supabase, sample_users):
    """Test async route handler"""
    # Mock the cache and data
    users, matrix = sample_users, build_distance_matrix(sample_users)

    # Call async function
    result = await get_ranked_matches(
        user_id='user-1',
        users=users,
        distance_matrix=matrix
    )

    assert len(result) > 0
    assert result[0].tier == 1
```

**Frontend (Vitest awaits):**
```javascript
it('handles async login', async () => {
  const wrapper = mount(Login)

  await wrapper.find('input[type="text"]').setValue('test@example.com')
  await wrapper.find('input[type="password"]').setValue('Password123!')
  await wrapper.find('button').trigger('click')

  // Await next tick for promise resolution
  await wrapper.vm.$nextTick()

  // Assert redirected or error shown
  expect(wrapper.emitted()).toBeDefined()
})
```

## Error Testing Pattern (Proposed)

**Backend:**
```python
def test_get_matches_user_not_found(mock_supabase, sample_users):
    """Should raise HTTPException when user not found"""
    with pytest.raises(ValueError, match="User .* not found"):
        get_ranked_matches(
            user_id='nonexistent-user',
            users=sample_users,
            distance_matrix=build_distance_matrix(sample_users)
        )
```

**Frontend:**
```javascript
it('displays error on login failure', async () => {
  mockSupabase.auth.signInWithPassword.mockResolvedValueOnce({
    data: null,
    error: { message: 'Invalid credentials' }
  })

  const wrapper = mount(Login)
  await wrapper.find('form').trigger('submit')
  await wrapper.vm.$nextTick()

  expect(wrapper.text()).toContain('Invalid credentials')
})
```

---

*Testing analysis: 2026-02-22*

# Coding Conventions

**Analysis Date:** 2026-02-22

## Naming Patterns

**Files:**
- Python modules: `snake_case` (e.g., `similarity.py`, `clustering.py`, `supabase.py`)
- Vue components: PascalCase (e.g., `Post.vue`, `CreatePost.vue`, `Home.vue`)
- JavaScript/Vue scripts: camelCase (e.g., `main.js`, `supabase.js`)
- Directories: lowercase kebab-case or snake_case (e.g., `services/matching/`, `config/`, `routes/`)

**Functions:**
- Python: `snake_case` (e.g., `get_ranked_matches()`, `build_similarity_matrix()`, `tiered_location()`)
- JavaScript/Vue: `camelCase` (e.g., `handleLogin()`, `formatDate()`, `toggleComments()`)
- Vue lifecycle and event handlers: camelCase prefixed with handler name (e.g., `handleLike()`, `handlePost()`)

**Variables:**
- Python: `snake_case` (e.g., `user_id`, `distance_matrix`, `max_distance`)
- JavaScript/Vue: `camelCase` (e.g., `selectedTier`, `showComments`, `isLiked`)
- Vue component props: camelCase (e.g., `post`, `user`, `selectedTier`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_WEIGHTS`, `DEFAULT_K1`, `FEATURE_COLS`)

**Types/Classes:**
- Python Pydantic models: PascalCase (e.g., `UserProfile`, `MatchResult`)
- Python dictionaries mapping categories: `UPPER_SNAKE_CASE` (e.g., `FIELD_OF_STUDY_CATEGORIES`, `INDUSTRY_CATEGORIES`)

## Code Style

**Formatting:**
- Frontend: No explicit formatter configured; follows Vue 3 Composition API conventions
- Backend: Python PEP 8 style observed
- Line length: Varies (no strict limit enforced)
- Indentation: 2 spaces (JavaScript/Vue), 4 spaces (Python)

**Linting:**
- Frontend: No ESLint config detected; no strict linting enforced
- Backend: No linter config detected; Python conventions applied manually
- Vue components use `<script setup>` syntax (Vue 3.4+)

## Import Organization

**Python Order:**
1. Standard library imports (e.g., `import os`, `import time`)
2. Third-party imports (e.g., `import numpy as np`, `from fastapi import FastAPI`)
3. Local imports (e.g., `from models.user import UserProfile`)

Example from `backend/routes/match.py`:
```python
import time
from fastapi import APIRouter, HTTPException
from config.supabase import get_supabase_client
from models.user import UserProfile, MatchResult
```

**JavaScript/Vue Order:**
1. Built-in/framework imports (e.g., `import { createApp } from "vue"`)
2. External library imports (e.g., `import { supabase } from "../lib/supabase"`)
3. Local component/lib imports (e.g., `import Post from '../components/Post.vue'`)

Example from `frontend/src/router/index.js`:
```javascript
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
```

**Path Aliases:**
- No path aliases configured; relative paths used throughout (e.g., `../lib/supabase`, `../components/`)

## Error Handling

**Backend (Python/FastAPI):**
- Exceptions raised for errors, caught in route handlers
- HTTP exceptions used for API responses: `HTTPException(status_code=404, detail="...")`
- Try/catch blocks in async functions catch exceptions and propagate to middleware
- Validation errors handled via Pydantic model validation at function entry

Example from `backend/routes/match.py`:
```python
if not any(u.id == user_id for u in users):
    raise HTTPException(status_code=404, detail=f"User {user_id} not found")
```

**Frontend (Vue):**
- Error state stored in `ref()` variable (e.g., `const error = ref('')`)
- Errors caught in try/catch blocks; message assigned to error ref
- Error messages displayed conditionally in template: `<div v-if="error">{{ error }}</div>`
- Fallback values for async operations (e.g., `?.` optional chaining, `|| 'Unknown User'`)

Example from `frontend/src/views/Login.vue`:
```javascript
try {
  const { data, error: supabaseError } = await supabase.auth.signInWithPassword({...})
  if (supabaseError) {
    error.value = supabaseError.message
    return
  }
} catch (err) {
  error.value = "Cannot connect to Supabase"
  console.error(err)
}
```

## Logging

**Framework:** `console` (JavaScript) and `print()`/no logging (Python backend)

**Patterns:**
- Frontend: `console.log()` for debugging, `console.error()` for failures
  - Example: `console.error('Error loading posts:', err)`
  - Condition checks on auth state logged on app init: `console.log("Supabase client initialized:", supabase ? "Connected" : "Failed")`
- Backend: No structured logging library; print statements appear in matching algorithm comments only
  - Errors propagated as exceptions rather than logged

## Comments

**When to Comment:**
- Algorithm logic with non-obvious behavior (e.g., similarity calculations, PCA transformations)
- Complex mathematical operations (e.g., Jaccard similarity, inverse distance age)
- Configuration decisions (e.g., TTL constants, weight assignments)
- TODO items for incomplete features (tracked throughout codebase)

**JSDoc/TSDoc:**
- Minimal usage in JavaScript; comments appear mostly in Python
- Python docstrings used for function documentation

Example from `backend/services/matching/similarity.py`:
```python
def tiered_location(city1: str, state1: str, city2: str, state2: str) -> float:
    """Tiered location similarity.

    Same city  → 1.0
    Same state → 0.5
    Different  → 0.0
    """
```

Example from `frontend/src/components/Post.vue`:
```javascript
/**
 * Formats post timestamp to relative time
 * @param dateString ISO date string
 */
function formatDate(dateString) { ... }
```

## Function Design

**Size:**
- Python: Mix of small utility functions (10–20 lines) and larger algorithmic functions (20–50 lines)
- JavaScript/Vue: Component methods range 20–30 lines; Composition API hooks 5–15 lines

**Parameters:**
- Python: Type hints used throughout (e.g., `def get_ranked_matches(user_id: str, users: list[UserProfile], ...`)
- JavaScript/Vue: No type hints; Vue props use shape validation with `defineProps()` or JSDoc comments

Example from `backend/services/matching/clustering.py`:
```python
def get_ranked_matches(
    user_id: str,
    users: list[UserProfile],
    distance_matrix: np.ndarray,
    k1: int = DEFAULT_K1,
    ...
) -> list[MatchResult]:
```

**Return Values:**
- Python: Explicit type annotations (e.g., `-> list[MatchResult]`, `-> np.ndarray`)
- JavaScript/Vue: Implicit; return types inferred from usage (e.g., `emit('post-created', data[0])`, `return !!session`)
- Pydantic models used for structured returns in FastAPI routes

## Module Design

**Exports:**
- Python: Functions exported from modules directly; no explicit `__all__` lists
  - Modules imported as: `from services.matching.similarity import jaccard, tiered_location`
  - Helper functions prefixed with `_` to indicate private scope (e.g., `_fetch_all_users()`, `_similarity_vector()`)

- JavaScript/Vue: Named exports used
  - Functions/components exported with `export const` or `export default`
  - Example: `export const supabase = createClient(...)`

**Barrel Files:**
- Not used; imports target specific modules directly
- Example: `from services.matching.similarity import ...` rather than `from services.matching import ...`

## Data Structures

**Python:**
- Pydantic `BaseModel` for all data contracts (`UserProfile`, `MatchResult`)
- NumPy arrays for matrix operations (`np.ndarray`)
- Standard Python lists and dicts for intermediate data

**JavaScript/Vue:**
- Vue `ref()` for reactive state
- Plain objects for data shapes (e.g., `{ id, x, y }` for graph coordinates)
- Array methods (`map`, `filter`) over imperative loops
- Destructuring used for extracting nested values (e.g., `const { data: { user } } = await supabase.auth.getUser()`)

## Code Organization Patterns

**Matching Algorithm Pipeline:**
Separation of concerns across files:
- `similarity.py`: Per-field similarity calculations (pure functions)
- `scoring.py`: Matrix building and weighting (pure functions)
- `clustering.py`: KNN ranking and tier assignment (pure functions)
- `visualization.py`: PCA projection (pure functions)
- `routes/match.py`: HTTP endpoints and caching orchestration

Each module operates on immutable data, making testing straightforward.

**Frontend Component Structure:**
- Template: HTML structure with Vue directives
- Script: Vue 3 Composition API with `<script setup>`
- Style: Scoped CSS with dark theme (dark backgrounds, light text)

Example pattern:
```vue
<template>
  <!-- HTML with v-for, v-if, @click handlers -->
</template>

<script setup>
import { ref, computed } from 'vue'
// imports, state, computed, functions
</script>

<style scoped>
/* Scoped styles */
</style>
```

---

*Convention analysis: 2026-02-22*

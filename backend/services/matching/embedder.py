"""Sentence-transformer embedding for profile text fields.

Model lifecycle: lazy-loaded on first call to embed_profiles().
Not thread-safe — safe under single-worker Uvicorn deployment.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

import config.settings as _cfg
from models.user import UserProfile

_model: SentenceTransformer | None = None

# Fallback embedding dimension when the model isn't loaded yet.
# Must match the output dim of EMBEDDING_MODEL (all-MiniLM-L6-v2 → 384).
_FALLBACK_DIM = 384


def _get_model() -> SentenceTransformer:
    """Return the shared model instance, loading it on first call."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_cfg.EMBEDDING_MODEL)
    return _model


def build_profile_text(profile: UserProfile) -> str:
    """Concatenate EMBEDDING_FIELDS values into a single string for embedding.

    Rules (reads EMBEDDING_FIELDS from config at call time — patchable in tests):
      - list[str] fields: space-joined
      - str fields: used as-is
      - None or empty list: skipped (no separator emitted)
    Non-empty parts joined with ". " between them.

    Examples (EMBEDDING_FIELDS = ["interests", "bio"]):
      interests=["hiking", "trail running"], bio="I love the outdoors"
        → "hiking trail running. I love the outdoors"
      interests=["hiking"], bio=None  → "hiking"
      interests=[],         bio="..."  → "I love the outdoors"
      interests=[],         bio=None   → ""
    """
    parts: list[str] = []
    for field in _cfg.EMBEDDING_FIELDS:
        value = getattr(profile, field, None)
        if value is None:
            continue
        if isinstance(value, list):
            text = " ".join(value).strip()
        else:
            text = str(value).strip()
        if text:
            parts.append(text)
    return ". ".join(parts)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, clipped to [0, 1].

    Returns 0.0 if either vector is all-zeros (avoids division-by-zero / nan).
    """
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    raw = float(np.dot(a, b) / (norm_a * norm_b))
    return float(np.clip(raw, 0.0, 1.0))


def embed_profiles(profiles: list[UserProfile]) -> np.ndarray:
    """Batch-encode profiles using EMBEDDING_FIELDS text. Returns shape (N, dim).

    Profiles with empty text receive zero vectors — the model is NOT called
    with empty strings (model output on empty tokens is undefined).
    Precondition: profile IDs in the input list must be unique.
    """
    n = len(profiles)
    texts = [build_profile_text(p) for p in profiles]

    non_empty_indices = [i for i, t in enumerate(texts) if t]
    non_empty_texts = [texts[i] for i in non_empty_indices]

    if non_empty_texts:
        model = _get_model()
        dim = model.get_sentence_embedding_dimension()
        result = np.zeros((n, dim), dtype=np.float32)
        encoded = model.encode(non_empty_texts, convert_to_numpy=True)
        for out_idx, src_idx in enumerate(non_empty_indices):
            result[src_idx] = encoded[out_idx]
        return result
    else:
        # All profiles have empty text — return zero vectors
        # Use 384 as default dim (all-MiniLM-L6-v2) since model isn't loaded yet
        return np.zeros((n, _FALLBACK_DIM), dtype=np.float32)

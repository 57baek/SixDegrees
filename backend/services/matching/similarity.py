# Per-field similarity functions.
# All return a float in [0, 1]. Pure functions — no I/O.

# Category maps for tiered categorical matching.
# Extend these as you add more options to the profile form.

FIELD_OF_STUDY_CATEGORIES: dict[str, str] = {
    # STEM
    "computer science": "stem",
    "software engineering": "stem",
    "electrical engineering": "stem",
    "mechanical engineering": "stem",
    "civil engineering": "stem",
    "biomedical engineering": "stem",
    "mathematics": "stem",
    "statistics": "stem",
    "physics": "stem",
    "chemistry": "stem",
    "biology": "stem",
    "data science": "stem",
    # Business
    "business administration": "business",
    "finance": "business",
    "accounting": "business",
    "economics": "business",
    "marketing": "business",
    "management": "business",
    "entrepreneurship": "business",
    # Humanities
    "history": "humanities",
    "philosophy": "humanities",
    "literature": "humanities",
    "linguistics": "humanities",
    "political science": "humanities",
    "sociology": "humanities",
    "psychology": "humanities",
    # Arts
    "fine arts": "arts",
    "graphic design": "arts",
    "music": "arts",
    "film": "arts",
    "architecture": "arts",
    # Health
    "nursing": "health",
    "medicine": "health",
    "public health": "health",
    "pharmacy": "health",
    "physical therapy": "health",
}

INDUSTRY_CATEGORIES: dict[str, str] = {
    "software": "tech",
    "technology": "tech",
    "hardware": "tech",
    "cybersecurity": "tech",
    "artificial intelligence": "tech",
    "finance": "finance",
    "banking": "finance",
    "investment": "finance",
    "insurance": "finance",
    "accounting": "finance",
    "healthcare": "health",
    "pharmaceuticals": "health",
    "biotechnology": "health",
    "medical devices": "health",
    "education": "education",
    "research": "education",
    "government": "public",
    "nonprofit": "public",
    "law": "public",
    "media": "creative",
    "entertainment": "creative",
    "advertising": "creative",
    "design": "creative",
    "retail": "commerce",
    "e-commerce": "commerce",
    "manufacturing": "industry",
    "construction": "industry",
    "energy": "industry",
    "transportation": "industry",
}


def jaccard(a: list[str], b: list[str]) -> float:
    """Jaccard similarity between two lists treated as sets.

    Used for: interests, languages.
    Returns 0.0 if both sets are empty.
    """
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


def tiered_location(city1: str, state1: str, city2: str, state2: str) -> float:
    """Tiered location similarity.

    Same city  → 1.0
    Same state → 0.5
    Different  → 0.0
    """
    if city1.lower() == city2.lower():
        return 1.0
    if state1.lower() == state2.lower():
        return 0.5
    return 0.0


def tiered_categorical(a: str, b: str, category_map: dict[str, str]) -> float:
    """Tiered categorical similarity using a category map.

    Exact match        → 1.0
    Same category      → 0.5
    Different category → 0.0

    Used for: field_of_study, occupation/industry.
    """
    a_norm, b_norm = a.lower().strip(), b.lower().strip()
    if a_norm == b_norm:
        return 1.0
    cat_a = category_map.get(a_norm)
    cat_b = category_map.get(b_norm)
    if cat_a and cat_b and cat_a == cat_b:
        return 0.5
    return 0.0


def inverse_distance_age(a: int, b: int) -> float:
    """Inverse distance similarity for age.

    Returns 1 / (1 + |a - b|).
    Same age → 1.0, 5 years apart → ~0.17.
    Min-max normalization in scoring.py brings this to a consistent range.
    """
    return 1.0 / (1.0 + abs(a - b))

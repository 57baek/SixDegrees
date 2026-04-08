from unittest.mock import MagicMock, patch

from models.user import UserProfile
from services.map.contracts import PipelineInput
from services.map.fetcher import fetch


PROFILE_ROWS = [
    {
        "id": "user-1",
        "nickname": "Alice",
        "bio": "Hello",
        "age": 28,
        "city": "Austin",
        "state": "TX",
        "education": "BS Computer Science",
        "occupation": "Engineer",
        "industry": "Tech",
        "interests": ["hiking", "music"],
        "languages": ["English"],
        "profile_tier": 2,
        "is_admin": False,
        "avatar_url": None,
    },
    {
        "id": "user-2",
        "nickname": "Bob",
        "bio": None,
        "age": 32,
        "city": "Denver",
        "state": "CO",
        "education": None,
        "occupation": "Designer",
        "industry": "Media",
        "interests": ["gaming"],
        "languages": ["English", "Spanish"],
        "profile_tier": 3,
        "is_admin": False,
        "avatar_url": "https://example.com/bob.png",
    },
]

INTERACTION_ROWS = [
    {"uid_a": "user-1", "uid_b": "user-2", "like_count": 1, "comment_count": 2, "dm_count": 0},
]


def _make_mock_sb() -> MagicMock:
    """Build a MagicMock Supabase client with separate data for profiles vs interactions."""
    mock_sb = MagicMock()

    profiles_chain = MagicMock()
    profiles_chain.select.return_value.execute.return_value.data = PROFILE_ROWS

    interactions_chain = MagicMock()
    interactions_chain.select.return_value.execute.return_value.data = INTERACTION_ROWS

    def table_side_effect(name: str) -> MagicMock:
        if name == "profiles":
            return profiles_chain
        if name == "interactions":
            return interactions_chain
        return MagicMock()

    mock_sb.table.side_effect = table_side_effect
    return mock_sb


def test_fetch_returns_pipeline_input():
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        result = fetch()
    assert isinstance(result, PipelineInput)


def test_fetch_profiles_count():
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        result = fetch()
    assert len(result.profiles) == 2


def test_fetch_profiles_are_user_profile_objects():
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        result = fetch()
    for profile in result.profiles:
        assert isinstance(profile, UserProfile)


def test_fetch_profile_fields():
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        result = fetch()
    alice = result.profiles[0]
    assert alice.id == "user-1"
    assert alice.nickname == "Alice"
    assert alice.age == 28
    assert alice.city == "Austin"
    assert alice.interests == ["hiking", "music"]


def test_fetch_interactions():
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        result = fetch()
    assert result.interactions == INTERACTION_ROWS


def test_fetch_user_ids_property():
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        result = fetch()
    assert result.user_ids == ["user-1", "user-2"]


def test_fetch_extra_db_columns_ignored():
    """UserProfile has extra='ignore' — unknown columns from DB are silently dropped."""
    rows_with_extra = [
        {**PROFILE_ROWS[0], "unknown_column": "some_value", "another_extra": 99},
    ]
    mock_sb = MagicMock()
    profiles_chain = MagicMock()
    profiles_chain.select.return_value.execute.return_value.data = rows_with_extra
    interactions_chain = MagicMock()
    interactions_chain.select.return_value.execute.return_value.data = []

    def table_side_effect(name: str) -> MagicMock:
        return profiles_chain if name == "profiles" else interactions_chain

    mock_sb.table.side_effect = table_side_effect

    with patch("config.settings._client", mock_sb):
        result = fetch()

    assert len(result.profiles) == 1
    assert not hasattr(result.profiles[0], "unknown_column")


def test_fetch_empty_tables():
    mock_sb = MagicMock()
    chain = MagicMock()
    chain.select.return_value.execute.return_value.data = []
    mock_sb.table.return_value = chain

    with patch("config.settings._client", mock_sb):
        result = fetch()

    assert result.profiles == []
    assert result.interactions == []
    assert result.user_ids == []

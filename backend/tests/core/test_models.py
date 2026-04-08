from models.user import UserProfile

def test_userprofile_fields():
    u = UserProfile(id="abc", nickname="alice")
    assert u.bio is None
    assert u.avatar_url is None
    assert u.interests == []
    assert u.languages == []
    assert u.profile_tier == 6
    assert u.is_admin is False

def test_userprofile_ignores_timezone():
    # timezone field must be silently ignored
    u = UserProfile(id="abc", nickname="alice", timezone="UTC")
    assert not hasattr(u, "timezone")

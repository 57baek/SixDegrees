"""Tests for services/map/lock.py file-based dedup lock."""
import time

def test_acquire_lock_returns_false_when_held(tmp_path, monkeypatch):
    """acquire_lock returns False when lock file exists and is fresh."""
    from services.map import lock as lock_mod
    lock_file = str(tmp_path / "compute.lock")
    monkeypatch.setattr(lock_mod, "LOCK_FILE", lock_file)

    # Create a fresh lock file
    with open(lock_file, "w") as f:
        f.write(str(time.time()))

    result = lock_mod.acquire_lock()
    assert result is False


def test_acquire_lock_returns_true_when_stale(tmp_path, monkeypatch):
    """acquire_lock returns True and overwrites a stale lock file."""
    from services.map import lock as lock_mod
    lock_file = str(tmp_path / "compute.lock")
    monkeypatch.setattr(lock_mod, "LOCK_FILE", lock_file)
    monkeypatch.setattr(lock_mod, "LOCK_TTL_SECONDS", 1)

    # Create a lock file and set its mtime to 10 seconds in the past
    with open(lock_file, "w") as f:
        f.write(str(time.time()))

    stale_mtime = time.time() - 10
    import os
    os.utime(lock_file, (stale_mtime, stale_mtime))

    result = lock_mod.acquire_lock()
    assert result is True


def test_release_lock_no_file_is_safe(tmp_path, monkeypatch):
    """release_lock does not raise when lock file does not exist."""
    from services.map import lock as lock_mod
    lock_file = str(tmp_path / "nonexistent.lock")
    monkeypatch.setattr(lock_mod, "LOCK_FILE", lock_file)
    lock_mod.release_lock()  # must not raise

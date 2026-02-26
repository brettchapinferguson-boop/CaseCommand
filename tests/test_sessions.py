"""Tests for session management."""
import time
from server import sessions, get_session, _evict_oldest_session, MAX_SESSIONS


def test_session_created():
    session = get_session("test-1")
    assert session["id"] == "test-1"
    assert session["history"] == []
    assert "created" in session
    assert "last_accessed" in session


def test_session_reused():
    s1 = get_session("reuse-test")
    s1["history"].append({"role": "user", "content": "hello"})
    s2 = get_session("reuse-test")
    assert len(s2["history"]) == 1
    assert s2 is s1


def test_session_last_accessed_updated():
    s = get_session("access-test")
    first_access = s["last_accessed"]
    time.sleep(0.01)
    get_session("access-test")
    assert s["last_accessed"] > first_access


def test_evict_oldest_session():
    sessions.clear()
    # Create sessions with staggered access times
    get_session("old")
    sessions["old"]["last_accessed"] = time.time() - 100
    get_session("new")
    sessions["new"]["last_accessed"] = time.time()

    _evict_oldest_session()
    assert "old" not in sessions
    assert "new" in sessions


def test_session_cap():
    """Test that session creation evicts oldest when at capacity."""
    sessions.clear()
    # Fill up to MAX_SESSIONS with a smaller limit for test
    import server

    original_max = server.MAX_SESSIONS
    server.MAX_SESSIONS = 5
    try:
        for i in range(5):
            s = get_session(f"s{i}")
            s["last_accessed"] = time.time() - (5 - i)

        # All 5 exist
        assert len(sessions) == 5

        # Adding one more should evict the oldest
        get_session("s-new")
        assert len(sessions) == 5
        assert "s0" not in sessions  # oldest was evicted
        assert "s-new" in sessions
    finally:
        server.MAX_SESSIONS = original_max

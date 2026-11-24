"""
Tests for Visitor Counter Flask Application
Uses fakeredis to avoid requiring a live Redis instance.
Run with:  python -m pytest tests/ -v
"""

import pytest
import fakeredis

# ── Patch redis.Redis BEFORE importing app ─────────────────────────────────────
import redis as _redis_module


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """
    Replace redis.Redis with a fakeredis.FakeRedis so no real Redis
    server is needed during unit/integration tests.
    """
    server = fakeredis.FakeServer()
    fake = fakeredis.FakeRedis(server=server, decode_responses=True)

    monkeypatch.setattr(_redis_module, "Redis", lambda **kwargs: fake)
    # Also patch fakeredis internals used in app
    return fake


@pytest.fixture()
def app_client(fake_redis):
    """Return a Flask test client with APP_ENV=testing."""
    import os
    os.environ["APP_ENV"] = "testing"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"

    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ═══════════════════════════════════════════════════════════════════════════════
# Homepage tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestHomepage:
    def test_homepage_returns_200(self, app_client):
        """Homepage should return HTTP 200."""
        response = app_client.get("/")
        assert response.status_code == 200

    def test_homepage_contains_title(self, app_client):
        """Homepage HTML should include the app title."""
        response = app_client.get("/")
        assert b"Visitor Counter" in response.data

    def test_homepage_contains_counter(self, app_client):
        """Homepage should display a numeric visitor count."""
        response = app_client.get("/")
        assert response.status_code == 200
        # Counter display should be present in the page
        assert b"Total Visitors" in response.data

    def test_visitor_count_increments(self, app_client):
        """Each homepage request should increment the visitor count."""
        r1 = app_client.get("/")
        r2 = app_client.get("/")
        r3 = app_client.get("/")
        # All three requests should succeed
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200
        # After 3 visits, the page should show "3" somewhere
        assert b"3" in r3.data

    def test_homepage_shows_redis_status(self, app_client):
        """Homepage should display Redis status information."""
        response = app_client.get("/")
        assert b"Redis" in response.data


# ═══════════════════════════════════════════════════════════════════════════════
# Health check tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoints:
    def test_health_returns_200(self, app_client):
        """/health should always return 200 (liveness probe)."""
        response = app_client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, app_client):
        """/health response should be JSON with status=ok."""
        response = app_client.get("/health")
        data = response.get_json()
        assert data is not None
        assert data["status"] == "ok"
        assert data["service"] == "flask"

    def test_ready_returns_200_when_redis_ok(self, app_client):
        """/ready should return 200 when Redis is reachable (fakeredis)."""
        response = app_client.get("/ready")
        assert response.status_code == 200

    def test_ready_returns_json_ready(self, app_client):
        """/ready JSON should indicate ready status."""
        response = app_client.get("/ready")
        data = response.get_json()
        assert data is not None
        assert data["status"] == "ready"
        assert data["redis"] == "connected"


# ═══════════════════════════════════════════════════════════════════════════════
# Stats endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatsEndpoint:
    def test_stats_returns_200(self, app_client):
        """/stats should return HTTP 200."""
        response = app_client.get("/stats")
        assert response.status_code == 200

    def test_stats_returns_visitor_count(self, app_client):
        """/stats JSON should contain visitor_count key."""
        # Hit homepage first to create the counter
        app_client.get("/")
        response = app_client.get("/stats")
        data = response.get_json()
        assert "visitor_count" in data
        assert isinstance(data["visitor_count"], int)
        assert data["visitor_count"] >= 1

    def test_stats_count_matches_visits(self, app_client):
        """Stats count should match actual number of homepage visits."""
        # Reset by going to /reset first
        app_client.post("/reset")
        for _ in range(5):
            app_client.get("/")
        response = app_client.get("/stats")
        data = response.get_json()
        assert data["visitor_count"] == 5


# ═══════════════════════════════════════════════════════════════════════════════
# Reset endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestResetEndpoint:
    def test_reset_allowed_in_testing(self, app_client):
        """/reset POST should succeed when APP_ENV=testing."""
        response = app_client.post("/reset")
        assert response.status_code == 200
        data = response.get_json()
        assert data["visitor_count"] == 0

    def test_reset_then_count_starts_from_one(self, app_client):
        """After reset, the first visit should set counter to 1."""
        # Accumulate some visits
        for _ in range(10):
            app_client.get("/")
        # Reset
        app_client.post("/reset")
        # One more visit
        app_client.get("/")
        response = app_client.get("/stats")
        data = response.get_json()
        assert data["visitor_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Redis-unavailable behavior test
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedisUnavailable:
    def test_homepage_handles_redis_down(self, monkeypatch):
        """
        When Redis is completely unreachable, the homepage should still
        return 200 (not crash) and show an error message rather than a 500.
        """
        import redis as redis_mod

        class BrokenRedis:
            """Simulates a Redis client that always raises ConnectionError."""
            def __init__(self, **kwargs):
                pass
            def incr(self, key):
                raise redis_mod.exceptions.ConnectionError("Connection refused")
            def ping(self):
                raise redis_mod.exceptions.ConnectionError("Connection refused")
            def get(self, key):
                raise redis_mod.exceptions.ConnectionError("Connection refused")

        monkeypatch.setattr(redis_mod, "Redis", BrokenRedis)

        import os
        os.environ["APP_ENV"] = "testing"

        # Must re-import app module so the monkeypatch applies
        import importlib
        import app as app_module
        importlib.reload(app_module)

        with app_module.app.test_client() as client:
            response = client.get("/")
            assert response.status_code == 200
            # Should show error message, not crash
            assert b"error" in response.data.lower() or b"unavailable" in response.data.lower()

    def test_ready_returns_503_when_redis_down(self, monkeypatch):
        """/ready should return 503 when Redis is unreachable."""
        import redis as redis_mod

        class BrokenRedis:
            def __init__(self, **kwargs): pass
            def ping(self):
                raise redis_mod.exceptions.ConnectionError("down")
            def incr(self, key):
                raise redis_mod.exceptions.ConnectionError("down")

        monkeypatch.setattr(redis_mod, "Redis", BrokenRedis)

        import importlib
        import app as app_module
        importlib.reload(app_module)

        with app_module.app.test_client() as client:
            response = client.get("/ready")
            assert response.status_code == 503
            data = response.get_json()
            assert data["status"] == "not_ready"

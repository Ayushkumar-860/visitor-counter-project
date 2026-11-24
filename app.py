"""
Visitor Counter Web Application
Flask + Redis - Cloud Computing Academic Project
"""

import os
import logging
import time
from flask import Flask, render_template, jsonify
import redis

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Flask App ──────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Redis Configuration (from environment variables) ──────────────────────────
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB   = int(os.environ.get("REDIS_DB", 0))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
REDIS_COUNTER_KEY = os.environ.get("REDIS_COUNTER_KEY", "visitor_count")

APP_TITLE = os.environ.get("APP_TITLE", "Visitor Counter — Cloud Computing Project")
APP_ENV   = os.environ.get("APP_ENV", "production")


def get_redis_client():
    """Create and return a Redis client. Raises on failure."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )


def redis_ping() -> bool:
    """Return True if Redis is reachable."""
    try:
        client = get_redis_client()
        return client.ping()
    except Exception as exc:
        logger.warning("Redis ping failed: %s", exc)
        return False


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Homepage: increment and display the visitor counter."""
    redis_ok = False
    visitor_count = None
    error_message = None

    try:
        client = get_redis_client()
        # Atomic increment — thread-safe across multiple Gunicorn workers
        visitor_count = client.incr(REDIS_COUNTER_KEY)
        redis_ok = True
        logger.info("Visit #%s recorded", visitor_count)
    except redis.exceptions.ConnectionError as exc:
        error_message = "Redis is unreachable. Counter is unavailable."
        logger.error("Redis connection error: %s", exc)
    except redis.exceptions.TimeoutError as exc:
        error_message = "Redis timed out. Counter is unavailable."
        logger.error("Redis timeout: %s", exc)
    except Exception as exc:
        error_message = f"Unexpected error: {exc}"
        logger.exception("Unexpected error when incrementing counter")

    return render_template(
        "index.html",
        visitor_count=visitor_count,
        redis_ok=redis_ok,
        error_message=error_message,
        app_title=APP_TITLE,
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        app_env=APP_ENV,
    )


@app.route("/health")
def health():
    """
    Liveness probe endpoint.
    Returns 200 as long as the Flask process is alive.
    Does NOT check Redis (so a Redis outage won't restart the pod).
    """
    return jsonify({"status": "ok", "service": "flask"}), 200


@app.route("/ready")
def ready():
    """
    Readiness probe endpoint.
    Returns 200 only when Redis is reachable.
    Kubernetes will remove the pod from the Service load-balancer while this returns non-200.
    """
    if redis_ping():
        return jsonify({"status": "ready", "redis": "connected"}), 200
    return jsonify({"status": "not_ready", "redis": "unreachable"}), 503


@app.route("/stats")
def stats():
    """Return current visitor count as JSON (useful for monitoring)."""
    try:
        client = get_redis_client()
        count = client.get(REDIS_COUNTER_KEY)
        return jsonify({
            "visitor_count": int(count) if count else 0,
            "redis_host": REDIS_HOST,
            "redis_port": REDIS_PORT,
        }), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 503


@app.route("/reset", methods=["POST"])
def reset():
    """Reset the visitor counter (for testing purposes only)."""
    if APP_ENV == "production":
        return jsonify({"error": "Reset not allowed in production"}), 403
    try:
        client = get_redis_client()
        client.set(REDIS_COUNTER_KEY, 0)
        return jsonify({"status": "reset", "visitor_count": 0}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 503


# ── Entry Point (dev only — Gunicorn is used in Docker) ──────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = APP_ENV != "production"
    logger.info("Starting Flask dev server on 0.0.0.0:%s (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)

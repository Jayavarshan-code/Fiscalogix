import os
import redis
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FIX L: Redis URL Unification
# WHAT WAS WRONG: redis_client.py read REDIS_HOST + REDIS_PORT env vars while
# celery_app.py read REDIS_URL (the full connection string). On cloud deployments
# (Render, Railway, Upstash), only REDIS_URL is provided. This meant redis_client
# (used by the FX cache warmer inference path) connected to localhost:6379 while
# Celery connected to the real Redis. They pointed to different instances.
# The FX cache warmer wrote to cloud Redis; the inference path read from a blank
# localhost Redis — cache was always empty, inference always used fallback rates.
#
# FIX: Both now use REDIS_URL as the primary env var, with localhost fallback.
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def get_redis_client() -> redis.Redis:
    """
    Creates a Redis client from REDIS_URL (same env var used by Celery).
    Includes socket timeouts to prevent blocking inference threads.
    """
    try:
        client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        # Validate connection is alive
        client.ping()
        logger.info(f"Redis client connected to {REDIS_URL.split('@')[-1]}")
        return client
    except redis.exceptions.ConnectionError as e:
        logger.warning(f"Redis: connection failed ({e}). Cache operations will use fallbacks.")
        # Return a non-connected client — callers handle connection errors gracefully
        return redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )


# Singleton global cache interface
cache = get_redis_client()

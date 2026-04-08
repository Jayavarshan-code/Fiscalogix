import os
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class NullRedisCache:
    """
    Drop-in Redis replacement used when the Redis server is unreachable.

    Reads return None  → all cache misses, system falls back to static values.
    Writes raise ConnectionError → callers' try/except returns False/failure,
      which surfaces a proper 503 from admin endpoints instead of silent success.
    """

    def get(self, key):
        return None

    def exists(self, *keys):
        return 0

    def ttl(self, key):
        return -2  # Redis convention: key does not exist

    def setex(self, name, time, value):
        raise redis.exceptions.ConnectionError("Redis unavailable (NullCache)")

    def set(self, name, value, ex=None, px=None, nx=False, xx=False):
        raise redis.exceptions.ConnectionError("Redis unavailable (NullCache)")

    def delete(self, *names):
        raise redis.exceptions.ConnectionError("Redis unavailable (NullCache)")

    def ping(self):
        raise redis.exceptions.ConnectionError("Redis unavailable (NullCache)")

    # Allow isinstance / type checks downstream if ever needed
    is_null = True


def get_redis_client():
    """
    Returns a live Redis client when the server is reachable, or a NullRedisCache
    when it is not. Callers never receive a disconnected real client — every
    `cache.get()` either returns a value or returns None cleanly.

    REDIS_AVAILABLE at module level reflects which path was taken so that
    health-check endpoints can surface it without re-testing the connection.
    """
    global REDIS_AVAILABLE
    try:
        client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        client.ping()
        REDIS_AVAILABLE = True
        logger.info(f"Redis connected: {REDIS_URL.split('@')[-1]}")
        return client
    except redis.exceptions.ConnectionError as e:
        REDIS_AVAILABLE = False
        logger.warning(
            f"Redis unavailable ({e}). "
            "WACC overrides and tariff/FX caching are disabled. "
            "All financial calculations fall back to static Damodaran benchmarks. "
            "Set REDIS_URL and restart to enable caching."
        )
        return NullRedisCache()


# Module-level state — set by get_redis_client() above
REDIS_AVAILABLE: bool = False

# Singleton used by all importers: `from app.Db.redis_client import cache`
cache = get_redis_client()

import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

def get_redis_client():
    pool = redis.ConnectionPool(
        host=REDIS_HOST, 
        port=REDIS_PORT, 
        db=0, 
        decode_responses=True,
        socket_timeout=1.0,
        socket_connect_timeout=1.0
    )
    return redis.Redis(connection_pool=pool)

# Singleton global cache interface
cache = get_redis_client()

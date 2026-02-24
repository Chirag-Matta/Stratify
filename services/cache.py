import json
import os
import redis

client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

CACHE_TTL = 300  # 5 minutes

def get_user_experiments_cache(user_id: str):
    key = f"user:{user_id}:experiments"
    data = client.get(key)
    if data:
        print(f"[Cache] HIT for user {user_id}")
        return json.loads(data)
    print(f"[Cache] MISS for user {user_id}")
    return None

def set_user_experiments_cache(user_id: str, experiments: list):
    key = f"user:{user_id}:experiments"
    client.setex(key, CACHE_TTL, json.dumps(experiments))
    print(f"[Cache] SET for user {user_id}")

def invalidate_user_cache(user_id: str):
    key = f"user:{user_id}:experiments"
    client.delete(key)
    print(f"[Cache] INVALIDATED for user {user_id}")
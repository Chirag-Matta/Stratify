import json
import os
import redis
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

# Configuration
BANNER_MIXTURE_TTL = 86400  # 24 hours
BANNER_COUNT = 3  # Number of banners to select


def get_banner_mixture_cache(user_id: str) -> Optional[Dict]:
    """
    Retrieve cached banner mixture for user.
    
    Returns:
        Dict with banners, assigned_at, expires_at, source_experiments
        or None if not found/expired
    """
    key = f"user:{user_id}:banner_mixture"
    data = client.get(key)
    if data:
        print(f"[BannerMixture] HIT for user {user_id}")
        return json.loads(data)
    print(f"[BannerMixture] MISS for user {user_id}")
    return None


def set_banner_mixture_cache(
    user_id: str, 
    banners: List[int],
    source_experiments: List[Dict]
) -> Dict:
    """
    Store banner mixture in cache with TTL.
    
    Args:
        user_id: User identifier
        banners: List of banner IDs [1, 2, 3]
        source_experiments: List of experiments that contributed
                           [{"name": "exp1", "variant": "var1"}, ...]
    
    Returns:
        The mixture data that was stored
    """
    key = f"user:{user_id}:banner_mixture"
    
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=BANNER_MIXTURE_TTL)
    
    mixture = {
        "banners": banners,
        "assigned_at": now.isoformat() + "Z",
        "expires_at": expires_at.isoformat() + "Z",
        "ttl_seconds": BANNER_MIXTURE_TTL,
        "source_experiments": source_experiments
    }
    
    client.setex(key, BANNER_MIXTURE_TTL, json.dumps(mixture))
    print(f"[BannerMixture] SET for user {user_id}: {banners}")
    
    return mixture


def invalidate_banner_mixture(user_id: str) -> None:
    """Clear cached banner mixture (on segment/experiment changes)."""
    key = f"user:{user_id}:banner_mixture"
    client.delete(key)
    print(f"[BannerMixture] INVALIDATED for user {user_id}")


def generate_banner_mixture(
    available_banners: List[int],
    target_count: int = BANNER_COUNT
) -> List[int]:
    """
    Generate random banner mixture from available banners.
    
    Args:
        available_banners: Pool of banner IDs to choose from
        target_count: Number of banners to select (default 3)
    
    Returns:
        List of selected banner IDs
    """
    if len(available_banners) == 0:
        return []
    
    # Select without replacement
    selected = random.sample(
        available_banners,
        k=min(target_count, len(available_banners))
    )
    
    return sorted(selected)  # Sort for consistency
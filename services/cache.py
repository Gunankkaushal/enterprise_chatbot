import hashlib
import json
from typing import Any, Dict, Optional

import config

try:
    import redis
except Exception:
    redis = None


_redis_client = None


def _get_redis_client():
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    if not config.REDIS_URL or redis is None:
        return None

    try:
        _redis_client = redis.Redis.from_url(
            config.REDIS_URL,
            decode_responses=True
        )
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = None
        return None


def build_cache_key(query: str, target_indexes: str) -> str:
    normalized_query = " ".join(query.strip().lower().split())
    query_hash = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
    
    # Strip spaces, quotes, and brackets to make it a clean Redis key
    # e.g., "['public', 1]" becomes "public,1"
    safe_targets = target_indexes.replace(" ", "").replace("'", "").replace('"', "").replace("[", "").replace("]", "")
    
    return f"ask_cache:targets:{safe_targets}:q:{query_hash}"


def get_cached_answer(cache_key: str) -> Optional[Dict[str, Any]]:
    client = _get_redis_client()
    if client is None:
        return None

    try:
        raw_value = client.get(cache_key)
        if not raw_value:
            return None
        return json.loads(raw_value)
    except Exception:
        return None


def set_cached_answer(cache_key: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
    client = _get_redis_client()
    if client is None:
        return

    try:
        client.setex(cache_key, ttl_seconds, json.dumps(payload))
    except Exception:
        return
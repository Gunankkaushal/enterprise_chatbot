import os
from typing import Dict

import redis
import requests


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8002")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_system_status() -> Dict[str, str]:
    backend = "down"
    redis_status = "down"

    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            backend = "up"
    except Exception:
        backend = "down"

    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        pong = client.ping()
        if pong:
            redis_status = "up"
    except Exception:
        redis_status = "down"

    return {"backend": backend, "redis": redis_status}

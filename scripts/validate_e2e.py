"""
End-to-end validation runner for the enterprise chatbot workflow.

Usage:
  python scripts/validate_e2e.py --base-url http://127.0.0.1:8002 --pdf "C:\\path\\to\\file.pdf"
"""

import argparse
import hashlib
import json
import os
import time
from typing import Dict

import requests
import redis


def _assert_status(response: requests.Response, expected: int, step: str) -> None:
    if response.status_code != expected:
        raise RuntimeError(
            f"{step} failed. Expected {expected}, got {response.status_code}. "
            f"Body: {response.text}"
        )


def _auth_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _build_cache_key(query: str, department_id: int) -> str:
    normalized_query = " ".join(query.strip().lower().split())
    query_hash = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
    return f"ask_cache:dept:{department_id}:q:{query_hash}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8002")
    parser.add_argument("--pdf", required=True, help="Path to PDF/DOCX for upload test")
    parser.add_argument("--admin-email", default=f"admin_e2e_{int(time.time())}@example.com")
    parser.add_argument("--admin-password", default="AdminE2E@12345")
    parser.add_argument("--user-password", default="UserE2E@12345")
    parser.add_argument("--department-name", default=f"E2E_Department_{int(time.time())}")
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    parser.add_argument(
        "--strict-cache-check",
        action="store_true",
        help="Fail run if Redis key is missing or second ask is significantly slower than first."
    )
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        raise FileNotFoundError(f"Upload test file not found: {args.pdf}")

    print("1) Register admin...")
    register_admin = requests.post(
        f"{args.base_url}/auth/register",
        json={
            "email": args.admin_email,
            "password": args.admin_password,
            "is_admin": True,
            "department_id": None,
        },
        timeout=30,
    )
    _assert_status(register_admin, 201, "Admin register")

    print("2) Login admin...")
    login_admin = requests.post(
        f"{args.base_url}/auth/login",
        json={"email": args.admin_email, "password": args.admin_password},
        timeout=30,
    )
    _assert_status(login_admin, 200, "Admin login")
    admin_token = login_admin.json()["access_token"]

    print("3) Create department...")
    create_department = requests.post(
        f"{args.base_url}/create/",
        data={"name": args.department_name},
        headers=_auth_header(admin_token),
        timeout=30,
    )
    _assert_status(create_department, 200, "Create department")
    department_id = create_department.json()["department"]["id"]

    print("4) Upload document...")
    with open(args.pdf, "rb") as file_stream:
        upload_response = requests.post(
            f"{args.base_url}/upload/",
            headers=_auth_header(admin_token),
            data={"department_id": str(department_id)},
            files={"file": (os.path.basename(args.pdf), file_stream)},
            timeout=300,
        )
    _assert_status(upload_response, 200, "Upload document")

    print("5) Register non-admin user...")
    user_email = f"user_e2e_{int(time.time())}@example.com"
    register_user = requests.post(
        f"{args.base_url}/auth/register",
        json={
            "email": user_email,
            "password": args.user_password,
            "is_admin": False,
            "department_id": department_id,
        },
        timeout=30,
    )
    _assert_status(register_user, 201, "User register")

    print("6) Login user...")
    login_user = requests.post(
        f"{args.base_url}/auth/login",
        json={"email": user_email, "password": args.user_password},
        timeout=30,
    )
    _assert_status(login_user, 200, "User login")
    user_token = login_user.json()["access_token"]

    print("7) Ask question...")
    ask_payload = {
        "query": "Summarize key policy points from uploaded documents.",
        "department_id": department_id,
    }
    first_start = time.perf_counter()
    ask_response = requests.post(
        f"{args.base_url}/ask/",
        headers=_auth_header(user_token),
        json=ask_payload,
        timeout=300,
    )
    first_elapsed = time.perf_counter() - first_start
    _assert_status(ask_response, 200, "Ask question")
    ask_json = ask_response.json()
    if "answer" not in ask_json or "status" not in ask_json:
        raise RuntimeError(f"Unexpected ask response: {ask_json}")

    print("8) Ask same question again for cache validation...")
    second_start = time.perf_counter()
    ask_cached = requests.post(
        f"{args.base_url}/ask/",
        headers=_auth_header(user_token),
        json=ask_payload,
        timeout=300,
    )
    second_elapsed = time.perf_counter() - second_start
    _assert_status(ask_cached, 200, "Ask cached question")
    ask_cached_json = ask_cached.json()

    cache_key = _build_cache_key(
        query=ask_payload["query"],
        department_id=department_id
    )
    redis_key_found = False
    redis_error = None
    try:
        redis_client = redis.Redis.from_url(args.redis_url, decode_responses=True)
        redis_key_found = bool(redis_client.exists(cache_key))
    except Exception as exc:
        redis_error = str(exc)

    print(f"   Cache key: {cache_key}")
    print(f"   First ask:  {first_elapsed:.3f}s")
    print(f"   Second ask: {second_elapsed:.3f}s")
    if redis_error:
        print(f"   Redis check warning: {redis_error}")
    else:
        print(f"   Redis key exists: {redis_key_found}")

    if args.strict_cache_check:
        if not redis_key_found:
            raise RuntimeError(
                "Strict cache check failed: expected Redis cache key to exist after repeated ask."
            )
        if second_elapsed > (first_elapsed * 1.5):
            raise RuntimeError(
                f"Strict cache check failed: cached request was unexpectedly slower "
                f"({second_elapsed:.3f}s vs {first_elapsed:.3f}s)."
            )
        if ask_cached_json != ask_json:
            raise RuntimeError("Strict cache check failed: cached response payload does not match original.")

    print("\nE2E validation passed.")
    print(json.dumps({
        "department_id": department_id,
        "admin_email": args.admin_email,
        "user_email": user_email,
        "ask_status": ask_json.get("status"),
        "sources_count": len(ask_json.get("sources", [])),
        "cache_key": cache_key,
        "redis_key_exists": redis_key_found,
        "first_ask_seconds": round(first_elapsed, 3),
        "second_ask_seconds": round(second_elapsed, 3),
    }, indent=2))


if __name__ == "__main__":
    main()

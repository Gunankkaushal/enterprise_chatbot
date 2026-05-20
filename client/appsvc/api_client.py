import os
from typing import Any, Dict, Optional

import jwt
import requests


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8002")


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(email: str, password: str) -> Dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=60
    )
    response.raise_for_status()
    return response.json()


def decode_token_claims(token: str) -> Dict[str, Any]:
    return jwt.decode(token, options={"verify_signature": False})


def ask_question(token: str, query: str, department_id: int) -> Dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/ask/",
        headers=_auth_headers(token),
        json={"query": query, "department_id": department_id},
        timeout=180
    )
    response.raise_for_status()
    return response.json()


def upload_document(token: str, department_id: int, file_name: str, file_bytes: bytes) -> Dict[str, Any]:
    files = {"file": (file_name, file_bytes)}
    data = {"department_id": str(department_id)}
    response = requests.post(
        f"{API_BASE_URL}/upload/",
        headers=_auth_headers(token),
        data=data,
        files=files,
        timeout=300
    )
    response.raise_for_status()
    return response.json()


def create_department(token: str, name: str) -> Dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/create/",
        headers=_auth_headers(token),
        data={"name": name},
        timeout=60
    )
    response.raise_for_status()
    return response.json()


def register_user(email: str, password: str, is_admin: bool, department_id: Optional[int]) -> Dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={
            "email": email,
            "password": password,
            "is_admin": is_admin,
            "department_id": department_id
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()

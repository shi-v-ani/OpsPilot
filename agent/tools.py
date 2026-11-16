"""HTTP wrappers for calling the file-service lab from the agent."""

import os

import httpx

FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://localhost:8000")


def probe_file_service(user: str) -> dict:
    r = httpx.get(f"{FILE_SERVICE_URL}/probe", params={"user": user}, timeout=10)
    r.raise_for_status()
    return r.json()


def reset_to_healthy() -> dict:
    r = httpx.post(f"{FILE_SERVICE_URL}/admin/scenarios/healthy", timeout=10)
    r.raise_for_status()
    return r.json()

"""
Shared pytest fixtures for the OpsPilot diagnostic evaluation harness.

The suite expects the lab to be running (docker compose up). The file-service
must be reachable at FILE_SERVICE_URL (default http://localhost:8000).
"""

import os
import time

import httpx
import pytest

BASE_URL = os.getenv("FILE_SERVICE_URL", "http://localhost:8000")


def _wait_for_services(timeout=30):
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_err = exc
        time.sleep(1)
    raise RuntimeError(
        f"file-service not reachable at {BASE_URL} after {timeout}s.\n"
        f"Start the lab first:  docker compose up\n"
        f"Last error: {last_err}"
    )


@pytest.fixture(scope="session", autouse=True)
def lab_ready():
    _wait_for_services()


@pytest.fixture
def lab():
    """Reset to healthy before and after each test. Yield the base URL."""
    httpx.post(f"{BASE_URL}/admin/scenarios/healthy", timeout=5)
    yield BASE_URL
    httpx.post(f"{BASE_URL}/admin/scenarios/healthy", timeout=5)


def apply_scenario(base_url, name):
    r = httpx.post(f"{base_url}/admin/scenarios/{name}", timeout=10)
    r.raise_for_status()
    return r.json()


def probe(base_url, user="alice"):
    r = httpx.get(f"{base_url}/probe", params={"user": user}, timeout=10)
    r.raise_for_status()
    return r.json()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    total = passed + failed
    if total == 0:
        return
    pct = 100.0 * passed / total
    terminalreporter.write_sep("=", "OPSPILOT DIAGNOSTIC BASELINE SCORECARD")
    terminalreporter.write_line(f"Total tests : {total}")
    terminalreporter.write_line(f"Passed      : {passed}")
    terminalreporter.write_line(f"Failed      : {failed}")
    terminalreporter.write_line(f"Score       : {passed}/{total} = {pct:.1f}%")
    terminalreporter.write_sep("=")

"""
Tests that /shared-drive/access returns the right HTTP status per scenario.
The auth_slow case is omitted here because it is covered in test_scenarios.
"""

import httpx
import pytest

from tests.conftest import apply_scenario


CASES = [
    ("healthy", 200),
    ("auth_down", 503),
    ("mount_missing", 503),
    ("network_partition", 503),
]


@pytest.mark.parametrize("scenario,expected_status", CASES)
def test_shared_drive_access_status(lab, scenario, expected_status):
    apply_scenario(lab, scenario)
    r = httpx.get(f"{lab}/shared-drive/access", timeout=10)
    assert r.status_code == expected_status


def test_shared_drive_access_body_on_success(lab):
    apply_scenario(lab, "healthy")
    r = httpx.get(f"{lab}/shared-drive/access", timeout=10)
    body = r.json()
    assert body["status"] == "ok"
    assert body["user"] == "alice"
    assert body["resource"] == "shared-drive"
    assert "auth_latency_ms" in body

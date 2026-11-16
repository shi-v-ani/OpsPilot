"""
Core diagnostic tests: for each scenario and user, apply the scenario,
call /probe, and assert the root_cause_hint.
"""

import pytest

from tests.conftest import apply_scenario, probe


FAST_SCENARIOS = [
    ("healthy", None),
    ("auth_down", "auth_service_unavailable"),
    ("mount_missing", "file_storage_mount_missing"),
    ("network_partition", "network_unreachable"),
]

USERS = ["alice", "bob", "charlie"]


@pytest.mark.parametrize("scenario,expected_hint", FAST_SCENARIOS)
@pytest.mark.parametrize("user", USERS)
def test_probe_root_cause_hint(lab, scenario, expected_hint, user):
    apply_scenario(lab, scenario)
    result = probe(lab, user=user)
    assert result["user"] == user
    assert result["root_cause_hint"] == expected_hint


@pytest.mark.parametrize("user", USERS)
def test_probe_auth_slow(lab, user):
    # auth_slow takes ~2s per probe because the file-service times out
    apply_scenario(lab, "auth_slow")
    result = probe(lab, user=user)
    assert result["root_cause_hint"] == "auth_timeout"
    assert result["checks"]["auth"]["latency_ms"] >= 1500

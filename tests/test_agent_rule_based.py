"""
Rule-based (hermetic) agent tests. Each test applies a scenario, runs the
agent end-to-end with approval granted, and asserts:
  - the diagnosis matches the expected root cause
  - the verification confirms the fix worked
"""

import pytest

from agent.graph import run_incident
from tests.conftest import apply_scenario


FAST = [
    ("healthy", None),
    ("auth_down", "auth_service_unavailable"),
    ("mount_missing", "file_storage_mount_missing"),
    ("network_partition", "network_unreachable"),
]

USERS = ["alice", "bob", "charlie"]


@pytest.mark.parametrize("scenario,expected", FAST)
@pytest.mark.parametrize("user", USERS)
def test_agent_diagnoses_and_fixes(lab, scenario, expected, user):
    apply_scenario(lab, scenario)
    result = run_incident(user=user, approved=True)
    assert result["diagnosis"]["root_cause"] == expected
    assert result["verification"]["resolved"] is True


@pytest.mark.parametrize("user", USERS)
def test_agent_handles_auth_slow(lab, user):
    apply_scenario(lab, "auth_slow")
    result = run_incident(user=user, approved=True)
    assert result["diagnosis"]["root_cause"] == "auth_timeout"
    assert result["verification"]["resolved"] is True

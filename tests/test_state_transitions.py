"""
Tests that scenario state transitions are clean and predictable.
"""

import httpx

from tests.conftest import apply_scenario, probe


def test_healthy_is_default(lab):
    # lab fixture already reset to healthy
    r = probe(lab)
    assert r["root_cause_hint"] is None


def test_unknown_scenario_returns_404(lab):
    r = httpx.post(f"{lab}/admin/scenarios/does_not_exist", timeout=5)
    assert r.status_code == 404


def test_transition_between_scenarios(lab):
    apply_scenario(lab, "auth_down")
    r = probe(lab)
    assert r["root_cause_hint"] == "auth_service_unavailable"

    apply_scenario(lab, "mount_missing")
    r = probe(lab)
    assert r["root_cause_hint"] == "file_storage_mount_missing"
    # auth must be healthy again after the switch
    assert r["checks"]["auth"]["status"] == 200


def test_healthy_resets_all_failures(lab):
    apply_scenario(lab, "auth_down")
    apply_scenario(lab, "mount_missing")
    apply_scenario(lab, "healthy")
    r = probe(lab)
    assert r["root_cause_hint"] is None
    assert r["checks"]["auth"]["status"] == 200
    assert r["checks"]["file_storage"]["mounted"] is True


def test_reapplying_scenario_is_idempotent(lab):
    apply_scenario(lab, "auth_down")
    apply_scenario(lab, "auth_down")
    r = probe(lab)
    assert r["root_cause_hint"] == "auth_service_unavailable"

"""
Deep assertions on the /probe response payload, one test per scenario.
Verifies the specific fields a downstream agent would consume.
"""

from tests.conftest import apply_scenario, probe


def test_healthy_all_checks_green(lab):
    apply_scenario(lab, "healthy")
    r = probe(lab)
    assert r["checks"]["auth"]["reachable"] is True
    assert r["checks"]["auth"]["status"] == 200
    assert r["checks"]["auth"]["reason"] is None
    assert r["checks"]["file_storage"]["mounted"] is True
    assert r["checks"]["shared_drive"]["accessible"] is True
    assert r["root_cause_hint"] is None


def test_auth_down_checks(lab):
    apply_scenario(lab, "auth_down")
    r = probe(lab)
    assert r["checks"]["auth"]["reachable"] is True
    assert r["checks"]["auth"]["status"] == 503
    assert r["checks"]["auth"]["reason"] == "auth_service_unavailable"
    assert r["checks"]["file_storage"]["mounted"] is True
    assert r["checks"]["shared_drive"]["accessible"] is False


def test_auth_slow_checks(lab):
    apply_scenario(lab, "auth_slow")
    r = probe(lab)
    assert r["checks"]["auth"]["reachable"] is True
    assert r["checks"]["auth"]["status"] is None
    assert r["checks"]["auth"]["reason"] == "auth_timeout"
    assert r["checks"]["auth"]["latency_ms"] >= 1500
    assert r["checks"]["shared_drive"]["accessible"] is False


def test_mount_missing_checks(lab):
    apply_scenario(lab, "mount_missing")
    r = probe(lab)
    assert r["checks"]["auth"]["reachable"] is True
    assert r["checks"]["auth"]["status"] == 200
    assert r["checks"]["file_storage"]["mounted"] is False
    assert r["checks"]["shared_drive"]["accessible"] is False


def test_network_partition_checks(lab):
    apply_scenario(lab, "network_partition")
    r = probe(lab)
    assert r["checks"]["auth"]["reachable"] is False
    assert r["checks"]["auth"]["status"] is None
    assert r["checks"]["auth"]["reason"] == "network_unreachable"
    assert r["checks"]["auth"]["latency_ms"] == 0.0

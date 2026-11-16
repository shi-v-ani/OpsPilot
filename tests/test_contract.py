"""
Contract tests: the /probe response shape must not drift.
If these fail, the future LangGraph agent's tool schema needs updating too.
"""

from tests.conftest import probe


def test_probe_top_level_keys(lab):
    r = probe(lab)
    assert set(r.keys()) == {"user", "checks", "root_cause_hint"}


def test_probe_checks_keys(lab):
    r = probe(lab)
    assert set(r["checks"].keys()) == {"auth", "file_storage", "shared_drive"}


def test_probe_auth_keys(lab):
    r = probe(lab)
    assert set(r["checks"]["auth"].keys()) == {
        "reachable", "status", "latency_ms", "reason"
    }


def test_probe_file_storage_keys(lab):
    r = probe(lab)
    assert set(r["checks"]["file_storage"].keys()) == {"mounted"}


def test_probe_shared_drive_keys(lab):
    r = probe(lab)
    assert set(r["checks"]["shared_drive"].keys()) == {"accessible"}


def test_probe_echoes_user(lab):
    for user in ["alice", "bob", "charlie"]:
        r = probe(lab, user=user)
        assert r["user"] == user

"""
Safety tests: the agent must NOT execute without explicit human approval,
must record a full audit trail, and must escalate unknown root causes.
"""

from unittest.mock import patch

from agent.graph import run_incident
from tests.conftest import apply_scenario


def test_agent_does_not_execute_without_approval(lab):
    apply_scenario(lab, "auth_down")
    result = run_incident(user="alice", approved=False)
    assert result["execution"]["status"] == "skipped"
    assert result["verification"]["resolved"] is False


def test_agent_executes_with_approval(lab):
    apply_scenario(lab, "auth_down")
    result = run_incident(user="alice", approved=True)
    assert result["execution"]["status"] == "executed"
    assert result["verification"]["resolved"] is True


def test_agent_records_full_audit_trail(lab):
    apply_scenario(lab, "auth_down")
    result = run_incident(user="alice", approved=True)
    steps = [e["step"] for e in result["audit"]]
    assert steps == [
        "observe",
        "diagnose",
        "plan_remediation",
        "request_approval",
        "execute",
        "verify",
    ]
    for entry in result["audit"]:
        assert entry["timestamp"]
        assert isinstance(entry["details"], dict)


def test_agent_escalates_unknown_root_cause(lab):
    fake_probe = {
        "user": "alice",
        "checks": {
            "auth": {"reachable": True, "status": 200,
                     "latency_ms": 1.0, "reason": None},
            "file_storage": {"mounted": True},
            "shared_drive": {"accessible": True},
        },
        "root_cause_hint": "quantum_flux_inversion",
    }
    with patch("agent.nodes.probe_file_service", return_value=fake_probe):
        result = run_incident(user="alice", approved=True)
    assert result["diagnosis"]["root_cause"] == "quantum_flux_inversion"
    assert result["remediation"]["action"] == "escalate"
    assert result["execution"]["status"] == "escalated"


def test_agent_noop_on_healthy_system(lab):
    apply_scenario(lab, "healthy")
    result = run_incident(user="alice", approved=True)
    assert result["diagnosis"]["root_cause"] is None
    assert result["remediation"]["action"] == "none"
    assert result["execution"]["status"] == "noop"
    assert result["verification"]["resolved"] is True

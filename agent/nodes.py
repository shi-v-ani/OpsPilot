from datetime import datetime, timezone

from agent.llm import diagnose_rule_based, diagnose_with_llm
from agent.state import AgentState
from agent.tools import probe_file_service, reset_to_healthy


REMEDIATION_LIBRARY = {
    "auth_service_unavailable": {
        "action": "restart_auth_service",
        "command": "docker compose restart auth-service",
        "rationale": "Auth service returned 503. Restarting restores availability.",
        "risk_level": "low",
    },
    "auth_timeout": {
        "action": "restart_auth_service",
        "command": "docker compose restart auth-service",
        "rationale": "Auth service is slow. A restart clears stuck work.",
        "risk_level": "low",
    },
    "file_storage_mount_missing": {
        "action": "restore_storage_mount",
        "command": "POST /admin/scenarios/healthy",
        "rationale": "Shared-drive mount is missing. Reset restores it in the lab.",
        "risk_level": "medium",
    },
    "network_unreachable": {
        "action": "restore_network",
        "command": "POST /admin/scenarios/healthy",
        "rationale": "Network between services is cut. Reset heals it in the lab.",
        "risk_level": "medium",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(state: AgentState, step: str, details: dict) -> None:
    if "audit" not in state or state["audit"] is None:
        state["audit"] = []
    state["audit"].append(
        {"step": step, "details": details, "timestamp": _now()}
    )


def observe(state: AgentState) -> AgentState:
    probe = probe_file_service(state["user"])
    state["probe"] = probe
    _audit(state, "observe", {"root_cause_hint": probe.get("root_cause_hint")})
    return state


def diagnose(state: AgentState) -> AgentState:
    result = diagnose_with_llm(state["probe"])
    source = "llm"
    if result is None:
        result = diagnose_rule_based(state["probe"])
        source = "rule_based"
    state["diagnosis"] = result
    _audit(state, "diagnose", {
        "root_cause": result.get("root_cause"),
        "source": source,
    })
    return state


def plan_remediation(state: AgentState) -> AgentState:
    diag = state.get("diagnosis") or {}
    root = diag.get("root_cause")

    if root is None:
        plan = {
            "action": "none",
            "command": None,
            "rationale": "System is healthy; no action needed.",
            "risk_level": "none",
        }
    else:
        plan = REMEDIATION_LIBRARY.get(root) or {
            "action": "escalate",
            "command": None,
            "rationale": f"Unknown root cause '{root}' — escalating to human.",
            "risk_level": "high",
        }

    state["remediation"] = plan
    _audit(state, "plan_remediation", {"action": plan["action"]})
    return state


def request_approval(state: AgentState) -> AgentState:
    """Passthrough — the graph exposes the state at this point.
    The caller decides whether to resume with approved=True or False."""
    _audit(state, "request_approval", {"proposed": state.get("remediation")})
    return state


def execute(state: AgentState) -> AgentState:
    if not state.get("approved"):
        state["execution"] = {"status": "skipped", "reason": "not approved"}
        _audit(state, "execute", {"status": "skipped"})
        return state

    rem = state.get("remediation") or {}
    action = rem.get("action")

    if action == "none":
        state["execution"] = {"status": "noop", "reason": "system already healthy"}
    elif action == "escalate":
        state["execution"] = {"status": "escalated",
                              "reason": "unknown root cause"}
    else:
        result = reset_to_healthy()
        state["execution"] = {"status": "executed", "result": result}

    _audit(state, "execute", {"status": state["execution"]["status"]})
    return state


def verify(state: AgentState) -> AgentState:
    exec_status = (state.get("execution") or {}).get("status")
    if exec_status in ("skipped", "escalated"):
        state["verification"] = {
            "after_probe": None,
            "resolved": False,
            "reason": f"execution was {exec_status}",
        }
    else:
        after = probe_file_service(state["user"])
        state["verification"] = {
            "after_probe": after,
            "resolved": after.get("root_cause_hint") is None,
        }
    _audit(state, "verify", {"resolved": state["verification"]["resolved"]})
    return state

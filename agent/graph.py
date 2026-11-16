"""LangGraph wiring for the OpsPilot incident-response agent."""

import uuid

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    diagnose,
    execute,
    observe,
    plan_remediation,
    request_approval,
    verify,
)
from agent.state import AgentState


def build_agent():
    g = StateGraph(AgentState)

    g.add_node("observe", observe)
    g.add_node("diagnose", diagnose)
    g.add_node("plan_remediation", plan_remediation)
    g.add_node("request_approval", request_approval)
    g.add_node("execute", execute)
    g.add_node("verify", verify)

    g.add_edge(START, "observe")
    g.add_edge("observe", "diagnose")
    g.add_edge("diagnose", "plan_remediation")
    g.add_edge("plan_remediation", "request_approval")
    g.add_edge("request_approval", "execute")
    g.add_edge("execute", "verify")
    g.add_edge("verify", END)

    return g.compile()


def run_incident(user: str = "alice", approved: bool = False) -> dict:
    """Run one incident end-to-end. If approved=False, execution is skipped."""
    graph = build_agent()
    initial: AgentState = {
        "incident_id": str(uuid.uuid4()),
        "user": user,
        "approved": approved,
        "audit": [],
    }
    return dict(graph.invoke(initial))

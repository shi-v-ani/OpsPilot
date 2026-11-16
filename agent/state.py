from typing import Optional, TypedDict


class AuditEntry(TypedDict):
    step: str
    details: dict
    timestamp: str


class AgentState(TypedDict, total=False):
    incident_id: str
    user: str
    probe: dict
    diagnosis: Optional[dict]
    remediation: Optional[dict]
    approved: Optional[bool]
    execution: Optional[dict]
    verification: Optional[dict]
    audit: list[AuditEntry]
    error: Optional[str]

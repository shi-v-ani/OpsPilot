"""Pluggable diagnosis: LLM if configured, deterministic fallback otherwise."""

import json
import os
from typing import Optional


_RULE_BASED_MAP = {
    "auth_service_unavailable": {
        "root_cause": "auth_service_unavailable",
        "confidence": 0.95,
        "evidence": "auth-service returned HTTP 503 (probe auth.status=503)",
        "summary": "The authentication service is down.",
    },
    "auth_timeout": {
        "root_cause": "auth_timeout",
        "confidence": 0.90,
        "evidence": "auth-service did not respond within the 2.0s client timeout",
        "summary": "Authentication is slow and times out.",
    },
    "file_storage_mount_missing": {
        "root_cause": "file_storage_mount_missing",
        "confidence": 0.95,
        "evidence": "probe reports file_storage.mounted=false",
        "summary": "The shared-drive storage mount is missing.",
    },
    "network_unreachable": {
        "root_cause": "network_unreachable",
        "confidence": 0.90,
        "evidence": "file-service could not reach auth-service (probe auth.reachable=false)",
        "summary": "The network path from file-service to auth-service is down.",
    },
    None: {
        "root_cause": None,
        "confidence": 1.0,
        "evidence": "all probe checks are green",
        "summary": "The system is healthy; no incident.",
    },
}


def diagnose_rule_based(probe: dict) -> dict:
    hint = probe.get("root_cause_hint")
    return _RULE_BASED_MAP.get(hint, {
        "root_cause": hint,
        "confidence": 0.50,
        "evidence": "unrecognized root_cause_hint",
        "summary": "Unrecognized failure mode; escalating is advised.",
    })


def diagnose_with_llm(probe: dict) -> Optional[dict]:
    """Return LLM diagnosis, or None if no API key is configured."""
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-3-5-haiku-latest", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    else:
        return None

    prompt = (
        "You are an IT operations diagnostic assistant. Given the following "
        "/probe JSON from a monitoring system, identify the root cause. "
        "Respond ONLY with valid JSON matching exactly this schema: "
        '{"root_cause": string|null, "confidence": float between 0 and 1, '
        '"evidence": string, "summary": string}\n\n'
        f"PROBE JSON:\n{json.dumps(probe, indent=2)}"
    )

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        return json.loads(content)
    except Exception:
        return None

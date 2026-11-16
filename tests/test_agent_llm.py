"""
LLM-backed diagnosis tests. These are SKIPPED unless you have an API key set:

    $env:OPENAI_API_KEY = "sk-..."
    # or
    $env:ANTHROPIC_API_KEY = "sk-ant-..."
    pip install langchain-openai        # or langchain-anthropic
"""

import os

import pytest

from agent.graph import run_incident
from tests.conftest import apply_scenario


HAS_KEY = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))

pytestmark = pytest.mark.skipif(
    not HAS_KEY,
    reason="No LLM API key configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)",
)


SCENARIOS = [
    ("auth_down", "auth_service_unavailable"),
    ("mount_missing", "file_storage_mount_missing"),
    ("network_partition", "network_unreachable"),
]


@pytest.mark.parametrize("scenario,expected", SCENARIOS)
def test_llm_diagnoses_correctly(lab, scenario, expected):
    apply_scenario(lab, scenario)
    result = run_incident(user="alice", approved=True)
    assert result["diagnosis"]["root_cause"] == expected

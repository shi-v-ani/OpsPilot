# OpsPilot AI

A practical lab for demonstrating AI-assisted IT operations with safety boundaries.

## Services

- **auth-service** (port 8001) — verifies users, failure toggles: `auth_down`, `auth_slow`
- **file-service** (port 8000) — shared-drive access, `/probe` diagnostics, `/admin/scenarios/{name}`

## Agent

`agent/` is a LangGraph state machine that turns incidents into safe remediations:

    observe -> diagnose -> plan_remediation -> request_approval -> execute -> verify

- **observe** calls `/probe` on file-service
- **diagnose** returns `{root_cause, confidence, evidence, summary}` (LLM if API key present, deterministic fallback otherwise)
- **plan_remediation** maps the root cause to a specific action + risk level
- **request_approval** pauses for a human decision
- **execute** runs the fix ONLY if approved
- **verify** re-probes to confirm resolution
- **audit trail** records every step with a timestamp

Demo:

    docker compose up                       # Terminal A
    python -m agent.cli --user alice        # Terminal B

## Quick start

    docker compose up

## Tests

Start the lab, then:

    pip install -r requirements-dev.txt

    # Phase 3: diagnostic baseline
    pytest tests/test_scenarios.py tests/test_checks_details.py tests/test_shared_drive.py tests/test_state_transitions.py tests/test_contract.py

    # Phase 4: agent tests
    pytest tests/test_agent_rule_based.py tests/test_agent_approval.py tests/test_agent_llm.py

    # Everything together
    pytest

Baseline (Phase 3): **36/36 = 100%**.
Agent (Phase 4): **20/20 = 100%** (hermetic path), 3 LLM tests skipped unless API key is set.
Combined: **56/56 = 100%**, 3 skipped.

The agent must not regress the baseline, must respect the approval gate,
and must produce a complete audit trail. All of that is tested.

## Optional: LLM-backed diagnosis

    $env:OPENAI_API_KEY = "sk-..."
    pip install langchain-openai
    pytest tests/test_agent_llm.py

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graph.graph_builder import GraphBuilder
from agents.email_trigger import EmailTriggerAgent


def test_no_messages_prevents_downstream(monkeypatch) -> None:
    # Monkeypatch EmailTriggerAgent._fetch_emails to return empty list
    monkeypatch.setattr(EmailTriggerAgent, "_fetch_emails", lambda self, cfg: [])

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-no-msg",
        "nodes": [
            {"id": "email1", "data": {"kind": "email-trigger"}},
            {"id": "llm1", "data": {"kind": "llm"}},
            {"id": "send1", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "email1", "target": "llm1"},
            {"source": "llm1", "target": "send1"},
        ],
    }

    result = builder.execute_workflow(workflow)

    # visited_nodes will include executed nodes; check whether downstream nodes ran
    # The implementation may still traverse graph nodes depending on the StateGraph implementation.
    # Ensure EmailTrigger logged the no-messages condition and that downstream agents did not produce output keys
    exec_log = result.get("execution_log", [])

    assert any("Email trigger matched: 0" in entry for entry in exec_log)
    # downstream agents should not have produced outputs like llm_output or email_sent
    assert "llm_output" not in result
    assert "email_sent" not in result

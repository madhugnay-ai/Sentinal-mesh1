import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graph.graph_builder import GraphBuilder
from agents.email_trigger import EmailTriggerAgent
from agents.agent_registry import AgentRegistry


def test_no_messages_short_circuit(monkeypatch) -> None:
    # EmailTrigger returns no messages
    monkeypatch.setattr(EmailTriggerAgent, "_fetch_emails", lambda self, cfg: [])

    # Prepare dummy downstream agents that would record calls
    class DummyAgent:
        def __init__(self):
            self.called = False

        def execute(self, state):
            self.called = True
            state.setdefault("execution_log", []).append("dummy executed")
            state["dummy_called"] = True
            return state

    dummy_llm = DummyAgent()
    dummy_send = DummyAgent()

    # Monkeypatch AgentRegistry.get_agent to return our specific agents
    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Email Trigger":
            return EmailTriggerAgent()
        if node_type == "LLM":
            return dummy_llm
        if node_type == "Send Email":
            return dummy_send
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-no-msg-2",
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

    graph = builder.build_graph(workflow)
    initial_state = {
        "workflow_id": workflow["workflow_id"],
        "current_node": None,
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow,
    }

    final_state = graph.invoke(initial_state)

    # Email trigger should have recorded the no-messages log
    assert any("found no matching messages" in e for e in final_state.get("execution_log", []))
    # Downstream agents must NOT have been called
    assert dummy_llm.called is False
    assert dummy_send.called is False
    # No downstream outputs should exist
    assert "llm_output" not in final_state
    assert "email_sent" not in final_state
    # execution_status should be preserved as no_messages (set by EmailTrigger)
    assert final_state.get("execution_status") == "no_messages"


def test_normal_workflow_runs_downstream(monkeypatch) -> None:
    # EmailTrigger returns one message
    messages = [
        {"message_id": "m1", "sender": "a@example.com", "recipient": "me@example.com", "subject": "Hi", "body": "Hello", "received_at": "2020-01-02T00:00:00Z", "unread": True},
    ]
    monkeypatch.setattr(EmailTriggerAgent, "_fetch_emails", lambda self, cfg: messages)

    class DummyLLM:
        def __init__(self):
            self.called = False

        def execute(self, state):
            self.called = True
            state["llm_output"] = "ok"
            state.setdefault("execution_log", []).append("llm executed")
            state["execution_status"] = "completed"
            return state

    class DummySend:
        def __init__(self):
            self.called = False

        def execute(self, state):
            self.called = True
            state["email_sent"] = True
            state.setdefault("execution_log", []).append("send executed")
            state["email_status"] = "sent"
            return state

    dummy_llm = DummyLLM()
    dummy_send = DummySend()

    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Email Trigger":
            return EmailTriggerAgent()
        if node_type == "LLM":
            return dummy_llm
        if node_type == "Send Email":
            return dummy_send
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-normal",
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

    graph = builder.build_graph(workflow)
    initial_state = {
        "workflow_id": workflow["workflow_id"],
        "current_node": None,
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow,
    }

    final_state = graph.invoke(initial_state)

    assert dummy_llm.called is True
    assert dummy_send.called is True
    assert final_state.get("llm_output") == "ok"
    assert final_state.get("email_sent") is True
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.email_trigger import EmailTriggerAgent
from agents.supervisor import SupervisorAgent
from constants import node_types
from graph.graph_builder import GraphBuilder


def test_no_messages_workflow_monitoring(monkeypatch) -> None:
    # EmailTrigger returns no messages
    monkeypatch.setattr(EmailTriggerAgent, "_fetch_emails", lambda self, cfg: [])

    class DummyLLM:
        def __init__(self):
            self.called = False

        def execute(self, state):
            self.called = True
            state["llm_output"] = "ok"
            state.setdefault("execution_log", []).append("llm executed")
            return state

    class DummySend:
        def __init__(self):
            self.called = False

        def execute(self, state):
            self.called = True
            state["email_sent"] = True
            state.setdefault("execution_log", []).append("send executed")
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
        "workflow_id": "wf-no-msg-monitor",
        "nodes": [
            {"id": "email1", "data": {"kind": "email-trigger", "label": "Email Trigger"}},
            {"id": "llm1", "data": {"kind": "llm", "label": "LLM"}},
            {"id": "send1", "data": {"kind": "send-email", "label": "Send Email"}},
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
    supervisor = SupervisorAgent()
    final_state = supervisor.execute(final_state)

    from agents.failure_detection import FailureDetectionAgent
    from agents.auto_healing import AutoHealingAgent

    failure_detector = FailureDetectionAgent()
    auto_healer = AutoHealingAgent()
    final_state = failure_detector.execute(final_state)
    final_state = auto_healer.execute(final_state)

    print('DEBUG final_state keys', sorted(final_state.keys()))
    print('DEBUG completed_stages', final_state.get('completed_stages'))
    print('DEBUG skipped_stages', final_state.get('skipped_stages'))
    print('DEBUG failed_stages', final_state.get('failed_stages'))
    print('DEBUG executed_nodes', final_state.get('executed_nodes'))
    print('DEBUG skipped_nodes', final_state.get('skipped_nodes'))
    print('DEBUG execution_log', final_state.get('execution_log'))

    assert dummy_llm.called is False
    assert dummy_send.called is False
    assert final_state["execution_status"] == "no_messages"
    assert final_state["workflow_health"] == "Healthy"
    assert final_state["failure_category"] == "None"
    assert final_state["failure_severity"] == "Low"
    assert final_state["healing_strategy"] == "No Recovery Needed"
    assert final_state["healing_status"] == "Not Required"
    assert final_state["completed_stages"] == ["Email Trigger"]
    assert final_state["skipped_stages"] == ["LLM", "Send Email"]
    assert final_state["failed_stages"] == []


def test_normal_workflow_monitoring(monkeypatch) -> None:
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
            return state

    class DummySend:
        def __init__(self):
            self.called = False

        def execute(self, state):
            self.called = True
            state["email_sent"] = True
            state.setdefault("execution_log", []).append("send executed")
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
        "workflow_id": "wf-normal-monitor",
        "nodes": [
            {"id": "email1", "data": {"kind": "email-trigger", "label": "Email Trigger"}},
            {"id": "llm1", "data": {"kind": "llm", "label": "LLM"}},
            {"id": "send1", "data": {"kind": "send-email", "label": "Send Email"}},
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
    supervisor = SupervisorAgent()
    final_state = supervisor.execute(final_state)

    from agents.failure_detection import FailureDetectionAgent
    from agents.auto_healing import AutoHealingAgent

    failure_detector = FailureDetectionAgent()
    auto_healer = AutoHealingAgent()
    final_state = failure_detector.execute(final_state)
    final_state = auto_healer.execute(final_state)

    assert dummy_llm.called is True
    assert dummy_send.called is True
    assert final_state["workflow_health"] == "Healthy"
    assert final_state["failure_category"] == "None"
    assert final_state["completed_stages"] == ["Email Trigger", "LLM", "Send Email"]
    assert final_state["skipped_stages"] == []
    assert final_state["failed_stages"] == []

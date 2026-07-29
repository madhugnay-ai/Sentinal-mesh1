import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from agents.agent_registry import AgentRegistry
from agents.condition_agent import ConditionAgent
from agents.email_trigger import EmailTriggerAgent
from graph.graph_builder import GraphBuilder


def make_state(current_node: str, workflow_data: dict, initial_state: dict | None = None) -> dict:
    state = {
        "workflow_id": "wf-test",
        "current_node": current_node,
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow_data,
    }
    if initial_state:
        state.update(initial_state)
    return state


def build_condition_node(operator: str, value: str = "", field: str = "email_subject") -> dict:
    return {
        "id": "condition1",
        "data": {
            "kind": "condition",
            "field": field,
            "operator": operator,
            "value": value,
        },
    }


def test_condition_equals_true() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("equals", "Critical")], "edges": []}
    state = make_state("condition1", workflow, {"email_subject": "Critical"})

    result = agent.execute(state)

    assert result["condition_result"] is True
    assert result["execution_status"] == "completed"
    assert "Condition evaluated" in result["execution_log"][-1]


def test_condition_equals_false() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("equals", "Critical")], "edges": []}
    state = make_state("condition1", workflow, {"email_subject": "Normal"})

    result = agent.execute(state)

    assert result["condition_result"] is False
    assert result["execution_status"] == "completed"


def test_condition_contains() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("contains", "URGENT")], "edges": []}
    state = make_state("condition1", workflow, {"email_subject": "This is URGENT"})

    result = agent.execute(state)

    assert result["condition_result"] is True


def test_condition_not_contains() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("not_contains", "URGENT")], "edges": []}
    state = make_state("condition1", workflow, {"email_subject": "Normal update"})

    result = agent.execute(state)

    assert result["condition_result"] is True


def test_condition_greater_than() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("greater_than", "10", "severity")], "edges": []}
    state = make_state("condition1", workflow, {"severity": "15"})

    result = agent.execute(state)

    assert result["condition_result"] is True


def test_condition_less_than() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("less_than", "10", "severity")], "edges": []}
    state = make_state("condition1", workflow, {"severity": "5"})

    result = agent.execute(state)

    assert result["condition_result"] is True


def test_condition_exists() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("exists", "", "email_subject")], "edges": []}
    state = make_state("condition1", workflow, {"email_subject": "Hello"})

    result = agent.execute(state)

    assert result["condition_result"] is True


def test_condition_not_exists() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("not_exists", "", "email_subject")], "edges": []}
    state = make_state("condition1", workflow, {})

    result = agent.execute(state)

    assert result["condition_result"] is True


def test_condition_invalid_operator() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [build_condition_node("contains_not", "x")], "edges": []}
    state = make_state("condition1", workflow, {"email_subject": "test"})

    result = agent.execute(state)

    assert result["execution_status"] == "failed"
    assert "Unsupported condition operator" in result["errors"][0]


def test_condition_missing_field() -> None:
    agent = ConditionAgent()
    workflow = {"nodes": [{"id": "condition1", "data": {"kind": "condition", "operator": "equals", "value": "x"}}], "edges": []}
    state = make_state("condition1", workflow, {})

    result = agent.execute(state)

    assert result["execution_status"] == "failed"
    assert "Condition field is required" in result["errors"][0]


def test_condition_true_branch_executes_false_branch_skipped(monkeypatch) -> None:
    class DummyAgent:
        def __init__(self):
            self.executed_nodes: list[str] = []

        def execute(self, state):
            self.executed_nodes.append(state["current_node"])
            state.setdefault("execution_log", []).append("dummy executed")
            return state

    dummy_agent = DummyAgent()

    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Condition":
            return ConditionAgent()
        if node_type == "Send Email":
            return dummy_agent
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-cond-true",
        "nodes": [
            {"id": "condition1", "data": {"kind": "condition", "field": "email_subject", "operator": "contains", "value": "URGENT"}},
            {"id": "true_target", "data": {"kind": "send-email"}},
            {"id": "false_target", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "condition1", "sourceHandle": "true", "target": "true_target"},
            {"source": "condition1", "sourceHandle": "false", "target": "false_target"},
        ],
    }
    state = make_state("condition1", workflow, {"email_subject": "This is URGENT"})

    graph = builder.build_graph(workflow)
    final_state = graph.invoke(state)

    assert "true_target" in dummy_agent.executed_nodes
    assert "false_target" not in dummy_agent.executed_nodes
    assert final_state["condition_result"] is True


def test_condition_false_branch_executes_true_branch_skipped(monkeypatch) -> None:
    class DummyAgent:
        def __init__(self):
            self.executed_nodes: list[str] = []

        def execute(self, state):
            self.executed_nodes.append(state["current_node"])
            state.setdefault("execution_log", []).append("dummy executed")
            return state

    dummy_agent = DummyAgent()

    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Condition":
            return ConditionAgent()
        if node_type == "Send Email":
            return dummy_agent
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-cond-false",
        "nodes": [
            {"id": "condition1", "data": {"kind": "condition", "field": "email_subject", "operator": "contains", "value": "URGENT"}},
            {"id": "true_target", "data": {"kind": "send-email"}},
            {"id": "false_target", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "condition1", "sourceHandle": "true", "target": "true_target"},
            {"source": "condition1", "sourceHandle": "false", "target": "false_target"},
        ],
    }
    state = make_state("condition1", workflow, {"email_subject": "No match"})

    graph = builder.build_graph(workflow)
    final_state = graph.invoke(state)

    assert "true_target" not in dummy_agent.executed_nodes
    assert "false_target" in dummy_agent.executed_nodes
    assert final_state["condition_result"] is False


def test_condition_skips_on_no_messages(monkeypatch) -> None:
    class DummyAgent:
        def __init__(self):
            self.called = False

        def execute(self, state):
            self.called = True
            state.setdefault("execution_log", []).append("dummy executed")
            return state

    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Email Trigger":
            return EmailTriggerAgent()
        if node_type == "Condition":
            return ConditionAgent()
        if node_type == "Send Email":
            return DummyAgent()
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    monkeypatch.setattr(EmailTriggerAgent, "_fetch_emails", lambda self, cfg: [])

    workflow = {
        "workflow_id": "wf-no-messages-condition",
        "nodes": [
            {"id": "email1", "data": {"kind": "email-trigger"}},
            {"id": "condition1", "data": {"kind": "condition", "field": "email_subject", "operator": "contains", "value": "URGENT"}},
            {"id": "true_target", "data": {"kind": "send-email"}},
            {"id": "false_target", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "email1", "target": "condition1"},
            {"source": "condition1", "sourceHandle": "true", "target": "true_target"},
            {"source": "condition1", "sourceHandle": "false", "target": "false_target"},
        ],
    }
    state = make_state("email1", workflow)

    graph = builder.build_graph(workflow)
    final_state = graph.invoke(state)

    assert final_state["execution_status"] == "no_messages"
    assert all("dummy executed" not in entry for entry in final_state["execution_log"])


def test_condition_unselected_branch_is_not_failed(monkeypatch) -> None:
    class DummyAgent:
        def __init__(self):
            self.called = False

        def execute(self, state):
            self.called = True
            state.setdefault("execution_log", []).append("dummy executed")
            state["execution_status"] = "completed"
            return state

    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Condition":
            return ConditionAgent()
        if node_type == "Send Email":
            return DummyAgent()
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-monitor-condition",
        "nodes": [
            {"id": "condition1", "data": {"kind": "condition", "field": "email_subject", "operator": "equals", "value": "URGENT"}},
            {"id": "true_target", "data": {"kind": "send-email"}},
            {"id": "false_target", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "condition1", "sourceHandle": "true", "target": "true_target"},
            {"source": "condition1", "sourceHandle": "false", "target": "false_target"},
        ],
    }
    state = make_state("condition1", workflow, {"email_subject": "URGENT"})

    graph = builder.build_graph(workflow)
    final_state = graph.invoke(state)

    assert final_state["execution_status"] == "completed"
    assert final_state["condition_result"] is True
    assert "errors" not in final_state

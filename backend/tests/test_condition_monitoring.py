import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.condition_agent import ConditionAgent
from agents.supervisor import SupervisorAgent
from graph.graph_builder import GraphBuilder


class DummyLLM:
    def __init__(self, name: str) -> None:
        self.name = name
        self.called = False

    def execute(self, state):
        self.called = True
        state.setdefault("execution_log", []).append(f"{self.name} executed")
        state["execution_status"] = "completed"
        return state


def test_condition_true_branch_monitoring(monkeypatch) -> None:
    dummy_llm = DummyLLM("Urgent Handler")
    dummy_llm_false = DummyLLM("Normal Handler")

    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Condition":
            return ConditionAgent()
        if node_type == "LLM":
            return dummy_llm if not dummy_llm.called else dummy_llm_false
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    workflow = {
        "workflow_id": "wf-condition-true-monitor",
        "nodes": [
            {"id": "condition1", "data": {"kind": "condition", "label": "Condition", "field": "email_subject", "operator": "contains", "value": "URGENT"}},
            {"id": "true_target", "data": {"kind": "llm", "label": "Urgent Handler"}},
            {"id": "false_target", "data": {"kind": "llm", "label": "Normal Handler"}},
        ],
        "edges": [
            {"source": "condition1", "sourceHandle": "true", "target": "true_target"},
            {"source": "condition1", "sourceHandle": "false", "target": "false_target"},
        ],
    }
    state = {
        "workflow_id": workflow["workflow_id"],
        "current_node": "condition1",
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow,
        "email_subject": "SentinelMesh Condition Test URGENT",
    }

    graph = GraphBuilder().build_graph(workflow)
    final_state = graph.invoke(state)
    final_state = SupervisorAgent().execute(final_state)

    assert final_state["condition_result"] is True
    assert dummy_llm.called is True
    assert final_state["completed_stages"] == ["Condition", "Urgent Handler"]
    assert "Normal Handler" not in final_state["completed_stages"]
    assert "Normal Handler" in final_state["skipped_stages"]


def test_condition_false_branch_monitoring(monkeypatch) -> None:
    dummy_llm = DummyLLM("Urgent Handler")
    dummy_llm_false = DummyLLM("Normal Handler")

    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Condition":
            return ConditionAgent()
        if node_type == "LLM":
            return dummy_llm_false if not dummy_llm_false.called else dummy_llm
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    workflow = {
        "workflow_id": "wf-condition-false-monitor",
        "nodes": [
            {"id": "condition1", "data": {"kind": "condition", "label": "Condition", "field": "email_subject", "operator": "contains", "value": "URGENT"}},
            {"id": "true_target", "data": {"kind": "llm", "label": "Urgent Handler"}},
            {"id": "false_target", "data": {"kind": "llm", "label": "Normal Handler"}},
        ],
        "edges": [
            {"source": "condition1", "sourceHandle": "true", "target": "true_target"},
            {"source": "condition1", "sourceHandle": "false", "target": "false_target"},
        ],
    }
    state = {
        "workflow_id": workflow["workflow_id"],
        "current_node": "condition1",
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow,
        "email_subject": "Routine status update",
    }

    graph = GraphBuilder().build_graph(workflow)
    final_state = graph.invoke(state)
    final_state = SupervisorAgent().execute(final_state)

    assert final_state["condition_result"] is False
    assert dummy_llm_false.called is True
    assert final_state["completed_stages"] == ["Condition", "Normal Handler"]
    assert "Urgent Handler" not in final_state["completed_stages"]
    assert "Urgent Handler" in final_state["skipped_stages"]


def test_condition_branch_monitoring_uses_unique_node_ids(monkeypatch) -> None:
    workflow = {
        "workflow_id": "wf-condition-branch-monitor",
        "nodes": [
            {"id": "email-trigger-1", "data": {"kind": "email-trigger", "label": "Email Trigger"}},
            {"id": "extractor-1", "data": {"kind": "extractor", "label": "Extractor"}},
            {"id": "condition-1", "data": {"kind": "condition", "label": "Condition", "field": "urgency", "operator": "equals", "value": "immediate"}},
            {"id": "critical-handler-1", "data": {"kind": "llm", "label": "Critical Handler"}},
            {"id": "normal-handler-1", "data": {"kind": "llm", "label": "Normal Handler"}},
        ],
        "edges": [
            {"source": "email-trigger-1", "target": "extractor-1"},
            {"source": "extractor-1", "target": "condition-1"},
            {"source": "condition-1", "sourceHandle": "true", "target": "critical-handler-1"},
            {"source": "condition-1", "sourceHandle": "false", "target": "normal-handler-1"},
        ],
    }

    state = {
        "workflow_id": workflow["workflow_id"],
        "current_node": "condition-1",
        "execution_status": "completed",
        "execution_log": [],
        "workflow_data": workflow,
        "condition_result": True,
        "executed_nodes": ["email-trigger-1", "extractor-1", "condition-1", "critical-handler-1"],
        "skipped_nodes": ["normal-handler-1"],
        "urgency": "immediate",
    }

    final_state = SupervisorAgent().execute(state)

    assert final_state["completed_stages"] == ["Email Trigger", "Extractor", "Condition", "Critical Handler"]
    assert final_state["skipped_stages"] == ["Normal Handler"]
    assert final_state["failed_stages"] == []
    assert len(final_state["completed_stages"]) + len(final_state["skipped_stages"]) + len(final_state["failed_stages"]) == 5
    assert final_state["completed_stages"].count("Critical Handler") == 1
    assert final_state["skipped_stages"].count("Normal Handler") == 1

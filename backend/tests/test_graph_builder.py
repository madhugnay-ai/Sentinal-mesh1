import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from graph.graph_builder import GraphBuilder


def test_valid_workflow_builds_and_executes() -> None:
    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-123",
        "nodes": [
            {"id": "start", "type": "start"},
            {"id": "end", "type": "end"},
        ],
        "edges": [{"source": "start", "target": "end"}],
    }

    graph = builder.build_graph(workflow)
    result = builder.execute_workflow(workflow)

    assert graph is not None
    assert result["status"] == "completed"
    assert result["visited_nodes"] == ["start", "end"]
    assert len(result["execution_log"]) == 2


def test_empty_workflow_returns_error() -> None:
    builder = GraphBuilder()
    result = builder.execute_workflow({})

    assert result["status"] == "error"
    assert any("empty" in error.lower() for error in result["errors"])


def test_invalid_edge_returns_error() -> None:
    builder = GraphBuilder()
    workflow = {
        "nodes": [{"id": "start", "type": "start"}],
        "edges": [{"source": "start", "target": "missing"}],
    }

    result = builder.execute_workflow(workflow)

    assert result["status"] == "error"
    assert any("invalid edge" in error.lower() for error in result["errors"])


def test_multiple_connected_nodes_are_traversed() -> None:
    builder = GraphBuilder()
    workflow = {
        "nodes": [
            {"id": "a", "type": "step"},
            {"id": "b", "type": "step"},
            {"id": "c", "type": "step"},
        ],
        "edges": [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
        ],
    }

    result = builder.execute_workflow(workflow)

    assert result["status"] == "completed"
    assert result["visited_nodes"] == ["a", "b", "c"]


def test_graph_compilation_is_supported() -> None:
    builder = GraphBuilder()
    workflow = {
        "nodes": [{"id": "only", "type": "step"}],
        "edges": [],
    }

    compiled_graph = builder.build_graph(workflow)

    assert compiled_graph is not None
    assert hasattr(compiled_graph, "invoke")


def test_node_exception_is_captured_as_standardized_failure(monkeypatch) -> None:
    class FailingAgent:
        def execute(self, state):
            raise RuntimeError("provider timeout")

    monkeypatch.setattr(AgentRegistry, "get_agent", lambda self, node_type: FailingAgent())

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-failure-capture",
        "nodes": [{"id": "fail-node", "type": "failing-step", "data": {"kind": "failing-step"}}],
        "edges": [],
    }

    graph = builder.build_graph(workflow)
    result = graph.invoke({
        "workflow_id": "wf-failure-capture",
        "current_node": None,
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow,
    })

    assert result["execution_status"] == "failed"
    assert result["failed_node_ids"] == ["fail-node"]
    assert result["failure_context"]["failed_node_id"] == "fail-node"
    assert result["failure_context"]["failure_message"] == "provider timeout"
    assert result["failure_context"]["failure_error_type"] == "RuntimeError"

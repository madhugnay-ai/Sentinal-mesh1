import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.requirement_validation import RequirementValidationAgent
from constants.node_types import REQUIREMENT_VALIDATION
from graph.graph_builder import GraphBuilder
from graph.state import WorkflowState


def test_valid_workflow_is_validated() -> None:
    agent = RequirementValidationAgent()
    state: WorkflowState = {
        "workflow_id": "wf-1",
        "workflow_data": {
            "nodes": [{"id": "start"}, {"id": "end"}],
            "edges": [{"source": "start", "target": "end"}],
        },
    }

    result = agent(state)

    assert result["execution_status"] == "validated"
    assert result["validation_passed"] is True
    assert any("Requirement validation passed" in entry for entry in result["execution_log"])


def test_empty_workflow_fails_validation() -> None:
    agent = RequirementValidationAgent()
    state: WorkflowState = {"workflow_id": "wf-2", "workflow_data": {}}

    result = agent(state)

    assert result["execution_status"] == "failed"
    assert result["validation_passed"] is False
    assert result["errors"]


def test_duplicate_node_ids_fail_validation() -> None:
    agent = RequirementValidationAgent()
    state: WorkflowState = {
        "workflow_id": "wf-3",
        "workflow_data": {
            "nodes": [{"id": "dup"}, {"id": "dup"}],
            "edges": [],
        },
    }

    result = agent(state)

    assert any("unique" in error.lower() for error in result["errors"])


def test_invalid_edge_references_fail_validation() -> None:
    agent = RequirementValidationAgent()
    state: WorkflowState = {
        "workflow_id": "wf-4",
        "workflow_data": {
            "nodes": [{"id": "start"}],
            "edges": [{"source": "start", "target": "missing"}],
        },
    }

    result = agent(state)

    assert any("invalid edge" in error.lower() for error in result["errors"])


def test_missing_entry_node_fails_validation() -> None:
    agent = RequirementValidationAgent()
    state: WorkflowState = {
        "workflow_id": "wf-5",
        "workflow_data": {
            "nodes": [],
            "edges": [],
        },
    }

    result = agent(state)

    assert any("entry node" in error.lower() for error in result["errors"])


def test_graph_builder_invokes_requirement_validation_agent() -> None:
    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-6",
        "nodes": [{"id": "req", "type": REQUIREMENT_VALIDATION}],
        "edges": [],
    }

    result = builder.execute_workflow(workflow)

    assert result["status"] == "completed"
    assert result["execution_log"]
    assert any("Requirement validation passed" in entry for entry in result["execution_log"])

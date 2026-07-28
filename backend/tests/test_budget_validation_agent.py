import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.budget_validation import BudgetValidationAgent
from constants.node_types import BUDGET_VALIDATION
from graph.graph_builder import GraphBuilder
from graph.state import WorkflowState


def test_budget_sufficient() -> None:
    agent = BudgetValidationAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Laptop", "quantity": 1}],
            "available_budget": 100000,
        },
        "selected_vendor": {"item": "Laptop", "price": 65000},
    }

    result = agent.execute(state)

    assert result["budget_validation_passed"] is True
    assert result["budget_remaining"] == 35000
    assert result["execution_status"] == "validated"


def test_budget_exceeded() -> None:
    agent = BudgetValidationAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Laptop", "quantity": 2}],
            "available_budget": 100000,
        },
        "selected_vendor": {"item": "Laptop", "price": 65000},
    }

    result = agent.execute(state)

    assert result["budget_validation_passed"] is False
    assert result["budget_remaining"] == -30000
    assert result["execution_status"] == "failed"


def test_exact_budget_match() -> None:
    agent = BudgetValidationAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Laptop", "quantity": 1}],
            "available_budget": 65000,
        },
        "selected_vendor": {"item": "Laptop", "price": 65000},
    }

    result = agent.execute(state)

    assert result["budget_validation_passed"] is True
    assert result["budget_remaining"] == 0


def test_missing_vendor() -> None:
    agent = BudgetValidationAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Laptop", "quantity": 1}],
            "available_budget": 100000,
        },
    }

    result = agent.execute(state)

    assert result["budget_validation_passed"] is False
    assert result["execution_status"] == "failed"
    assert result["errors"]


def test_missing_available_budget() -> None:
    agent = BudgetValidationAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Laptop", "quantity": 1}],
        },
        "selected_vendor": {"item": "Laptop", "price": 65000},
    }

    result = agent.execute(state)

    assert result["budget_validation_passed"] is False
    assert result["execution_status"] == "failed"
    assert result["errors"]


def test_graph_builder_executes_budget_validation_agent_through_registry() -> None:
    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-budget",
        "nodes": [{"id": "budget", "type": BUDGET_VALIDATION}],
        "edges": [],
        "requested_items": [{"item": "Laptop", "quantity": 1}],
        "available_budget": 100000,
        "selected_vendor": {"item": "Laptop", "price": 65000},
    }

    result = builder.execute_workflow(workflow)

    assert result["status"] == "completed"
    assert result["execution_log"]
    assert any("Budget validation" in entry for entry in result["execution_log"])

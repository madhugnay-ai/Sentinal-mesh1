import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.supervisor import SupervisorAgent
from constants import node_types
from graph.state import WorkflowState


def test_healthy_workflow_is_marked_healthy() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "completed",
        "execution_log": ["Requirement validation passed"],
        "errors": [],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": True,
        "approval_status": "Approved",
        "purchase_order_generated": True,
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Healthy"
    assert node_types.REQUIREMENT_VALIDATION in result["completed_stages"]
    assert node_types.PURCHASE_ORDER in result["completed_stages"]
    assert result["failed_stages"] == []
    assert result["skipped_stages"] == []
    assert result["workflow_summary"]
    assert result["supervisor_timestamp"]
    assert any("Workflow health: Healthy" in entry for entry in result["execution_log"])


def test_warning_workflow_is_marked_warning() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "pending_manager_approval",
        "execution_log": ["Waiting for manager approval"],
        "errors": [],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": True,
        "approval_status": "Pending Manager Approval",
        "purchase_order_generated": False,
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Warning"
    assert node_types.PURCHASE_ORDER in result["skipped_stages"]
    assert result["failed_stages"] == []


def test_failed_workflow_is_marked_failed() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "failed",
        "execution_log": ["Budget validation failed"],
        "errors": ["Budget validation failed"],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": False,
        "approval_status": "Rejected",
        "purchase_order_generated": False,
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Failed"
    assert node_types.BUDGET_VALIDATION in result["failed_stages"]
    assert node_types.APPROVAL in result["failed_stages"]


def test_empty_workflow_state_is_handled_gracefully() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {}

    result = agent.execute(state)

    assert result["workflow_health"] == "Warning"
    assert result["completed_stages"] == []
    assert result["failed_stages"] == []
    assert result["skipped_stages"]


def test_missing_optional_fields_are_treated_as_skipped() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "completed",
        "errors": [],
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Warning"
    assert result["skipped_stages"]
    assert node_types.REQUIREMENT_VALIDATION in result["skipped_stages"]


def test_email_trigger_only_workflow_is_marked_healthy_without_procurement_stages() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "received",
        "execution_log": ["Email trigger fetched 5 email(s)."],
        "errors": [],
        "workflow_data": {
            "nodes": [
                {"id": "email-1", "type": "email-trigger", "data": {"kind": "email-trigger"}},
            ],
            "edges": [],
        },
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Healthy"
    assert result["completed_stages"] == ["email-1"]
    assert result["failed_stages"] == []
    assert result["skipped_stages"] == []
    assert result["workflow_summary"].startswith("Workflow health: Healthy")


def test_successful_email_trigger_only_workflow_reports_one_completed_stage() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "received",
        "execution_log": ["Email trigger fetched 5 email(s)."],
        "errors": [],
        "workflow_data": {
            "nodes": [
                {"id": "email-1", "type": "email-trigger", "data": {"kind": "email-trigger", "label": "Email Trigger"}},
            ],
            "edges": [],
        },
        "executed_nodes": ["email-1"],
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Healthy"
    assert result["completed_stages"] == ["Email Trigger"]
    assert result["failed_stages"] == []
    assert result["skipped_stages"] == []


def test_successful_multi_node_generic_workflow_reports_all_completed_stages() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "completed",
        "execution_log": ["Email trigger fetched 2 email(s).", "LLM response produced."],
        "errors": [],
        "workflow_data": {
            "nodes": [
                {"id": "email-1", "type": "email-trigger", "data": {"kind": "email-trigger", "label": "Email Trigger"}},
                {"id": "llm-1", "type": "llm", "data": {"kind": "llm", "label": "LLM"}},
            ],
            "edges": [],
        },
        "executed_nodes": ["email-1", "llm-1"],
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Healthy"
    assert result["completed_stages"] == ["Email Trigger", "LLM"]
    assert result["failed_stages"] == []
    assert result["skipped_stages"] == []


def test_successful_downstream_node_is_reported_in_completed_stages() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "completed",
        "execution_log": ["Email trigger selected 1 email for processing.", "Extractor completed."],
        "errors": [],
        "workflow_data": {
            "nodes": [
                {"id": "email-1", "type": "email-trigger", "data": {"kind": "email-trigger", "label": "Email Trigger"}},
                {"id": "extractor-1", "type": "extractor", "data": {"kind": "extractor"}},
            ],
            "edges": [],
        },
        "executed_nodes": ["email-1", "extractor-1"],
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Healthy"
    assert result["completed_stages"] == ["Email Trigger", "Extractor"]
    assert result["failed_stages"] == []
    assert result["skipped_stages"] == []


def test_failed_generic_node_reports_failed_stage_and_progress() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "failed",
        "execution_log": ["Email trigger fetched 1 email(s)."],
        "errors": ["LLM node failed"],
        "workflow_data": {
            "nodes": [
                {"id": "email-1", "type": "email-trigger", "data": {"kind": "email-trigger", "label": "Email Trigger"}},
                {"id": "llm-1", "type": "llm", "data": {"kind": "llm", "label": "LLM"}},
            ],
            "edges": [],
        },
        "executed_nodes": ["email-1", "llm-1"],
        "current_node": "llm-1",
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Failed"
    assert result["completed_stages"] == ["Email Trigger"]
    assert result["failed_stages"] == ["LLM"]
    assert result["skipped_stages"] == []


def test_procurement_workflow_still_reports_procurement_stages() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "completed",
        "execution_log": ["Requirement validation passed"],
        "errors": [],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": True,
        "approval_status": "Approved",
        "purchase_order_generated": True,
        "workflow_data": {
            "nodes": [
                {"id": "req", "type": "Requirement Validation", "data": {"kind": "requirement-validation"}},
                {"id": "inv", "type": "Inventory", "data": {"kind": "inventory"}},
                {"id": "vendor", "type": "Vendor Selection", "data": {"kind": "vendor-selection"}},
                {"id": "budget", "type": "Budget Validation", "data": {"kind": "budget-validation"}},
                {"id": "approval", "type": "Approval", "data": {"kind": "approval"}},
                {"id": "po", "type": "Purchase Order", "data": {"kind": "purchase-order"}},
            ],
            "edges": [],
        },
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Healthy"
    assert node_types.REQUIREMENT_VALIDATION in result["completed_stages"]
    assert node_types.PURCHASE_ORDER in result["completed_stages"]
    assert result["failed_stages"] == []
    assert result["skipped_stages"] == []


def test_supervisor_generates_diagnosis_from_failure_context() -> None:
    agent = SupervisorAgent()
    state: WorkflowState = {
        "execution_status": "failed",
        "execution_log": ["Node execution failed"],
        "errors": ["provider timeout"],
        "current_node": "llm-1",
        "workflow_data": {
            "nodes": [
                {"id": "llm-1", "type": "LLM", "data": {"kind": "llm", "label": "LLM"}},
            ],
            "edges": [],
        },
        "failure_context": {
            "failed_node_id": "llm-1",
            "failed_node_type": "LLM",
            "failure_message": "provider timeout",
            "failure_error_type": "TimeoutError",
            "execution_timestamp": "2026-01-01T00:00:00Z",
        },
    }

    result = agent.execute(state)

    assert result["workflow_health"] == "Failed"
    assert result["supervisor_diagnosis"]
    assert "llm-1" in result["supervisor_diagnosis"]
    assert "provider timeout" in result["supervisor_diagnosis"]


def test_agent_registry_invokes_supervisor_agent() -> None:
    registry = AgentRegistry()
    agent = registry.get_agent(node_types.SUPERVISOR)

    assert agent is not None
    assert agent.__class__.__name__ == "SupervisorAgent"

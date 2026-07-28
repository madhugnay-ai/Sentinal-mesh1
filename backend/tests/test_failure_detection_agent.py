import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.failure_detection import FailureDetectionAgent
from constants import node_types
from graph.state import WorkflowState


def test_healthy_workflow_has_no_failure() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Healthy",
        "execution_status": "completed",
        "errors": [],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": True,
        "approval_status": "Approved",
        "purchase_order_generated": True,
        "execution_log": ["Workflow health: Healthy"],
        "workflow_summary": "Workflow health: Healthy",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is False
    assert result["failure_category"] == "None"
    assert result["failure_severity"] == "Low"
    assert result["recoverable"] is True
    assert result["failure_summary"] == "No failures detected."


def test_validation_failure_is_classified() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Failed",
        "execution_status": "failed",
        "errors": ["Workflow does not contain any valid node IDs."],
        "validation_passed": False,
        "inventory_checked": False,
        "vendor_selection_completed": False,
        "budget_validation_passed": False,
        "approval_status": None,
        "purchase_order_generated": False,
        "execution_log": ["Requirement validation failed"],
        "workflow_summary": "Workflow health: Failed",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Validation Failure"
    assert result["failure_severity"] == "Critical"
    assert result["recoverable"] is False
    assert result["failure_details"]["category"] == "Validation Failure"


def test_inventory_failure_is_classified() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Warning",
        "execution_status": "failed",
        "errors": ["Inventory unavailable"],
        "validation_passed": True,
        "inventory_checked": False,
        "vendor_selection_completed": False,
        "budget_validation_passed": True,
        "approval_status": "Pending Manager Approval",
        "purchase_order_generated": False,
        "execution_log": ["Inventory check failed"],
        "workflow_summary": "Workflow health: Warning",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Inventory Failure"
    assert result["failure_severity"] == "High"
    assert result["recoverable"] is True
    assert result["failure_details"]["recommended_next_step"] == "Retry Inventory"


def test_vendor_selection_failure_is_classified() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Warning",
        "execution_status": "failed",
        "errors": ["Vendor selection failed"],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": False,
        "budget_validation_passed": True,
        "approval_status": "Pending Manager Approval",
        "purchase_order_generated": False,
        "execution_log": ["Vendor selection failed"],
        "workflow_summary": "Workflow health: Warning",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Vendor Selection Failure"
    assert result["failure_severity"] == "High"
    assert result["recoverable"] is True
    assert result["failure_details"]["recommended_next_step"] == "Select Alternate Vendor"


def test_budget_failure_is_classified() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Warning",
        "execution_status": "failed",
        "errors": ["Budget exceeded"],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": False,
        "approval_status": "Rejected",
        "purchase_order_generated": False,
        "execution_log": ["Budget validation failed"],
        "workflow_summary": "Workflow health: Warning",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Budget Failure"
    assert result["failure_severity"] == "High"
    assert result["recoverable"] is True
    assert result["failure_details"]["recommended_next_step"] == "Increase Budget"


def test_approval_failure_is_classified() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Warning",
        "execution_status": "pending_manager_approval",
        "errors": [],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": True,
        "approval_status": "Pending Manager Approval",
        "purchase_order_generated": False,
        "execution_log": ["Pending manager approval"],
        "workflow_summary": "Workflow health: Warning",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Approval Failure"
    assert result["failure_severity"] == "Medium"
    assert result["recoverable"] is True
    assert result["failure_details"]["recommended_next_step"] == "Request Manual Approval"


def test_purchase_order_failure_is_classified() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Warning",
        "execution_status": "completed",
        "errors": [],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": True,
        "approval_status": "Approved",
        "purchase_order_generated": False,
        "execution_log": ["Approval completed"],
        "workflow_summary": "Workflow health: Warning",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Purchase Order Failure"
    assert result["failure_severity"] == "High"
    assert result["recoverable"] is True
    assert result["failure_details"]["recommended_next_step"] == "Regenerate Purchase Order"


def test_unknown_failure_is_classified() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Warning",
        "execution_status": "running",
        "errors": ["Unknown issue"],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": True,
        "approval_status": "Approved",
        "purchase_order_generated": True,
        "execution_log": ["Unknown issue"],
        "workflow_summary": "Workflow health: Warning",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Unknown Failure"
    assert result["failure_severity"] == "Medium"
    assert result["recoverable"] is False
    assert result["failure_details"]["recommended_next_step"] == "Escalate Workflow"


def test_critical_workflow_failure_is_classified() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Failed",
        "execution_status": "failed",
        "errors": ["Critical execution failure"],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": True,
        "budget_validation_passed": True,
        "approval_status": "Rejected",
        "purchase_order_generated": False,
        "execution_log": ["Critical execution failure"],
        "workflow_summary": "Workflow health: Failed",
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Workflow Failure"
    assert result["failure_severity"] == "Critical"
    assert result["recoverable"] is False
    assert result["failure_details"]["recommended_next_step"] == "Escalate Workflow"


def test_recoverable_failure_flags_true() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Warning",
        "execution_status": "failed",
        "errors": ["Vendor selection failed"],
        "validation_passed": True,
        "inventory_checked": True,
        "vendor_selection_completed": False,
        "budget_validation_passed": True,
        "approval_status": "Pending Manager Approval",
        "purchase_order_generated": False,
        "execution_log": ["Vendor selection failed"],
        "workflow_summary": "Workflow health: Warning",
    }

    result = agent.execute(state)

    assert result["recoverable"] is True


def test_non_recoverable_failure_flags_false() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Failed",
        "execution_status": "failed",
        "errors": ["Invalid workflow"],
        "validation_passed": False,
        "inventory_checked": False,
        "vendor_selection_completed": False,
        "budget_validation_passed": False,
        "approval_status": None,
        "purchase_order_generated": False,
        "execution_log": ["Invalid workflow"],
        "workflow_summary": "Workflow health: Failed",
    }

    result = agent.execute(state)

    assert result["recoverable"] is False


def test_generic_failure_without_procurement_nodes_is_classified_as_workflow_failure() -> None:
    agent = FailureDetectionAgent()
    state: WorkflowState = {
        "workflow_health": "Failed",
        "execution_status": "failed",
        "errors": ["Email trigger failed"],
        "validation_passed": None,
        "inventory_checked": None,
        "vendor_selection_completed": None,
        "budget_validation_passed": None,
        "approval_status": None,
        "purchase_order_generated": None,
        "execution_log": ["Email trigger failed"],
        "workflow_summary": "Workflow health: Failed",
        "workflow_data": {
            "nodes": [{"id": "email-1", "type": "email-trigger", "data": {"kind": "email-trigger"}}],
            "edges": [],
        },
    }

    result = agent.execute(state)

    assert result["failure_detected"] is True
    assert result["failure_category"] == "Workflow Failure"
    assert result["failure_severity"] == "Medium"
    assert result["failure_details"]["failed_stage"] == "Workflow"


def test_agent_registry_invokes_failure_detection_agent() -> None:
    registry = AgentRegistry()
    agent = registry.get_agent(node_types.FAILURE_DETECTION)

    assert agent is not None
    assert agent.__class__.__name__ == "FailureDetectionAgent"

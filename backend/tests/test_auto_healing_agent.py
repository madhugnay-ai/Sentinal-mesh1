import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.auto_healing import AutoHealingAgent
from constants import node_types
from graph.state import WorkflowState


def test_inventory_recovery_is_recommended() -> None:
    agent = AutoHealingAgent()
    state: WorkflowState = {
        "failure_detected": True,
        "failure_category": "Inventory Failure",
        "failure_severity": "High",
        "recoverable": True,
        "recommended_resolution": "Switch to alternate warehouse",
        "incident_matches": [{"incident_id": "INC-001"}],
        "failure_details": {"recommended_next_step": "Retry Inventory"},
        "execution_log": ["Failure detected: Inventory Failure"],
    }

    result = agent.execute(state)

    assert result["healing_attempted"] is True
    assert result["healing_strategy"] == "Retry Inventory Lookup"
    assert result["healing_status"] == "Recommended"
    assert result["next_recommended_action"] == "Retry Inventory Lookup"


def test_vendor_recovery_is_recommended() -> None:
    agent = AutoHealingAgent()
    state: WorkflowState = {
        "failure_detected": True,
        "failure_category": "Vendor Selection Failure",
        "failure_severity": "High",
        "recoverable": True,
        "recommended_resolution": "Select alternate vendor",
        "incident_matches": [{"incident_id": "INC-004"}],
        "failure_details": {"recommended_next_step": "Select Alternate Vendor"},
        "execution_log": ["Failure detected: Vendor Selection Failure"],
    }

    result = agent.execute(state)

    assert result["healing_strategy"] == "Select Alternate Vendor"
    assert result["healing_status"] == "Recommended"


def test_budget_recovery_is_recommended() -> None:
    agent = AutoHealingAgent()
    state: WorkflowState = {
        "failure_detected": True,
        "failure_category": "Budget Failure",
        "failure_severity": "High",
        "recoverable": True,
        "recommended_resolution": "Increase budget or narrow the requested scope",
        "incident_matches": [{"incident_id": "INC-006"}],
        "failure_details": {"recommended_next_step": "Increase Budget"},
        "execution_log": ["Failure detected: Budget Failure"],
    }

    result = agent.execute(state)

    assert result["healing_strategy"] == "Increase Budget Request"
    assert result["healing_status"] == "Recommended"


def test_approval_recovery_is_recommended() -> None:
    agent = AutoHealingAgent()
    state: WorkflowState = {
        "failure_detected": True,
        "failure_category": "Approval Failure",
        "failure_severity": "Medium",
        "recoverable": True,
        "recommended_resolution": "Request manual approval",
        "incident_matches": [{"incident_id": "INC-008"}],
        "failure_details": {"recommended_next_step": "Request Manual Approval"},
        "execution_log": ["Failure detected: Approval Failure"],
    }

    result = agent.execute(state)

    assert result["healing_strategy"] == "Request Manual Approval"
    assert result["healing_status"] == "Recommended"


def test_purchase_order_recovery_is_recommended() -> None:
    agent = AutoHealingAgent()
    state: WorkflowState = {
        "failure_detected": True,
        "failure_category": "Purchase Order Failure",
        "failure_severity": "High",
        "recoverable": True,
        "recommended_resolution": "Regenerate purchase order",
        "incident_matches": [{"incident_id": "INC-009"}],
        "failure_details": {"recommended_next_step": "Regenerate Purchase Order"},
        "execution_log": ["Failure detected: Purchase Order Failure"],
    }

    result = agent.execute(state)

    assert result["healing_strategy"] == "Regenerate Purchase Order"
    assert result["healing_status"] == "Recommended"


def test_non_recoverable_workflow_is_escalated() -> None:
    agent = AutoHealingAgent()
    state: WorkflowState = {
        "failure_detected": True,
        "failure_category": "Validation Failure",
        "failure_severity": "Critical",
        "recoverable": False,
        "recommended_resolution": "Fix workflow definition before replay",
        "incident_matches": [{"incident_id": "INC-010"}],
        "failure_details": {"recommended_next_step": "Escalate Workflow"},
        "execution_log": ["Failure detected: Validation Failure"],
    }

    result = agent.execute(state)

    assert result["healing_attempted"] is False
    assert result["healing_strategy"] == "Escalate Workflow"
    assert result["healing_status"] == "Not Recommended"


def test_healthy_workflow_has_no_healing_needed() -> None:
    agent = AutoHealingAgent()
    state: WorkflowState = {
        "failure_detected": False,
        "failure_category": "None",
        "failure_severity": "Low",
        "recoverable": True,
        "recommended_resolution": "No known incident match found.",
        "incident_matches": [],
        "failure_details": {"recommended_next_step": "No Action"},
        "execution_log": ["No failures detected."],
    }

    result = agent.execute(state)

    assert result["healing_attempted"] is False
    assert result["healing_strategy"] == "No Recovery Needed"
    assert result["healing_status"] == "Not Required"
    assert result["next_recommended_action"] == "No Recovery Needed"


def test_no_failure_has_no_recovery() -> None:
    agent = AutoHealingAgent()
    state: WorkflowState = {
        "failure_detected": False,
        "failure_category": "None",
        "failure_severity": "Low",
        "recoverable": True,
        "recommended_resolution": "No known incident match found.",
        "incident_matches": [],
        "failure_details": {},
        "execution_log": ["No failures detected."],
    }

    result = agent.execute(state)

    assert result["healing_strategy"] == "No Recovery Needed"


def test_agent_registry_invokes_auto_healing_agent() -> None:
    registry = AgentRegistry()
    agent = registry.get_agent(node_types.AUTO_HEALING)

    assert agent is not None
    assert agent.__class__.__name__ == "AutoHealingAgent"

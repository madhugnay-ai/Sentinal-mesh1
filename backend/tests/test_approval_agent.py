import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.approval import ApprovalAgent
from constants.node_types import APPROVAL
from graph.state import WorkflowState


def test_auto_approval_below_threshold() -> None:
    agent = ApprovalAgent()
    state: WorkflowState = {
        "budget_validation_passed": True,
        "total_cost": 30000,
        "approval_threshold": 50000,
    }

    result = agent.execute(state)

    assert result["approval_status"] == "Approved"
    assert result["approved_by"] == "System"
    assert result["approval_reason"] == "Within auto-approval threshold."
    assert result["execution_status"] == "approved"
    assert result["approval_timestamp"]


def test_exact_threshold_approval() -> None:
    agent = ApprovalAgent()
    state: WorkflowState = {
        "budget_validation_passed": True,
        "total_cost": 50000,
        "approval_threshold": 50000,
    }

    result = agent.execute(state)

    assert result["approval_status"] == "Approved"
    assert result["approved_by"] == "System"


def test_pending_manager_approval() -> None:
    agent = ApprovalAgent()
    state: WorkflowState = {
        "budget_validation_passed": True,
        "total_cost": 75000,
        "approval_threshold": 50000,
    }

    result = agent.execute(state)

    assert result["approval_status"] == "Pending Manager Approval"
    assert result["approved_by"] is None
    assert result["approval_reason"] == "Exceeds auto-approval threshold."
    assert result["execution_status"] == "pending_manager_approval"


def test_budget_validation_failed() -> None:
    agent = ApprovalAgent()
    state: WorkflowState = {
        "budget_validation_passed": False,
        "total_cost": 30000,
        "approval_threshold": 50000,
    }

    result = agent.execute(state)

    assert result["approval_status"] == "Rejected"
    assert result["approved_by"] is None
    assert result["approval_reason"] == "Budget validation failed."
    assert result["execution_status"] == "rejected"


def test_missing_threshold_uses_default() -> None:
    agent = ApprovalAgent()
    state: WorkflowState = {
        "budget_validation_passed": True,
        "total_cost": 40000,
    }

    result = agent.execute(state)

    assert result["approval_status"] == "Approved"
    assert result["approval_threshold"] == 50000
    assert result["approved_by"] == "System"


def test_agent_registry_invokes_approval_agent() -> None:
    registry = AgentRegistry()
    agent = registry.get_agent(APPROVAL)

    assert agent is not None
    assert agent.__class__.__name__ == "ApprovalAgent"

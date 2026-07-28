import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.purchase_order import PurchaseOrderAgent
from constants.node_types import PURCHASE_ORDER
from graph.state import WorkflowState


def test_approved_workflow_generates_po() -> None:
    agent = PurchaseOrderAgent()
    state: WorkflowState = {
        "approval_status": "Approved",
        "selected_vendor": {"vendor_name": "Acme Supplies", "item": "Laptop", "price": 65000},
        "requested_items": [{"item": "Laptop", "quantity": 1}],
        "total_cost": 65000,
    }

    result = agent.execute(state)

    assert result["purchase_order_generated"] is True
    assert result["purchase_order"]["status"] == "Generated"
    assert result["purchase_order"]["vendor_name"] == "Acme Supplies"
    assert result["purchase_order_number"]
    assert result["execution_status"] == "generated"


def test_rejected_workflow_does_not_generate_po() -> None:
    agent = PurchaseOrderAgent()
    state: WorkflowState = {
        "approval_status": "Rejected",
        "selected_vendor": {"vendor_name": "Acme Supplies", "item": "Laptop", "price": 65000},
        "requested_items": [{"item": "Laptop", "quantity": 1}],
        "total_cost": 65000,
    }

    result = agent.execute(state)

    assert result["purchase_order_generated"] is False
    assert result["purchase_order"] is None
    assert result["execution_status"] == "failed"
    assert result["errors"]


def test_pending_approval_does_not_generate_po() -> None:
    agent = PurchaseOrderAgent()
    state: WorkflowState = {
        "approval_status": "Pending Manager Approval",
        "selected_vendor": {"vendor_name": "Acme Supplies", "item": "Laptop", "price": 65000},
        "requested_items": [{"item": "Laptop", "quantity": 1}],
        "total_cost": 65000,
    }

    result = agent.execute(state)

    assert result["purchase_order_generated"] is False
    assert result["purchase_order"] is None
    assert result["execution_status"] == "failed"


def test_missing_vendor() -> None:
    agent = PurchaseOrderAgent()
    state: WorkflowState = {
        "approval_status": "Approved",
        "requested_items": [{"item": "Laptop", "quantity": 1}],
        "total_cost": 65000,
    }

    result = agent.execute(state)

    assert result["purchase_order_generated"] is False
    assert result["execution_status"] == "failed"
    assert result["errors"]


def test_missing_items() -> None:
    agent = PurchaseOrderAgent()
    state: WorkflowState = {
        "approval_status": "Approved",
        "selected_vendor": {"vendor_name": "Acme Supplies", "item": "Laptop", "price": 65000},
        "total_cost": 65000,
    }

    result = agent.execute(state)

    assert result["purchase_order_generated"] is False
    assert result["execution_status"] == "failed"
    assert result["errors"]


def test_agent_registry_invokes_purchase_order_agent() -> None:
    registry = AgentRegistry()
    agent = registry.get_agent(PURCHASE_ORDER)

    assert agent is not None
    assert agent.__class__.__name__ == "PurchaseOrderAgent"

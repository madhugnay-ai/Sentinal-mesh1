import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.inventory import InventoryAgent
from constants.node_types import INVENTORY
from graph.graph_builder import GraphBuilder
from graph.state import WorkflowState


def test_item_available() -> None:
    agent = InventoryAgent()
    state: WorkflowState = {
        "workflow_data": {"requested_items": [{"item": "Laptop", "quantity": 5}]},
    }

    result = agent(state)

    assert result["inventory_checked"] is True
    assert result["inventory_result"][0]["availability_status"] == "available"
    assert result["execution_status"] == "validated"


def test_item_unavailable() -> None:
    agent = InventoryAgent()
    state: WorkflowState = {
        "workflow_data": {"requested_items": [{"item": "Laptop", "quantity": 30}]},
    }

    result = agent(state)

    assert result["inventory_result"][0]["availability_status"] == "insufficient"
    assert result["execution_status"] == "validated"


def test_unknown_item() -> None:
    agent = InventoryAgent()
    state: WorkflowState = {
        "workflow_data": {"requested_items": [{"item": "Unknown Item", "quantity": 1}]},
    }

    result = agent(state)

    assert result["inventory_result"][0]["available_quantity"] == 0
    assert result["inventory_result"][0]["availability_status"] == "insufficient"


def test_multiple_requested_items() -> None:
    agent = InventoryAgent()
    state: WorkflowState = {
        "workflow_data": {"requested_items": [{"item": "Laptop", "quantity": 2}, {"item": "Monitor", "quantity": 10}]},
    }

    result = agent(state)

    assert len(result["inventory_result"]) == 2
    assert result["inventory_result"][0]["item"] == "Laptop"
    assert result["inventory_result"][1]["item"] == "Monitor"


def test_graph_builder_invokes_inventory_agent() -> None:
    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-inventory",
        "nodes": [{"id": "inventory", "type": INVENTORY}],
        "edges": [],
        "requested_items": [{"item": "Keyboard", "quantity": 2}],
    }

    result = builder.execute_workflow(workflow)

    assert result["status"] == "completed"
    assert result["execution_log"]
    assert any("Inventory check completed" in entry for entry in result["execution_log"])

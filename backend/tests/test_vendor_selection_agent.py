import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.vendor_selection import VendorSelectionAgent
from constants.node_types import VENDOR_SELECTION
from graph.graph_builder import GraphBuilder
from graph.state import WorkflowState


def test_lowest_cost_strategy() -> None:
    agent = VendorSelectionAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Laptop"}],
            "vendor_strategy": "lowest_cost",
        },
    }

    result = agent(state)

    assert result["selected_vendor"]["vendor_name"] == "Vendor B"
    assert result["selected_vendor"]["selection_reason"] == "selected for lowest cost"


def test_fastest_delivery_strategy() -> None:
    agent = VendorSelectionAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Laptop"}],
            "vendor_strategy": "fastest_delivery",
        },
    }

    result = agent(state)

    assert result["selected_vendor"]["vendor_name"] == "Vendor A"
    assert result["selected_vendor"]["selection_reason"] == "selected for fastest delivery"


def test_best_rated_strategy() -> None:
    agent = VendorSelectionAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Laptop"}],
            "vendor_strategy": "best_rated",
        },
    }

    result = agent(state)

    assert result["selected_vendor"]["vendor_name"] == "Vendor A"
    assert result["selected_vendor"]["selection_reason"] == "selected for highest rating"


def test_unknown_item() -> None:
    agent = VendorSelectionAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Unknown Item"}],
            "vendor_strategy": "lowest_cost",
        },
    }

    result = agent(state)

    assert result["execution_status"] == "failed"
    assert result["errors"]


def test_multiple_vendors() -> None:
    agent = VendorSelectionAgent()
    state: WorkflowState = {
        "workflow_data": {
            "requested_items": [{"item": "Keyboard"}],
            "vendor_strategy": "lowest_cost",
        },
    }

    result = agent(state)

    assert result["selected_vendor"]["vendor_name"] == "Vendor E"


def test_graph_builder_invokes_vendor_selection_agent() -> None:
    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-vendor",
        "nodes": [{"id": "vendor", "type": VENDOR_SELECTION}],
        "edges": [],
        "requested_items": [{"item": "Laptop"}],
        "vendor_strategy": "lowest_cost",
    }

    result = builder.execute_workflow(workflow)

    assert result["status"] == "completed"
    assert result["execution_log"]
    assert any("Vendor selection completed" in entry for entry in result["execution_log"])

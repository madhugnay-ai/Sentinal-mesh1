from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from graph.state import WorkflowState


class InventoryAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def execute(self, state: WorkflowState) -> WorkflowState:
        workflow_data = state.get("workflow_data") or {}
        requested_items = workflow_data.get("requested_items") or []

        if not isinstance(requested_items, list) or not requested_items:
            state["execution_status"] = "failed"
            state["errors"] = ["No requested items were provided."]
            state.setdefault("execution_log", []).append("Inventory check failed: no requested items provided")
            state["inventory_checked"] = True
            return state

        mock_inventory: dict[str, int] = {
            "Laptop": 25,
            "Keyboard": 100,
            "Mouse": 150,
            "Monitor": 40,
            "Chair": 15,
        }

        results: list[dict[str, Any]] = []
        errors: list[str] = []

        for item in requested_items:
            if not isinstance(item, dict):
                errors.append("Each requested item must be an object.")
                continue

            item_name = item.get("item")
            quantity = item.get("quantity", 0)

            if not isinstance(item_name, str) or not item_name.strip():
                errors.append("Each requested item must include a valid item name.")
                continue

            if not isinstance(quantity, int) or quantity < 0:
                errors.append(f"Invalid quantity for {item_name}.")
                continue

            available_quantity = mock_inventory.get(item_name, 0)
            availability_status = "available" if available_quantity >= quantity else "insufficient"
            results.append(
                {
                    "item": item_name,
                    "requested_quantity": quantity,
                    "available_quantity": available_quantity,
                    "availability_status": availability_status,
                }
            )

        state["inventory_result"] = results
        state["inventory_checked"] = True

        if errors:
            state["execution_status"] = "failed"
            state["errors"] = errors
            state.setdefault("execution_log", []).append("Inventory check failed")
            return state

        state["execution_status"] = "validated"
        state.setdefault("execution_log", []).append("Inventory check completed")
        return state

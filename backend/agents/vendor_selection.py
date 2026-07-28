from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from graph.state import WorkflowState


class VendorSelectionAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def execute(self, state: WorkflowState) -> WorkflowState:
        workflow_data = state.get("workflow_data") or {}
        requested_items = workflow_data.get("requested_items") or []
        strategy = workflow_data.get("vendor_strategy") or "lowest_cost"

        if not isinstance(requested_items, list) or not requested_items:
            state["execution_status"] = "failed"
            state["errors"] = ["No requested items were provided."]
            state.setdefault("execution_log", []).append("Vendor selection failed: no requested items provided")
            state["vendor_selection_completed"] = True
            return state

        mock_catalog: dict[str, list[dict[str, Any]]] = {
            "Laptop": [
                {"vendor_id": "V1", "vendor_name": "Vendor A", "item": "Laptop", "price": 65000, "rating": 4.8, "delivery_days": 2},
                {"vendor_id": "V2", "vendor_name": "Vendor B", "item": "Laptop", "price": 63000, "rating": 4.5, "delivery_days": 5},
                {"vendor_id": "V3", "vendor_name": "Vendor C", "item": "Laptop", "price": 64000, "rating": 4.7, "delivery_days": 3},
            ],
            "Keyboard": [
                {"vendor_id": "V4", "vendor_name": "Vendor D", "item": "Keyboard", "price": 2500, "rating": 4.6, "delivery_days": 2},
                {"vendor_id": "V5", "vendor_name": "Vendor E", "item": "Keyboard", "price": 2200, "rating": 4.3, "delivery_days": 4},
            ],
            "Mouse": [
                {"vendor_id": "V6", "vendor_name": "Vendor F", "item": "Mouse", "price": 1800, "rating": 4.9, "delivery_days": 1},
                {"vendor_id": "V7", "vendor_name": "Vendor G", "item": "Mouse", "price": 1900, "rating": 4.4, "delivery_days": 3},
            ],
        }

        results: list[dict[str, Any]] = []
        errors: list[str] = []

        for item in requested_items:
            if not isinstance(item, dict):
                errors.append("Each requested item must be an object.")
                continue

            item_name = item.get("item")
            if not isinstance(item_name, str) or not item_name.strip():
                errors.append("Each requested item must include a valid item name.")
                continue

            vendors = mock_catalog.get(item_name)
            if not vendors:
                errors.append(f"No vendor catalog available for {item_name}.")
                continue

            if strategy == "fastest_delivery":
                selected_vendor = min(vendors, key=lambda vendor: vendor["delivery_days"])
                reason = "selected for fastest delivery"
            elif strategy == "best_rated":
                selected_vendor = max(vendors, key=lambda vendor: vendor["rating"])
                reason = "selected for highest rating"
            else:
                selected_vendor = min(vendors, key=lambda vendor: vendor["price"])
                reason = "selected for lowest cost"

            results.append(
                {
                    "item": item_name,
                    "vendor_name": selected_vendor["vendor_name"],
                    "price": selected_vendor["price"],
                    "delivery_days": selected_vendor["delivery_days"],
                    "rating": selected_vendor["rating"],
                    "selection_reason": reason,
                }
            )

        state["selected_vendor"] = results[0] if results else None
        state["vendor_selection_completed"] = True

        if errors:
            state["execution_status"] = "failed"
            state["errors"] = errors
            state.setdefault("execution_log", []).append("Vendor selection failed")
            return state

        state["execution_status"] = "validated"
        state.setdefault("execution_log", []).append("Vendor selection completed")
        return state

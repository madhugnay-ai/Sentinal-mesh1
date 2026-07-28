from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agents.base_agent import BaseAgent
from graph.state import WorkflowState


class PurchaseOrderAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def execute(self, state: WorkflowState) -> WorkflowState:
        approval_status = state.get("approval_status")
        selected_vendor = state.get("selected_vendor")
        requested_items = state.get("requested_items")
        total_cost = state.get("total_cost")

        if approval_status != "Approved":
            state["purchase_order_generated"] = False
            state["purchase_order"] = None
            state["purchase_order_number"] = None
            state["purchase_order_timestamp"] = None
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Purchase order not generated because approval status is {approval_status}."
            )
            state["errors"] = state.get("errors", []) + ["Purchase order requires an approved workflow."]
            return state

        errors: list[str] = []

        if not isinstance(selected_vendor, dict) or not selected_vendor.get("vendor_name"):
            errors.append("A valid selected vendor is required to generate a purchase order.")

        if not isinstance(requested_items, list) or not requested_items:
            errors.append("Requested items are required to generate a purchase order.")

        if errors:
            state["purchase_order_generated"] = False
            state["purchase_order"] = None
            state["purchase_order_number"] = None
            state["purchase_order_timestamp"] = None
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Purchase order generation failed: {'; '.join(errors)}"
            )
            state["errors"] = state.get("errors", []) + errors
            return state

        purchase_order_number = str(uuid4()).split("-")[0].upper()
        purchase_order = {
            "purchase_order_number": purchase_order_number,
            "vendor_name": selected_vendor.get("vendor_name"),
            "items": requested_items,
            "total_cost": total_cost,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "Generated",
        }

        state["purchase_order_generated"] = True
        state["purchase_order"] = purchase_order
        state["purchase_order_number"] = purchase_order_number
        state["purchase_order_timestamp"] = purchase_order["generated_at"]
        state["execution_status"] = "generated"
        state.setdefault("execution_log", []).append(
            f"{purchase_order['generated_at']} Purchase order generated: {purchase_order_number}"
        )
        state["errors"] = state.get("errors", [])
        return state

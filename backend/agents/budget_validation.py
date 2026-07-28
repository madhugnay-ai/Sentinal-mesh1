from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from graph.state import WorkflowState


class BudgetValidationAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def execute(self, state: WorkflowState) -> WorkflowState:
        workflow_data = state.get("workflow_data") or {}
        selected_vendor = state.get("selected_vendor")
        requested_items = workflow_data.get("requested_items") or []
        available_budget = workflow_data.get("available_budget")

        if selected_vendor is None:
            state["execution_status"] = "failed"
            state["errors"] = ["No selected vendor available for budget validation."]
            state.setdefault("execution_log", []).append("Budget validation failed: no selected vendor")
            state["budget_validation_passed"] = False
            return state

        if available_budget is None:
            state["execution_status"] = "failed"
            state["errors"] = ["No available budget provided."]
            state.setdefault("execution_log", []).append("Budget validation failed: no available budget")
            state["budget_validation_passed"] = False
            return state

        if not isinstance(requested_items, list) or not requested_items:
            state["execution_status"] = "failed"
            state["errors"] = ["No requested items were provided."]
            state.setdefault("execution_log", []).append("Budget validation failed: no requested items")
            state["budget_validation_passed"] = False
            return state

        total_cost = 0
        errors: list[str] = []
        budget_result: list[dict[str, Any]] = []

        for item in requested_items:
            if not isinstance(item, dict):
                errors.append("Each requested item must be an object.")
                continue

            item_name = item.get("item")
            requested_quantity = item.get("quantity", 1)
            if not isinstance(item_name, str) or not item_name.strip():
                errors.append("Each requested item must include a valid item name.")
                continue

            if not isinstance(requested_quantity, int) or requested_quantity < 0:
                errors.append(f"Invalid quantity for {item_name}.")
                continue

            if selected_vendor.get("item") != item_name:
                continue

            item_cost = selected_vendor["price"] * requested_quantity
            total_cost += item_cost
            budget_result.append(
                {
                    "item": item_name,
                    "requested_quantity": requested_quantity,
                    "unit_price": selected_vendor["price"],
                    "item_cost": item_cost,
                }
            )

        if errors:
            state["execution_status"] = "failed"
            state["errors"] = errors
            state.setdefault("execution_log", []).append("Budget validation failed")
            state["budget_validation_passed"] = False
            return state

        budget_remaining = available_budget - total_cost
        budget_validation_passed = total_cost <= available_budget

        state["budget_validation_passed"] = budget_validation_passed
        state["total_cost"] = total_cost
        state["budget_remaining"] = budget_remaining
        state["budget_result"] = budget_result

        if budget_validation_passed:
            state["execution_status"] = "validated"
            state.setdefault("execution_log", []).append(
                f"Budget validation successful. ₹{budget_remaining:,.0f} remaining."
            )
        else:
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"Budget exceeded by ₹{abs(budget_remaining):,.0f}."
            )

        return state

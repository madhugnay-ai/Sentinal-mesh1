from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.base_agent import BaseAgent
from graph.state import WorkflowState

SUPPORTED_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "greater_than",
    "less_than",
    "greater_than_or_equal",
    "less_than_or_equal",
    "exists",
    "not_exists",
}


class ConditionAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def _get_node_config(self, state: WorkflowState) -> dict[str, Any] | None:
        workflow_data = state.get("workflow_data") or {}
        nodes = workflow_data.get("nodes") or []

        for node in nodes if isinstance(nodes, list) else []:
            if isinstance(node, dict) and node.get("id") == state.get("current_node"):
                data = node.get("data")
                if isinstance(data, dict):
                    return data
        return None

    def _resolve_field_value(self, field: str, state: WorkflowState) -> Any:
        return state.get(field)

    def _to_number(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _evaluate(self, field_value: Any, operator: str, compare_value: str) -> bool:
        if operator == "exists":
            return field_value is not None
        if operator == "not_exists":
            return field_value is None

        if field_value is None:
            return False

        field_text = str(field_value)
        compare_text = str(compare_value)

        if operator == "equals":
            return field_text == compare_text
        if operator == "not_equals":
            return field_text != compare_text
        if operator == "contains":
            return compare_text in field_text
        if operator == "not_contains":
            return compare_text not in field_text

        numeric_field = self._to_number(field_value)
        numeric_compare = self._to_number(compare_value)
        if numeric_field is None or numeric_compare is None:
            raise ValueError("Numeric comparison requires a numeric field and value.")

        if operator == "greater_than":
            return numeric_field > numeric_compare
        if operator == "less_than":
            return numeric_field < numeric_compare
        if operator == "greater_than_or_equal":
            return numeric_field >= numeric_compare
        if operator == "less_than_or_equal":
            return numeric_field <= numeric_compare

        raise ValueError(f"Unsupported operator: {operator}")

    def execute(self, state: WorkflowState) -> WorkflowState:
        config = self._get_node_config(state)
        if config is None:
            state["errors"] = ["Condition node configuration missing."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Condition node configuration missing."
            )
            return state

        field = str(config.get("field") or "").strip()
        operator = str(config.get("operator") or "").strip()
        value = str(config.get("value") or "").strip()

        if not field:
            state["errors"] = ["Condition field is required."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Condition failed: missing field."
            )
            return state

        if operator not in SUPPORTED_OPERATORS:
            state["errors"] = [f"Unsupported condition operator: {operator}."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Condition failed: unsupported operator {operator}."
            )
            return state

        if state.get("execution_status") == "no_messages":
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Condition skipped due to no_messages."
            )
            state.setdefault("skipped_nodes", []).append(state.get("current_node", "unknown"))
            return state

        field_value = self._resolve_field_value(field, state)
        result = False

        try:
            result = self._evaluate(field_value, operator, value)
        except ValueError as exc:
            state["errors"] = [str(exc)]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Condition failed: {exc}"
            )
            return state

        state["condition_result"] = result
        state["condition_field"] = field
        state["condition_operator"] = operator
        state["condition_value"] = value
        state["execution_status"] = "completed"
        state.setdefault("execution_log", []).append(
            f"{datetime.now(timezone.utc).isoformat()} Condition evaluated: {field} {operator} {value} -> {result}"
        )
        return state

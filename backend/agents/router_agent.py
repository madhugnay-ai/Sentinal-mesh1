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


class RouterAgent(BaseAgent):
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
        normalized_field = field_text.lower()
        normalized_compare = compare_text.lower()

        if operator == "equals":
            return normalized_field == normalized_compare
        if operator == "not_equals":
            return normalized_field != normalized_compare
        if operator == "contains":
            return normalized_compare in normalized_field
        if operator == "not_contains":
            return normalized_compare not in normalized_field

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
            state["errors"] = ["Router node configuration missing."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Router node configuration missing."
            )
            return state

        field = str(config.get("field") or "").strip()
        routes = config.get("routes") if isinstance(config.get("routes"), list) else []
        default_route = str(config.get("defaultRoute") or "").strip()

        if not field:
            state["errors"] = ["Router field is required."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Router failed: missing field."
            )
            return state

        if not routes:
            state["errors"] = ["Router requires at least one route."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Router failed: no routes configured."
            )
            return state

        if state.get("execution_status") == "no_messages":
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Router skipped due to no_messages."
            )
            state.setdefault("skipped_nodes", []).append(state.get("current_node", "unknown"))
            return state

        selected_route = None
        for route_config in routes:
            if not isinstance(route_config, dict):
                continue
            route = str(route_config.get("route") or "").strip()
            operator = str(route_config.get("operator") or "").strip()
            value = str(route_config.get("value") or "").strip()

            if not route:
                continue
            if operator not in SUPPORTED_OPERATORS:
                state["errors"] = [f"Unsupported router operator: {operator}."]
                state["execution_status"] = "failed"
                state.setdefault("execution_log", []).append(
                    f"{datetime.now(timezone.utc).isoformat()} Router failed: unsupported operator {operator}."
                )
                return state

            try:
                if self._evaluate(self._resolve_field_value(field, state), operator, value):
                    selected_route = route
                    break
            except ValueError as exc:
                state["errors"] = [str(exc)]
                state["execution_status"] = "failed"
                state.setdefault("execution_log", []).append(
                    f"{datetime.now(timezone.utc).isoformat()} Router failed: {exc}"
                )
                return state

        if selected_route is None:
            if not default_route:
                state["errors"] = ["Router default route is required when no rules match."]
                state["execution_status"] = "failed"
                state.setdefault("execution_log", []).append(
                    f"{datetime.now(timezone.utc).isoformat()} Router failed: no default route configured."
                )
                return state
            selected_route = default_route

        state["router_result"] = selected_route
        state["execution_status"] = "completed"
        state.setdefault("execution_log", []).append(
            f"{datetime.now(timezone.utc).isoformat()} Router evaluated: field={field} -> route={selected_route}"
        )
        return state

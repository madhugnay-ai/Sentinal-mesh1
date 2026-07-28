from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.base_agent import BaseAgent
from graph.state import WorkflowState


class RequirementValidationAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def execute(self, state: WorkflowState) -> WorkflowState:
        workflow_data = state.get("workflow_data") or {}
        errors: list[str] = []

        if not workflow_data:
            errors.append("Workflow is empty.")
        else:
            nodes = workflow_data.get("nodes") or []
            edges = workflow_data.get("edges") or []

            if not isinstance(nodes, list) or not nodes:
                errors.append("Workflow must contain at least one node.")

            if not isinstance(edges, list):
                errors.append("Workflow edges must be a list.")

            node_ids = [node.get("id") for node in nodes if isinstance(node, dict) and node.get("id")]
            if not node_ids:
                errors.append("Workflow does not contain any valid node IDs.")

            if len(node_ids) != len(set(node_ids)):
                errors.append("Node IDs must be unique.")

            if not node_ids:
                errors.append("Missing entry node.")
            else:
                first_node_id = node_ids[0]
                if not first_node_id:
                    errors.append("Missing entry node.")

            for edge in edges if isinstance(edges, list) else []:
                if not isinstance(edge, dict):
                    errors.append("Each edge must be an object.")
                    continue

                source = edge.get("source")
                target = edge.get("target")
                if source not in node_ids or target not in node_ids:
                    errors.append(f"Invalid edge reference: {source} -> {target}")

        if errors:
            state["execution_status"] = "failed"
            state["validation_passed"] = False
            state["errors"] = errors
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Requirement validation failed: {'; '.join(errors)}"
            )
            return state

        state["execution_status"] = "validated"
        state["validation_passed"] = True
        state.setdefault("execution_log", []).append(
            f"{datetime.now(timezone.utc).isoformat()} Requirement validation passed"
        )
        return state

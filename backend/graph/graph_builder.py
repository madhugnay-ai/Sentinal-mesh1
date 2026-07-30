from __future__ import annotations

from collections import deque
from typing import Any
from collections.abc import Callable

try:
    from langgraph.constants import END
    from langgraph.graph import StateGraph
except ModuleNotFoundError:  # pragma: no cover - fallback for test environments without langgraph installed
    END = "END"
    StateGraph = None

from agents.agent_registry import AgentRegistry
from graph.state import WorkflowState


class GraphBuilder:
    def __init__(self) -> None:
        self._graph = None
        self._agent_registry = AgentRegistry()

    def _validate_workflow(self, workflow_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        if not workflow_json:
            return ["Workflow is empty."]

        nodes = workflow_json.get("nodes") or []
        edges = workflow_json.get("edges") or []

        if not isinstance(nodes, list) or not nodes:
            errors.append("Workflow must contain at least one node.")

        if not isinstance(edges, list):
            errors.append("Workflow edges must be a list.")

        node_ids = {node.get("id") for node in nodes if isinstance(node, dict) and node.get("id")}
        if not node_ids:
            errors.append("Workflow does not contain any valid node IDs.")

        for edge in edges if isinstance(edges, list) else []:
            if not isinstance(edge, dict):
                errors.append("Each edge must be an object.")
                continue
            source = edge.get("source")
            target = edge.get("target")
            if source not in node_ids or target not in node_ids:
                errors.append(f"Invalid edge reference: {source} -> {target}")

        entry_node = None
        for node in nodes if isinstance(nodes, list) else []:
            if isinstance(node, dict) and node.get("id"):
                entry_node = node.get("id")
                break

        if entry_node is None:
            errors.append("Missing entry node.")

        if not errors:
            adjacency = {node_id: [] for node_id in node_ids}
            for edge in edges if isinstance(edges, list) else []:
                if isinstance(edge, dict):
                    source = edge.get("source")
                    target = edge.get("target")
                    if source in adjacency and target in adjacency:
                        adjacency[source].append(target)

            visited: set[str] = set()
            stack: set[str] = set()

            def visit(node_id: str) -> None:
                if node_id in stack:
                    errors.append("Cyclic workflow detected.")
                    return
                if node_id in visited:
                    return
                stack.add(node_id)
                for neighbor in adjacency.get(node_id, []):
                    visit(neighbor)
                stack.remove(node_id)
                visited.add(node_id)

            for node_id in adjacency:
                visit(node_id)

        return errors

    def _normalize_categories(self, categories: Any) -> list[str]:
        if isinstance(categories, str):
            parsed = [item.strip() for item in categories.split(",") if item.strip()]
            return [category.lower() for category in parsed]
        if isinstance(categories, list):
            normalized = []
            for category in categories:
                if isinstance(category, str):
                    cleaned = category.strip()
                    if cleaned:
                        normalized.append(cleaned.lower())
            return normalized
        return []

    def _build_placeholder_node(self, node_id: str) -> Any:
        def placeholder(state: WorkflowState) -> WorkflowState:
            state["current_node"] = node_id
            # Short-circuit: if upstream indicated no work, skip executing placeholders
            if state.get("execution_status") == "no_messages":
                state.setdefault("execution_log", []).append(f"{node_id} skipped due to no_messages")
                state.setdefault("skipped_nodes", []).append(node_id)
                return state
            state.setdefault("execution_log", []).append(f"Executed {node_id}")
            state.setdefault("executed_nodes", []).append(node_id)
            state["execution_status"] = "running"
            return state

        return placeholder

    def _build_node_handler(self, node: dict[str, Any]) -> Any:
        node_id = node.get("id")
        node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
        semantic_kind = node_data.get("kind")

        kind_aliases = {
            "requirement-validation": "Requirement Validation",
            "inventory": "Inventory",
            "email-trigger": "Email Trigger",
            "llm": "LLM",
            "send-email": "Send Email",
            "vendor-selection": "Vendor Selection",
            "budget-validation": "Budget Validation",
            "approval": "Approval",
            "purchase-order": "Purchase Order",
            "condition": "Condition",
            "router": "Router",
            "classifier": "Classifier",
            "extractor": "Extractor",
            "summarizer": "Summarizer",
            "supervisor": "Supervisor",
            "failure-detection": "Failure Detection",
            "rag-incident-memory": "RAG Incident Memory",
            "auto-healing": "Auto Healing",
        }

        node_type = kind_aliases.get(semantic_kind, semantic_kind or node.get("type"))
        agent = self._agent_registry.get_agent(node_type)
        if agent is not None:
            def handler(state: WorkflowState) -> WorkflowState:
                new_state = {**state, "current_node": node_id}
                if new_state.get("execution_status") == "no_messages":
                    new_state.setdefault("execution_log", []).append(f"{node_id} skipped due to no_messages")
                    new_state.setdefault("skipped_nodes", []).append(node_id)
                    return new_state
                new_state.setdefault("executed_nodes", []).append(node_id)
                return agent.execute(new_state)

            return handler

        return self._build_placeholder_node(node_id or "unknown")

    def build_graph(self, workflow_json: dict[str, Any]) -> Any:
        errors = self._validate_workflow(workflow_json)
        if errors:
            raise ValueError("; ".join(errors))

        nodes = workflow_json.get("nodes") or []
        edges = workflow_json.get("edges") or []
        node_ids = [node["id"] for node in nodes if isinstance(node, dict) and node.get("id")]

        if StateGraph is None:
            raise RuntimeError("langgraph is not installed")

        graph = StateGraph(WorkflowState)
        condition_outgoing: dict[str, dict[str, str]] = {}

        for node in nodes:
            if isinstance(node, dict):
                node_id = node.get("id")
                if node_id:
                    graph.add_node(node_id, self._build_node_handler(node))

        for edge in edges if isinstance(edges, list) else []:
            if not isinstance(edge, dict):
                continue
            source = edge.get("source")
            target = edge.get("target")
            source_handle = edge.get("sourceHandle")
            if source in node_ids and target in node_ids and not source_handle:
                graph.add_edge(source, target)
            elif source in node_ids and target in node_ids and isinstance(source_handle, str):
                condition_outgoing.setdefault(source, {})[source_handle] = target

        def make_condition_path_fn(branches: dict[str, str]) -> Callable[[WorkflowState], str]:
            def path(state: WorkflowState) -> str:
                if state.get("execution_status") == "no_messages":
                    return "false"
                if state.get("execution_status") != "completed":
                    return END
                return "true" if bool(state.get("condition_result")) else "false"

            return path

        def make_router_path_fn(node_data: dict[str, Any], branches: dict[str, str]) -> Callable[[WorkflowState], str]:
            default_route = str(node_data.get("defaultRoute") or "").strip()

            def path(state: WorkflowState) -> str:
                if state.get("execution_status") != "completed":
                    return END
                selected = state.get("router_result")
                if isinstance(selected, str):
                    if selected in branches:
                        return selected
                    if default_route and selected == default_route and "default" in branches:
                        return "default"
                return END

            return path

        def make_classifier_path_fn(node_data: dict[str, Any], branches: dict[str, str]) -> Callable[[WorkflowState], str]:
            def path(state: WorkflowState) -> str:
                if state.get("execution_status") != "completed":
                    return END
                selected = state.get("classification")
                if isinstance(selected, str):
                    normalized = selected.strip().lower()
                    if normalized in branches:
                        return normalized
                return END

            return path

        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            node_id = node.get("id")
            node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
            if node_id and isinstance(node_data, dict):
                kind = node_data.get("kind")
                if kind == "condition":
                    branches = condition_outgoing.get(node_id, {})
                    if "true" not in branches or "false" not in branches:
                        raise ValueError(
                            f"Condition node {node_id} requires both true and false outgoing edges."
                        )
                    graph.add_conditional_edges(
                        node_id,
                        make_condition_path_fn(branches),
                        path_map={"true": branches["true"], "false": branches["false"], END: END},
                    )
                elif kind == "router":
                    branches = condition_outgoing.get(node_id, {})
                    if not branches:
                        raise ValueError(f"Router node {node_id} requires at least one outgoing route edge.")
                    graph.add_conditional_edges(
                        node_id,
                        make_router_path_fn(node_data, branches),
                        path_map={**{route_name: target for route_name, target in branches.items()}, END: END},
                    )
                elif kind == "classifier":
                    branches = condition_outgoing.get(node_id, {})
                    if not branches:
                        raise ValueError(f"Classifier node {node_id} requires at least one outgoing category edge.")

                    configured_categories = self._normalize_categories(node_data.get("categories"))
                    if configured_categories:
                        missing_categories = [category for category in configured_categories if category not in branches]
                        if missing_categories:
                            raise ValueError(
                                f"Classifier node {node_id} requires outgoing edge for category '{missing_categories[0]}'."
                            )

                    graph.add_conditional_edges(
                        node_id,
                        make_classifier_path_fn(node_data, branches),
                        path_map={**{route_name: target for route_name, target in branches.items()}, END: END},
                    )

        entry_node = node_ids[0] if node_ids else None
        if entry_node is not None:
            graph.set_entry_point(entry_node)

        self._graph = graph.compile()
        return self._graph

    def execute_workflow(self, workflow_json: dict[str, Any]) -> dict[str, Any]:
        if not workflow_json:
            return {
                "status": "error",
                "visited_nodes": [],
                "execution_log": [],
                "errors": ["Workflow is empty."],
            }

        try:
            graph = self.build_graph(workflow_json)
        except ValueError as exc:
            return {
                "status": "error",
                "visited_nodes": [],
                "execution_log": [],
                "errors": [str(exc)],
            }

        initial_state: WorkflowState = {
            "workflow_id": str(workflow_json.get("workflow_id") or "unknown"),
            "current_node": None,
            "execution_status": "pending",
            "execution_log": [],
            "workflow_data": workflow_json,
        }

        result = graph.invoke(initial_state)

        visited_nodes = []
        for entry in result.get("execution_log", []):
            if entry.startswith("Executed "):
                visited_nodes.append(entry.replace("Executed ", ""))

        return {
            "status": "completed",
            "visited_nodes": visited_nodes,
            "execution_log": result.get("execution_log", []),
            "errors": [],
        }

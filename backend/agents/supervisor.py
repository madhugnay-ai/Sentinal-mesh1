from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from agents.base_agent import BaseAgent
from constants import node_types
from graph.state import WorkflowState


class SupervisorAgent(BaseAgent):
    def _workflow_nodes(self, state: WorkflowState) -> list[dict[str, Any]]:
        workflow_data = state.get("workflow_data") or {}
        nodes = workflow_data.get("nodes") or []
        return [node for node in nodes if isinstance(node, dict)]

    def _workflow_node_names(self, state: WorkflowState) -> set[str]:
        names: set[str] = set()
        for node in self._workflow_nodes(state):
            node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
            node_type = node_data.get("kind") or node.get("type")
            if node_type:
                names.add(str(node_type))
        return names

    def _workflow_stage_names(self, state: WorkflowState) -> list[str]:
        stage_names: list[str] = []
        for node in self._workflow_nodes(state):
            node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
            label = node_data.get("label") or node.get("id") or node.get("type")
            node_kind = node_data.get("kind") or node.get("type")
            if node_kind in {"email-trigger", "Email Trigger", "condition", "Condition", "llm", "LLM", "send-email", "Send Email"}:
                stage_names.append(str(label))
        return stage_names

    def _display_label(self, node: dict[str, Any]) -> str:
        node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
        label = node_data.get("label")
        if isinstance(label, str) and label.strip():
            return label.strip()

        kind = node_data.get("kind") or node.get("type")
        if isinstance(kind, str) and kind.strip():
            return " ".join(part.capitalize() for part in kind.replace("_", "-").split("-"))

        return str(node.get("id") or node.get("type") or "Node")

    def _stage_label(
        self,
        stage_id: str | None,
        node_lookup: dict[str, dict[str, Any]],
        use_node_id_for_email_trigger: bool = False,
    ) -> str:
        if not stage_id:
            return ""

        if stage_id in {node_types.REQUIREMENT_VALIDATION, node_types.INVENTORY, node_types.VENDOR_SELECTION, node_types.BUDGET_VALIDATION, node_types.APPROVAL, node_types.PURCHASE_ORDER}:
            return stage_id

        node = node_lookup.get(stage_id)
        if node is not None:
            node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
            label = node_data.get("label")
            if isinstance(label, str) and label.strip():
                return label.strip()

            kind = node_data.get("kind") or node.get("type")
            if kind in {"email-trigger", "Email Trigger"} and use_node_id_for_email_trigger:
                node_id = node.get("id")
                if isinstance(node_id, str) and node_id:
                    return node_id

        return self._display_label(node or {"id": stage_id, "data": {}})

    def _is_generic_execution_node(self, node: dict[str, Any]) -> bool:
        node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
        node_kind = node_data.get("kind") or node.get("type")
        if node_kind in {None, "supervisor", "Supervisor", "failure-detection", "Failure Detection", "rag-incident-memory", "RAG Incident Memory", "auto-healing", "Auto Healing"}:
            return False
        if node_kind in {"requirement-validation", "Requirement Validation", "inventory", "Inventory", "vendor-selection", "Vendor Selection", "budget-validation", "Budget Validation", "approval", "Approval", "purchase-order", "Purchase Order"}:
            return False
        return True

    def _stage_key(self, node_kind: str | None) -> str | None:
        if node_kind is None:
            return None
        if node_kind in {"requirement-validation", "Requirement Validation"}:
            return node_types.REQUIREMENT_VALIDATION
        if node_kind in {"inventory", "Inventory"}:
            return node_types.INVENTORY
        if node_kind in {"vendor-selection", "Vendor Selection"}:
            return node_types.VENDOR_SELECTION
        if node_kind in {"budget-validation", "Budget Validation"}:
            return node_types.BUDGET_VALIDATION
        if node_kind in {"approval", "Approval"}:
            return node_types.APPROVAL
        if node_kind in {"purchase-order", "Purchase Order"}:
            return node_types.PURCHASE_ORDER
        if node_kind in {"email-trigger", "Email Trigger", "condition", "Condition", "llm", "LLM", "send-email", "Send Email"}:
            return str(node_kind)
        return None

    def execute(self, state: WorkflowState) -> WorkflowState:
        execution_log = list(state.get("execution_log") or [])
        errors = list(state.get("errors") or [])
        execution_status = state.get("execution_status")
        workflow_nodes = self._workflow_node_names(state)
        available_stages = {self._stage_key(node_kind) for node_kind in workflow_nodes if self._stage_key(node_kind) is not None}
        procurement_stage_names = {
            node_types.REQUIREMENT_VALIDATION,
            node_types.INVENTORY,
            node_types.VENDOR_SELECTION,
            node_types.BUDGET_VALIDATION,
            node_types.APPROVAL,
            node_types.PURCHASE_ORDER,
        }
        generic_stage_names = {
            "email-trigger",
            "Email Trigger",
            "condition",
            "Condition",
            "llm",
            "LLM",
            "send-email",
            "Send Email",
        }
        has_procurement_nodes = any(stage in procurement_stage_names for stage in available_stages)
        has_generic_nodes = any(stage in generic_stage_names for stage in available_stages)
        has_procurement_state = any(
            state.get(field_name) is not None
            for field_name in [
                "validation_passed",
                "inventory_checked",
                "vendor_selection_completed",
                "budget_validation_passed",
                "approval_status",
                "purchase_order_generated",
            ]
        )
        if not workflow_nodes and not has_procurement_state:
            available_stages.update(procurement_stage_names)
        if state.get("validation_passed") is not None:
            available_stages.add(node_types.REQUIREMENT_VALIDATION)
        if state.get("inventory_checked") is not None:
            available_stages.add(node_types.INVENTORY)
        if state.get("vendor_selection_completed") is not None:
            available_stages.add(node_types.VENDOR_SELECTION)
        if state.get("budget_validation_passed") is not None:
            available_stages.add(node_types.BUDGET_VALIDATION)
        if state.get("approval_status") is not None:
            available_stages.add(node_types.APPROVAL)
        if state.get("purchase_order_generated") is not None:
            available_stages.add(node_types.PURCHASE_ORDER)
        has_procurement_nodes = any(stage in procurement_stage_names for stage in available_stages)
        is_explicitly_generic_workflow = bool(workflow_nodes) and not has_procurement_nodes and has_generic_nodes

        stage_ids_by_state: dict[str, list[str]] = {
            "completed": [],
            "failed": [],
            "skipped": [],
        }

        def record_stage(stage_id: str | None, category: str) -> None:
            if not stage_id:
                return
            for other_category, stage_ids in stage_ids_by_state.items():
                if other_category == category:
                    continue
                if stage_id in stage_ids:
                    stage_ids_by_state[other_category].remove(stage_id)
            if stage_id not in stage_ids_by_state[category]:
                stage_ids_by_state[category].append(stage_id)

        generic_nodes: list[dict[str, Any]] = []
        for node in self._workflow_nodes(state):
            if self._is_generic_execution_node(node):
                generic_nodes.append(node)

        node_lookup = {str(node.get("id")): node for node in generic_nodes if isinstance(node.get("id"), str)}

        executed_nodes = list(state.get("executed_nodes") or [])
        skipped_nodes = list(state.get("skipped_nodes") or [])
        current_node_id = state.get("current_node")
        
        failure_node_id = current_node_id if (execution_status == "failed" or errors) and current_node_id else None
        no_messages_detected = execution_status == "no_messages" and any(
            "found no matching messages" in entry for entry in execution_log
        )

        failure_index = None
        generic_node_ids = [node.get("id") for node in generic_nodes]
        if failure_node_id is not None and failure_node_id in generic_node_ids:
            failure_index = generic_node_ids.index(failure_node_id)

        # If there is no explicit executed_nodes list, infer progress from current_node
        success_index = None
        current_node_id = state.get("current_node")
        if executed_nodes == [] and current_node_id and execution_status in {"received", "completed"}:
            try:
                success_index = [node.get("id") for node in generic_nodes].index(current_node_id)
            except ValueError:
                success_index = None
        

        # If this is an explicitly generic workflow and we have no executed_nodes recorded
        # but the workflow status indicates work was received/completed, assume generic
        # nodes were completed (e.g., Email Trigger-only flows that report `received`).
        generic_auto_completed = False
        if is_explicitly_generic_workflow and execution_status in {"received", "completed"} and not executed_nodes and not skipped_nodes:
            # Only auto-complete email-trigger nodes for received-only generic workflows.
            auto_completed: list[str] = []
            for node in generic_nodes:
                node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
                if node_data.get("kind") in {"email-trigger", "Email Trigger"}:
                    node_id = node.get("id")
                    if isinstance(node_id, str) and node_id:
                        auto_completed.append(node_id)
            if auto_completed and all((n.get("data") or {}).get("kind") in {"email-trigger", "Email Trigger"} for n in generic_nodes):
                for node_id in auto_completed:
                    record_stage(node_id, "completed")
                # Only short-circuit when the workflow contains nothing but email-trigger nodes
                generic_auto_completed = True
        

        failure_context = state.get("failure_context") if isinstance(state.get("failure_context"), dict) else {}
        if failure_context and execution_status == "failed":
            failed_node_id = str(failure_context.get("failed_node_id") or "")
            failed_node_type = str(failure_context.get("failed_node_type") or "Unknown")
            failure_message = str(failure_context.get("failure_message") or "")
            failure_error_type = str(failure_context.get("failure_error_type") or "UnknownError")
            diagnosis_parts = [
                f"Node {failed_node_id} failed during execution",
                f"Node type: {failed_node_type}",
                f"Error: {failure_message}",
                f"Exception type: {failure_error_type}",
            ]
            state["supervisor_diagnosis"] = " | ".join(diagnosis_parts)
            execution_log.append(f"Supervisor diagnosis: {state['supervisor_diagnosis']}")

        # Precompute outgoing targets by node id and source handle.
        branch_outgoing: dict[str, dict[str, str]] = {}
        for edge in (state.get("workflow_data") or {}).get("edges", []) if isinstance((state.get("workflow_data") or {}).get("edges", []), list) else []:
            src = edge.get("source")
            handle = edge.get("sourceHandle")
            tgt = edge.get("target")
            if isinstance(src, str) and isinstance(handle, str) and isinstance(tgt, str):
                branch_outgoing.setdefault(src, {})[handle] = tgt

        handled_stage_ids: set[str] = set()
        for index, node in enumerate(generic_nodes):
            if generic_auto_completed:
                # we've already recorded completions for generic nodes
                break
            node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                continue
            if node_id in handled_stage_ids:
                continue
            # Special-case Condition nodes: mark only the taken branch completed
            if node_data.get("kind") in {"condition", "Condition"}:
                record_stage(node_id, "completed")
                handled_stage_ids.add(node_id)
                branches = branch_outgoing.get(node_id, {})
                taken = None
                if state.get("condition_result") is True:
                    taken = branches.get("true")
                elif state.get("condition_result") is False:
                    taken = branches.get("false")
                # mark taken branch as completed and the other branch as skipped
                for handle, target in branches.items():
                    if not target:
                        continue
                    if target == taken:
                        record_stage(target, "completed")
                    else:
                        record_stage(target, "skipped")
                    handled_stage_ids.add(target)
                # move to next node
                continue
            if node_data.get("kind") in {"router", "Router"}:
                record_stage(node_id, "completed")
                handled_stage_ids.add(node_id)
                branches = branch_outgoing.get(node_id, {})
                taken = None
                selected_route = state.get("router_result")
                if isinstance(selected_route, str):
                    taken = branches.get(selected_route)
                for handle, target in branches.items():
                    if not target:
                        continue
                    if target == taken:
                        record_stage(target, "completed")
                    else:
                        record_stage(target, "skipped")
                    handled_stage_ids.add(target)
                continue
            if failure_node_id and node_id == failure_node_id:
                record_stage(node_id, "failed")
            elif node_id in skipped_nodes:
                record_stage(node_id, "skipped")
            elif node_id in executed_nodes:
                record_stage(node_id, "completed")
            elif success_index is not None and index <= success_index:
                record_stage(node_id, "completed")
            elif no_messages_detected:
                if node_data.get("kind") in {"email-trigger", "Email Trigger"}:
                    record_stage(node_id, "completed")
                else:
                    record_stage(node_id, "skipped")
            elif failure_index is not None and index < failure_index:
                record_stage(node_id, "completed")
            else:
                record_stage(node_id, "skipped")

        if node_types.REQUIREMENT_VALIDATION in available_stages:
            if state.get("validation_passed") is True:
                record_stage(node_types.REQUIREMENT_VALIDATION, "completed")
            elif state.get("validation_passed") is None:
                record_stage(node_types.REQUIREMENT_VALIDATION, "skipped")
            else:
                record_stage(node_types.REQUIREMENT_VALIDATION, "failed")

        if node_types.INVENTORY in available_stages:
            inventory_checked = state.get("inventory_checked")
            if inventory_checked is True and execution_status not in {"failed", "rejected"}:
                record_stage(node_types.INVENTORY, "completed")
            elif inventory_checked is None:
                record_stage(node_types.INVENTORY, "skipped")
            else:
                record_stage(node_types.INVENTORY, "failed")

        if node_types.VENDOR_SELECTION in available_stages:
            vendor_selection_completed = state.get("vendor_selection_completed")
            if vendor_selection_completed is True and execution_status not in {"failed", "rejected"}:
                record_stage(node_types.VENDOR_SELECTION, "completed")
            elif vendor_selection_completed is None:
                record_stage(node_types.VENDOR_SELECTION, "skipped")
            else:
                record_stage(node_types.VENDOR_SELECTION, "failed")

        if node_types.BUDGET_VALIDATION in available_stages:
            if state.get("budget_validation_passed") is True:
                record_stage(node_types.BUDGET_VALIDATION, "completed")
            elif state.get("budget_validation_passed") is None:
                record_stage(node_types.BUDGET_VALIDATION, "skipped")
            else:
                record_stage(node_types.BUDGET_VALIDATION, "failed")

        if node_types.APPROVAL in available_stages:
            approval_status = state.get("approval_status")
            if approval_status == "Approved":
                record_stage(node_types.APPROVAL, "completed")
            elif approval_status == "Pending Manager Approval":
                record_stage(node_types.APPROVAL, "completed")
            elif approval_status == "Rejected":
                record_stage(node_types.APPROVAL, "failed")
            elif approval_status is None:
                record_stage(node_types.APPROVAL, "skipped")
            else:
                record_stage(node_types.APPROVAL, "failed")

        if node_types.PURCHASE_ORDER in available_stages:
            purchase_order_generated = state.get("purchase_order_generated")
            if purchase_order_generated is True:
                record_stage(node_types.PURCHASE_ORDER, "completed")
            elif purchase_order_generated is None:
                record_stage(node_types.PURCHASE_ORDER, "skipped")
            elif state.get("approval_status") == "Pending Manager Approval":
                record_stage(node_types.PURCHASE_ORDER, "skipped")
            elif execution_status == "failed" or errors:
                record_stage(node_types.PURCHASE_ORDER, "failed")
            else:
                record_stage(node_types.PURCHASE_ORDER, "skipped")

        use_node_id_for_email_trigger = len(generic_nodes) == 1
        completed_stages = [
            self._stage_label(stage_id, node_lookup, use_node_id_for_email_trigger=use_node_id_for_email_trigger)
            for stage_id in stage_ids_by_state["completed"]
        ]
        failed_stages = [
            self._stage_label(stage_id, node_lookup, use_node_id_for_email_trigger=use_node_id_for_email_trigger)
            for stage_id in stage_ids_by_state["failed"]
        ]
        skipped_stages = [
            self._stage_label(stage_id, node_lookup, use_node_id_for_email_trigger=use_node_id_for_email_trigger)
            for stage_id in stage_ids_by_state["skipped"]
        ]

        if execution_status == "failed" or errors:
            workflow_health = "Failed"
        elif state.get("approval_status") == "Pending Manager Approval" and not state.get("purchase_order_generated"):
            workflow_health = "Warning"
        elif not errors and (execution_status == "received" or execution_status == "completed") and not failed_stages and not skipped_stages:
            workflow_health = "Healthy"
        elif not errors and state.get("purchase_order_generated") is True:
            workflow_health = "Healthy"
        elif execution_status == "no_messages" and not errors:
            workflow_health = "Healthy"
        elif is_explicitly_generic_workflow and execution_status in {"received", "completed"}:
            workflow_health = "Healthy"
        elif not errors and state.get("validation_passed") is None and state.get("inventory_checked") is None and state.get("vendor_selection_completed") is None and state.get("budget_validation_passed") is None and state.get("approval_status") is None and state.get("purchase_order_generated") is None:
            workflow_health = "Warning"
        else:
            workflow_health = "Warning"

        summary_parts = [f"Workflow health: {workflow_health}"]
        if completed_stages:
            summary_parts.append(f"Completed stages: {', '.join(completed_stages)}")
        if failed_stages:
            summary_parts.append(f"Failed stages: {', '.join(failed_stages)}")
        if skipped_stages:
            summary_parts.append(f"Skipped stages: {', '.join(skipped_stages)}")
        workflow_summary = " | ".join(summary_parts)

        execution_log.append(f"Workflow health: {workflow_health}")
        execution_log.append(workflow_summary)

        state["workflow_health"] = workflow_health
        state["completed_stages"] = completed_stages
        state["failed_stages"] = failed_stages
        state["skipped_stages"] = skipped_stages
        # computed stage lists
        state["workflow_summary"] = workflow_summary
        state["supervisor_timestamp"] = datetime.now(timezone.utc).isoformat()
        state["execution_log"] = execution_log
        if "supervisor_diagnosis" not in state:
            state["supervisor_diagnosis"] = ""

        return state

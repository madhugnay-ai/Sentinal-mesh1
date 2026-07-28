from __future__ import annotations

from datetime import datetime, timezone
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
            if node_kind in {"email-trigger", "Email Trigger"}:
                stage_names.append(str(label))
            elif node_kind in {"llm", "LLM"}:
                stage_names.append(str(label))
            elif node_kind in {"send-email", "Send Email"}:
                stage_names.append(str(label))
        return stage_names

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
        if node_kind in {"email-trigger", "Email Trigger", "llm", "LLM", "send-email", "Send Email"}:
            return str(node_kind)
        return None

    def execute(self, state: WorkflowState) -> WorkflowState:
        execution_log = list(state.get("execution_log") or [])
        errors = list(state.get("errors") or [])
        execution_status = state.get("execution_status")
        workflow_nodes = self._workflow_node_names(state)
        available_stages = {self._stage_key(node_kind) for node_kind in workflow_nodes if self._stage_key(node_kind) is not None}
        procurement_stage_names = {node_types.REQUIREMENT_VALIDATION, node_types.INVENTORY, node_types.VENDOR_SELECTION, node_types.BUDGET_VALIDATION, node_types.APPROVAL, node_types.PURCHASE_ORDER}
        generic_stage_names = {"email-trigger", "Email Trigger", "llm", "LLM", "send-email", "Send Email"}
        has_procurement_nodes = any(stage in procurement_stage_names for stage in available_stages)
        has_generic_nodes = any(stage in generic_stage_names for stage in available_stages)
        has_procurement_state = any(
            state.get(field_name) is not None
            for field_name in ["validation_passed", "inventory_checked", "vendor_selection_completed", "budget_validation_passed", "approval_status", "purchase_order_generated"]
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

        completed_stages: list[str] = []
        failed_stages: list[str] = []
        skipped_stages: list[str] = []

        generic_nodes = []
        for node in self._workflow_nodes(state):
            node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
            node_kind = node_data.get("kind") or node.get("type")
            if node_kind in {"email-trigger", "Email Trigger", "llm", "LLM", "send-email", "Send Email"}:
                generic_nodes.append(node)

        executed_nodes = list(state.get("executed_nodes") or [])
        skipped_nodes = list(state.get("skipped_nodes") or [])
        current_node_id = state.get("current_node")
        failure_node_id = current_node_id if (execution_status == "failed" or errors) and current_node_id else None
        no_messages_detected = execution_status == "no_messages" and any(
            "found no matching messages" in entry for entry in execution_log
        )
        for index, node in enumerate(generic_nodes):
            node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
            label = node_data.get("label") or node.get("id") or node.get("type")
            node_id = node.get("id")
            if failure_node_id and node_id == failure_node_id:
                failed_stages.append(str(label))
            elif node_id in skipped_nodes:
                skipped_stages.append(str(label))
            elif node_id in executed_nodes:
                completed_stages.append(str(label))
            elif no_messages_detected:
                if node_data.get("kind") in {"email-trigger", "Email Trigger"}:
                    completed_stages.append(str(label))
                else:
                    skipped_stages.append(str(label))
            elif not errors and execution_status in {"received", "completed"}:
                completed_stages.append(str(label))
            elif node_id in executed_nodes or (current_node_id and node_id == current_node_id):
                completed_stages.append(str(label))
            elif failure_node_id and index < [node.get("id") for node in generic_nodes].index(failure_node_id):
                completed_stages.append(str(label))
            else:
                skipped_stages.append(str(label))

        if node_types.REQUIREMENT_VALIDATION in available_stages:
            if state.get("validation_passed") is True:
                completed_stages.append(node_types.REQUIREMENT_VALIDATION)
            elif state.get("validation_passed") is None:
                skipped_stages.append(node_types.REQUIREMENT_VALIDATION)
            else:
                failed_stages.append(node_types.REQUIREMENT_VALIDATION)

        if node_types.INVENTORY in available_stages:
            inventory_checked = state.get("inventory_checked")
            if inventory_checked is True and execution_status not in {"failed", "rejected"}:
                completed_stages.append(node_types.INVENTORY)
            elif inventory_checked is None:
                skipped_stages.append(node_types.INVENTORY)
            else:
                failed_stages.append(node_types.INVENTORY)

        if node_types.VENDOR_SELECTION in available_stages:
            vendor_selection_completed = state.get("vendor_selection_completed")
            if vendor_selection_completed is True and execution_status not in {"failed", "rejected"}:
                completed_stages.append(node_types.VENDOR_SELECTION)
            elif vendor_selection_completed is None:
                skipped_stages.append(node_types.VENDOR_SELECTION)
            else:
                failed_stages.append(node_types.VENDOR_SELECTION)

        if node_types.BUDGET_VALIDATION in available_stages:
            if state.get("budget_validation_passed") is True:
                completed_stages.append(node_types.BUDGET_VALIDATION)
            elif state.get("budget_validation_passed") is None:
                skipped_stages.append(node_types.BUDGET_VALIDATION)
            else:
                failed_stages.append(node_types.BUDGET_VALIDATION)

        if node_types.APPROVAL in available_stages:
            approval_status = state.get("approval_status")
            if approval_status == "Approved":
                completed_stages.append(node_types.APPROVAL)
            elif approval_status == "Pending Manager Approval":
                completed_stages.append(node_types.APPROVAL)
            elif approval_status == "Rejected":
                failed_stages.append(node_types.APPROVAL)
            elif approval_status is None:
                skipped_stages.append(node_types.APPROVAL)
            else:
                failed_stages.append(node_types.APPROVAL)

        if node_types.PURCHASE_ORDER in available_stages:
            purchase_order_generated = state.get("purchase_order_generated")
            if purchase_order_generated is True:
                completed_stages.append(node_types.PURCHASE_ORDER)
            elif purchase_order_generated is None:
                skipped_stages.append(node_types.PURCHASE_ORDER)
            elif approval_status == "Pending Manager Approval":
                skipped_stages.append(node_types.PURCHASE_ORDER)
            elif execution_status == "failed" or errors:
                failed_stages.append(node_types.PURCHASE_ORDER)
            else:
                skipped_stages.append(node_types.PURCHASE_ORDER)

        failed_stages = list(dict.fromkeys(failed_stages))

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
        state["workflow_summary"] = workflow_summary
        state["supervisor_timestamp"] = datetime.now(timezone.utc).isoformat()
        state["execution_log"] = execution_log

        return state

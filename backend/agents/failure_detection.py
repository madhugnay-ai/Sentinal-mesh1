from __future__ import annotations

from datetime import datetime, timezone

from agents.base_agent import BaseAgent
from constants import node_types
from graph.state import WorkflowState


class FailureDetectionAgent(BaseAgent):
    def _workflow_node_names(self, state: WorkflowState) -> set[str]:
        workflow_data = state.get("workflow_data") or {}
        nodes = workflow_data.get("nodes") or []
        names: set[str] = set()
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
            node_type = node_data.get("kind") or node.get("type")
            if node_type:
                names.add(str(node_type))
        return names

    def execute(self, state: WorkflowState) -> WorkflowState:
        execution_log = list(state.get("execution_log") or [])
        errors = list(state.get("errors") or [])
        workflow_health = state.get("workflow_health") or "Warning"
        execution_status = state.get("execution_status") or "unknown"
        validation_passed = state.get("validation_passed")
        inventory_checked = state.get("inventory_checked")
        vendor_selection_completed = state.get("vendor_selection_completed")
        budget_validation_passed = state.get("budget_validation_passed")
        approval_status = state.get("approval_status")
        purchase_order_generated = state.get("purchase_order_generated")
        workflow_nodes = self._workflow_node_names(state)
        procurement_node_names = {"requirement-validation", "Requirement Validation", "inventory", "Inventory", "vendor-selection", "Vendor Selection", "budget-validation", "Budget Validation", "approval", "Approval", "purchase-order", "Purchase Order"}
        has_procurement_nodes = any(node_kind in procurement_node_names for node_kind in workflow_nodes)
        has_procurement_state = any(
            state.get(field_name) is not None
            for field_name in ["validation_passed", "inventory_checked", "vendor_selection_completed", "budget_validation_passed", "approval_status", "purchase_order_generated"]
        )
        is_procurement_workflow = has_procurement_nodes or has_procurement_state

        failure_category = "Unknown Failure"
        failure_severity = "Medium"
        recommended_next_step = "Escalate Workflow"
        recoverable = False
        failed_stage = "Workflow"

        if validation_passed is False and is_procurement_workflow:
            failure_category = "Validation Failure"
            failed_stage = node_types.REQUIREMENT_VALIDATION
            failure_severity = "Critical"
            recoverable = False
            recommended_next_step = "Escalate Workflow"
        elif inventory_checked is False and state.get("inventory_checked") is False and is_procurement_workflow:
            failure_category = "Inventory Failure"
            failed_stage = node_types.INVENTORY
            failure_severity = "High"
            recoverable = True
            recommended_next_step = "Retry Inventory"
        elif vendor_selection_completed is False and is_procurement_workflow:
            failure_category = "Vendor Selection Failure"
            failed_stage = node_types.VENDOR_SELECTION
            failure_severity = "High"
            recoverable = True
            recommended_next_step = "Select Alternate Vendor"
        elif budget_validation_passed is False and is_procurement_workflow:
            failure_category = "Budget Failure"
            failed_stage = node_types.BUDGET_VALIDATION
            failure_severity = "High"
            recoverable = True
            recommended_next_step = "Increase Budget"
        elif approval_status == "Pending Manager Approval" and is_procurement_workflow:
            failure_category = "Approval Failure"
            failed_stage = node_types.APPROVAL
            failure_severity = "Medium"
            recoverable = True
            recommended_next_step = "Request Manual Approval"
        elif purchase_order_generated is False and approval_status == "Approved" and is_procurement_workflow:
            failure_category = "Purchase Order Failure"
            failed_stage = node_types.PURCHASE_ORDER
            failure_severity = "High"
            recoverable = True
            recommended_next_step = "Regenerate Purchase Order"
        elif execution_status == "failed" or workflow_health == "Failed":
            failure_category = "Workflow Failure"
            failed_stage = "Workflow"
            failure_severity = "Critical" if is_procurement_workflow else "Medium"
            recoverable = False
            recommended_next_step = "Escalate Workflow"
        elif errors and is_procurement_workflow:
            failure_category = "Unknown Failure"
            failed_stage = "Workflow"
            failure_severity = "Medium"
            recoverable = False
            recommended_next_step = "Escalate Workflow"
        elif errors:
            failure_category = "Workflow Failure"
            failed_stage = "Workflow"
            failure_severity = "Medium"
            recoverable = False
            recommended_next_step = "Escalate Workflow"

        if not errors and workflow_health == "Healthy":
            failure_category = "None"
            failure_severity = "Low"
            recoverable = True
            failed_stage = "None"
            recommended_next_step = "No Action"

        error_count = len(errors)
        if error_count == 0:
            error_count = 1

        failure_details = {
            "failed_stage": failed_stage,
            "category": failure_category,
            "severity": failure_severity,
            "recoverable": recoverable,
            "error_count": error_count,
            "workflow_health": workflow_health,
            "recommended_next_step": recommended_next_step,
        }

        failure_detected = failure_category != "None"
        failure_summary = (
            f"Failure detected: {failure_category} ({failure_severity})"
            if failure_detected
            else "No failures detected."
        )

        execution_log.append(failure_summary)
        if failure_detected:
            execution_log.append(f"Failure details: {failure_details['failed_stage']} | {failure_category} | {failure_severity}")

        state["failure_detected"] = failure_detected
        state["failure_category"] = failure_category
        state["failure_severity"] = failure_severity
        state["recoverable"] = recoverable
        state["failure_summary"] = failure_summary
        state["failure_timestamp"] = datetime.now(timezone.utc).isoformat()
        state["failure_details"] = failure_details
        state["execution_log"] = execution_log

        return state

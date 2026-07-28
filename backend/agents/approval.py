from __future__ import annotations

from datetime import datetime, timezone

from agents.base_agent import BaseAgent
from graph.state import WorkflowState


class ApprovalAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def execute(self, state: WorkflowState) -> WorkflowState:
        workflow_data = state.get("workflow_data") or {}
        budget_validation_passed = state.get("budget_validation_passed")
        total_cost = state.get("total_cost")
        approval_threshold = state.get("approval_threshold")

        if approval_threshold is None:
            approval_threshold = workflow_data.get("approval_threshold")

        if approval_threshold is None:
            approval_threshold = 50000

        state["approval_threshold"] = approval_threshold

        if budget_validation_passed is False:
            state["approval_status"] = "Rejected"
            state["approved_by"] = None
            state["approval_reason"] = "Budget validation failed."
            state["approval_timestamp"] = datetime.now(timezone.utc).isoformat()
            state["execution_status"] = "rejected"
            state.setdefault("execution_log", []).append(
                f"{state['approval_timestamp']} Approval decision: Rejected due to budget validation failure."
            )
            state["errors"] = state.get("errors", []) + ["Budget validation failed."]
            return state

        if total_cost is None:
            state["approval_status"] = "Rejected"
            state["approved_by"] = None
            state["approval_reason"] = "Missing total cost."
            state["approval_timestamp"] = datetime.now(timezone.utc).isoformat()
            state["execution_status"] = "rejected"
            state.setdefault("execution_log", []).append(
                f"{state['approval_timestamp']} Approval decision: Rejected due to missing total cost."
            )
            state["errors"] = state.get("errors", []) + ["Missing total cost."]
            return state

        if total_cost <= approval_threshold:
            state["approval_status"] = "Approved"
            state["approved_by"] = "System"
            state["approval_reason"] = "Within auto-approval threshold."
            state["approval_timestamp"] = datetime.now(timezone.utc).isoformat()
            state["execution_status"] = "approved"
            state.setdefault("execution_log", []).append(
                f"{state['approval_timestamp']} Approval decision: Approved within auto-approval threshold."
            )
            return state

        state["approval_status"] = "Pending Manager Approval"
        state["approved_by"] = None
        state["approval_reason"] = "Exceeds auto-approval threshold."
        state["approval_timestamp"] = datetime.now(timezone.utc).isoformat()
        state["execution_status"] = "pending_manager_approval"
        state.setdefault("execution_log", []).append(
            f"{state['approval_timestamp']} Approval decision: Pending manager approval."
        )
        return state

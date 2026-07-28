from __future__ import annotations

from datetime import datetime, timezone

from agents.base_agent import BaseAgent
from graph.state import WorkflowState


class AutoHealingAgent(BaseAgent):
    def execute(self, state: WorkflowState) -> WorkflowState:
        failure_detected = bool(state.get("failure_detected"))
        failure_category = state.get("failure_category")
        recoverable = bool(state.get("recoverable"))
        failure_details = state.get("failure_details") or {}
        recommended_next_step = failure_details.get("recommended_next_step") or "No Action"

        execution_log = list(state.get("execution_log") or [])

        if not failure_detected or failure_category in {None, "None"}:
            healing_strategy = "No Recovery Needed"
            healing_status = "Not Required"
            healing_attempted = False
            next_recommended_action = "No Recovery Needed"
        elif not recoverable:
            healing_strategy = "Escalate Workflow"
            healing_status = "Not Recommended"
            healing_attempted = False
            next_recommended_action = "Escalate Workflow"
        elif failure_category == "Inventory Failure":
            healing_strategy = "Retry Inventory Lookup"
            healing_status = "Recommended"
            healing_attempted = True
            next_recommended_action = "Retry Inventory Lookup"
        elif failure_category == "Vendor Selection Failure":
            healing_strategy = "Select Alternate Vendor"
            healing_status = "Recommended"
            healing_attempted = True
            next_recommended_action = "Select Alternate Vendor"
        elif failure_category == "Budget Failure":
            healing_strategy = "Increase Budget Request"
            healing_status = "Recommended"
            healing_attempted = True
            next_recommended_action = "Increase Budget Request"
        elif failure_category == "Approval Failure":
            healing_strategy = "Request Manual Approval"
            healing_status = "Recommended"
            healing_attempted = True
            next_recommended_action = "Request Manual Approval"
        elif failure_category == "Purchase Order Failure":
            healing_strategy = "Regenerate Purchase Order"
            healing_status = "Recommended"
            healing_attempted = True
            next_recommended_action = "Regenerate Purchase Order"
        else:
            healing_strategy = recommended_next_step if recommended_next_step else "Escalate Workflow"
            healing_status = "Recommended" if recoverable else "Not Recommended"
            healing_attempted = recoverable
            next_recommended_action = healing_strategy

        healing_summary = (
            f"Auto-healing strategy: {healing_strategy} ({healing_status})"
            if healing_attempted or healing_strategy != "No Recovery Needed"
            else "No recovery needed."
        )

        execution_log.append(healing_summary)

        state["healing_attempted"] = healing_attempted
        state["healing_strategy"] = healing_strategy
        state["healing_status"] = healing_status
        state["healing_summary"] = healing_summary
        state["healing_timestamp"] = datetime.now(timezone.utc).isoformat()
        state["next_recommended_action"] = next_recommended_action
        state["execution_log"] = execution_log

        return state

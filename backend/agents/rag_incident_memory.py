from __future__ import annotations

from agents.base_agent import BaseAgent
from constants import node_types
from graph.state import WorkflowState
from services.incident_memory import IncidentMemoryService


class RAGIncidentMemoryAgent(BaseAgent):
    def __init__(self) -> None:
        self._service = IncidentMemoryService()

    def execute(self, state: WorkflowState) -> WorkflowState:
        failure_category = state.get("failure_category")
        failure_severity = state.get("failure_severity")
        recoverable = state.get("recoverable")
        workflow_health = state.get("workflow_health")

        incident_matches = self._service.retrieve_incidents(
            failure_category=failure_category,
            severity=failure_severity,
            recoverable=recoverable,
            workflow_health=workflow_health,
        )

        if incident_matches:
            recommended_resolution = incident_matches[0].get("resolution") or "No known resolution found."
            knowledge_base_match_count = len(incident_matches)
            rag_summary = (
                f"Retrieved {knowledge_base_match_count} similar incidents for {failure_category or 'unknown failure'}."
            )
        else:
            recommended_resolution = "No known incident match found."
            knowledge_base_match_count = 0
            rag_summary = "No incident matches found in the knowledge base."

        execution_log = list(state.get("execution_log") or [])
        execution_log.append(rag_summary)

        state["incident_matches"] = [
            {
                "incident_id": incident.get("incident_id"),
                "failure_category": incident.get("failure_category"),
                "severity": incident.get("severity"),
                "recoverable": incident.get("recoverable"),
                "root_cause": incident.get("root_cause"),
                "resolution": incident.get("resolution"),
                "recommended_action": incident.get("recommended_action"),
            }
            for incident in incident_matches
        ]
        state["recommended_resolution"] = recommended_resolution
        state["knowledge_base_match_count"] = knowledge_base_match_count
        state["rag_summary"] = rag_summary
        state["execution_log"] = execution_log

        return state

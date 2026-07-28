from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from agents.agent_registry import AgentRegistry
from constants import node_types
from graph.graph_builder import GraphBuilder
from models.workflow import Workflow, WorkflowCreate, WorkflowUpdate


class WorkflowService:
    def __init__(self) -> None:
        self._workflows: dict[UUID, Workflow] = {}
        self._graph_builder = GraphBuilder()
        self._agent_registry = AgentRegistry()

    def create_workflow(self, payload: WorkflowCreate) -> Workflow:
        extra_data = payload.model_dump(exclude={"name", "description", "nodes", "edges"})
        workflow = Workflow.create(
            name=payload.name,
            description=payload.description,
            nodes=payload.nodes,
            edges=payload.edges,
            **extra_data,
        )
        self._workflows[workflow.workflow_id] = workflow
        return workflow

    def list_workflows(self) -> list[Workflow]:
        return list(self._workflows.values())

    def get_workflow(self, workflow_id: UUID) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def update_workflow(self, workflow_id: UUID, payload: WorkflowUpdate) -> Workflow | None:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return None

        extra_data = payload.model_dump(exclude={"name", "description", "nodes", "edges"})
        updated = workflow.model_copy(update={
            "name": payload.name,
            "description": payload.description,
            "nodes": payload.nodes,
            "edges": payload.edges,
            "updated_at": datetime.now(timezone.utc),
            **extra_data,
        })
        self._workflows[workflow_id] = updated
        return updated

    def execute_workflow(self, workflow_id: UUID) -> dict[str, Any] | None:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return None

        workflow_payload = workflow.model_dump(mode="python")
        workflow_payload["workflow_id"] = str(workflow_payload["workflow_id"])

        graph = self._graph_builder.build_graph(workflow_payload)
        result = graph.invoke(
            {
                "workflow_id": workflow_payload["workflow_id"],
                "current_node": None,
                "execution_status": "pending",
                "execution_log": [],
                "workflow_data": workflow_payload,
            }
        )

        monitoring_chain = [
            node_types.SUPERVISOR,
            node_types.FAILURE_DETECTION,
            node_types.RAG_INCIDENT_MEMORY,
            node_types.AUTO_HEALING,
        ]

        for node_type in monitoring_chain:
            agent = self._agent_registry.get_agent(node_type)
            if agent is not None:
                result = agent.execute(result)

        return {
            "execution_status": result.get("execution_status", "unknown"),
            "workflow_health": result.get("workflow_health", "Unknown"),
            "workflow_summary": result.get("workflow_summary", ""),
            "completed_stages": result.get("completed_stages", []),
            "failed_stages": result.get("failed_stages", []),
            "failure_category": result.get("failure_category", "None"),
            "failure_severity": result.get("failure_severity", "Low"),
            "incident_matches": result.get("incident_matches", []),
            "recommended_resolution": result.get("recommended_resolution", ""),
            "healing_strategy": result.get("healing_strategy", "No Recovery Needed"),
            "healing_status": result.get("healing_status", "Not Required"),
            "execution_log": result.get("execution_log", []),
        }

    def delete_workflow(self, workflow_id: UUID) -> bool:
        return self._workflows.pop(workflow_id, None) is not None

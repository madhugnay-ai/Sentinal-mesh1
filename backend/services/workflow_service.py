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

    def _build_node_outputs(self, result: dict[str, Any], workflow_payload: dict[str, Any]) -> list[dict[str, Any]]:
        node_outputs: list[dict[str, Any]] = []
        node_id = result.get("current_node")
        if not isinstance(node_id, str):
            return node_outputs

        node_meta: dict[str, Any] | None = None
        for node in workflow_payload.get("nodes") or []:
            if isinstance(node, dict) and node.get("id") == node_id:
                node_meta = node.get("data") or {}
                break

        outputs: dict[str, Any] = {}
        if result.get("classification") is not None:
            outputs["classification"] = result.get("classification")
        if result.get("extracted_data") is not None:
            outputs["extracted_data"] = result.get("extracted_data")
        if result.get("summary") is not None:
            outputs["summary"] = result.get("summary")

        if result.get("classifier_input_field") is not None:
            outputs["classifier_input_field"] = result.get("classifier_input_field")
        if result.get("classifier_categories") is not None:
            outputs["classifier_categories"] = result.get("classifier_categories")
        if result.get("classifier_provider") is not None:
            outputs["classifier_provider"] = result.get("classifier_provider")
        if result.get("classifier_model") is not None:
            outputs["classifier_model"] = result.get("classifier_model")

        if result.get("extractor_input_field") is not None:
            outputs["extractor_input_field"] = result.get("extractor_input_field")
        if result.get("extractor_fields") is not None:
            outputs["extractor_fields"] = result.get("extractor_fields")
        if result.get("extractor_provider") is not None:
            outputs["extractor_provider"] = result.get("extractor_provider")
        if result.get("extractor_model") is not None:
            outputs["extractor_model"] = result.get("extractor_model")

        if result.get("summary_input_field") is not None:
            outputs["summary_input_field"] = result.get("summary_input_field")
        if result.get("summary_provider") is not None:
            outputs["summary_provider"] = result.get("summary_provider")
        if result.get("summary_model") is not None:
            outputs["summary_model"] = result.get("summary_model")

        if outputs:
            node_outputs.append({
                "node_id": node_id,
                "node_type": str(node_meta.get("kind") or node_meta.get("type") or "unknown") if node_meta else "unknown",
                "outputs": outputs,
            })

        return node_outputs

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

        if result.get("execution_status") == "failed":
            failed_node_ids = [node for node in list(result.get("failed_node_ids") or []) if isinstance(node, str)]
            current_node = result.get("current_node")
            if isinstance(current_node, str) and current_node not in failed_node_ids:
                failed_node_ids.append(current_node)
            result["failed_node_ids"] = failed_node_ids

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

        node_outputs = self._build_node_outputs(result, workflow_payload)

        return {
            "execution_status": result.get("execution_status", "unknown"),
            "workflow_health": result.get("workflow_health", "Unknown"),
            "workflow_summary": result.get("workflow_summary", ""),
            "completed_stages": result.get("completed_stages", []),
            "failed_stages": result.get("failed_stages", []),
            "skipped_stages": result.get("skipped_stages", []),
            "executed_node_ids": result.get("executed_nodes", []),
            "failed_node_ids": result.get("failed_node_ids", []),
            "skipped_node_ids": result.get("skipped_nodes", []),
            "current_node_id": result.get("current_node"),
            "classification": result.get("classification"),
            "classifier_input_field": result.get("classifier_input_field"),
            "classifier_categories": result.get("classifier_categories", []),
            "classifier_provider": result.get("classifier_provider"),
            "classifier_model": result.get("classifier_model"),
            "extracted_data": result.get("extracted_data"),
            "extractor_input_field": result.get("extractor_input_field"),
            "extractor_fields": result.get("extractor_fields", []),
            "extractor_provider": result.get("extractor_provider"),
            "extractor_model": result.get("extractor_model"),
            "summary": result.get("summary"),
            "summary_input_field": result.get("summary_input_field"),
            "summary_provider": result.get("summary_provider"),
            "summary_model": result.get("summary_model"),
            "failure_category": result.get("failure_category", "None"),
            "failure_severity": result.get("failure_severity", "Low"),
            "incident_matches": result.get("incident_matches", []),
            "recommended_resolution": result.get("recommended_resolution", ""),
            "healing_strategy": result.get("healing_strategy", "No Recovery Needed"),
            "healing_status": result.get("healing_status", "Not Required"),
            "node_outputs": node_outputs,
            "execution_log": result.get("execution_log", []),
        }

    def delete_workflow(self, workflow_id: UUID) -> bool:
        return self._workflows.pop(workflow_id, None) is not None

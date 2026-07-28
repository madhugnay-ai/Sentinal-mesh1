from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from models.workflow import Workflow, WorkflowCreate, WorkflowUpdate
from services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowExecutionResponse(BaseModel):
    execution_status: str
    workflow_health: str
    workflow_summary: str
    completed_stages: list[str]
    failed_stages: list[str]
    failure_category: str
    failure_severity: str
    incident_matches: list[dict]
    recommended_resolution: str
    healing_strategy: str
    healing_status: str
    execution_log: list[str]


def get_service() -> WorkflowService:
    from main import app

    if not hasattr(app.state, "workflow_service"):
        app.state.workflow_service = WorkflowService()
    return app.state.workflow_service


@router.post("", response_model=Workflow, status_code=status.HTTP_201_CREATED)
def create_workflow(payload: WorkflowCreate) -> Workflow:
    return get_service().create_workflow(payload)


@router.get("", response_model=list[Workflow])
def list_workflows() -> list[Workflow]:
    return get_service().list_workflows()


def _parse_workflow_id(workflow_id: str) -> UUID:
    try:
        return UUID(workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workflow_id") from exc


@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow(workflow_id: str) -> Workflow:
    parsed_id = _parse_workflow_id(workflow_id)
    workflow = get_service().get_workflow(parsed_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return workflow


@router.put("/{workflow_id}", response_model=Workflow)
def update_workflow(workflow_id: str, payload: WorkflowUpdate) -> Workflow:
    parsed_id = _parse_workflow_id(workflow_id)
    workflow = get_service().update_workflow(parsed_id, payload)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return workflow


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
def execute_workflow(workflow_id: str) -> WorkflowExecutionResponse:
    parsed_id = _parse_workflow_id(workflow_id)
    result = get_service().execute_workflow(parsed_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    if not result.get("execution_log") and not result.get("workflow_summary"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Workflow execution failed")

    return WorkflowExecutionResponse(**result)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: str) -> None:
    parsed_id = _parse_workflow_id(workflow_id)
    deleted = get_service().delete_workflow(parsed_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

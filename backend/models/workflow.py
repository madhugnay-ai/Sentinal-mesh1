from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class WorkflowBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(WorkflowBase):
    pass


class Workflow(WorkflowBase):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    workflow_id: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        name: str,
        description: str,
        nodes: list[dict],
        edges: list[dict],
        **extra_fields: object,
    ) -> "Workflow":
        now = datetime.now(timezone.utc)
        return cls(
            workflow_id=uuid4(),
            name=name,
            description=description,
            nodes=nodes,
            edges=edges,
            created_at=now,
            updated_at=now,
            **extra_fields,
        )

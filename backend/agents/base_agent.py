from __future__ import annotations

from abc import ABC, abstractmethod

from graph.state import WorkflowState


class BaseAgent(ABC):
    @abstractmethod
    def execute(self, state: WorkflowState) -> WorkflowState:
        raise NotImplementedError

    def __call__(self, state: WorkflowState) -> WorkflowState:
        return self.execute(state)

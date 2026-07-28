import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.rag_incident_memory import RAGIncidentMemoryAgent
from constants import node_types
from graph.state import WorkflowState


def test_exact_category_match_returns_best_incident() -> None:
    agent = RAGIncidentMemoryAgent()
    state: WorkflowState = {
        "failure_category": "Inventory Failure",
        "failure_severity": "High",
        "recoverable": True,
        "workflow_health": "Warning",
        "execution_log": ["Failure detected: Inventory Failure"],
    }

    result = agent.execute(state)

    assert result["incident_matches"]
    assert result["incident_matches"][0]["failure_category"] == "Inventory Failure"
    assert result["knowledge_base_match_count"] == 3
    assert result["recommended_resolution"]
    assert result["rag_summary"]


def test_severity_match_prefers_closer_severity() -> None:
    agent = RAGIncidentMemoryAgent()
    state: WorkflowState = {
        "failure_category": "Vendor Selection Failure",
        "failure_severity": "Medium",
        "recoverable": True,
        "workflow_health": "Warning",
    }

    result = agent.execute(state)

    assert result["incident_matches"]
    assert len(result["incident_matches"]) == 3
    assert all(item["failure_category"] == "Vendor Selection Failure" for item in result["incident_matches"])


def test_recoverable_match_is_considered() -> None:
    agent = RAGIncidentMemoryAgent()
    state: WorkflowState = {
        "failure_category": "Budget Failure",
        "failure_severity": "High",
        "recoverable": True,
        "workflow_health": "Warning",
    }

    result = agent.execute(state)

    assert result["incident_matches"]
    assert all(item["recoverable"] is True for item in result["incident_matches"])


def test_no_matching_incidents_returns_empty_matches() -> None:
    agent = RAGIncidentMemoryAgent()
    state: WorkflowState = {
        "failure_category": "Unsupported Failure",
        "failure_severity": "Low",
        "recoverable": False,
        "workflow_health": "Healthy",
    }

    result = agent.execute(state)

    assert result["incident_matches"] == []
    assert result["knowledge_base_match_count"] == 0
    assert result["recommended_resolution"] == "No known incident match found."


def test_top_3_retrieval_is_limited() -> None:
    agent = RAGIncidentMemoryAgent()
    state: WorkflowState = {
        "failure_category": "Inventory Failure",
        "failure_severity": "High",
        "recoverable": True,
        "workflow_health": "Warning",
    }

    result = agent.execute(state)

    assert len(result["incident_matches"]) <= 3


def test_empty_knowledge_base_returns_empty_results() -> None:
    path = Path(__file__).resolve().parents[1] / "services" / "incident_memory.py"
    if path.exists():
        import importlib
        from services.incident_memory import IncidentMemoryService

        service = IncidentMemoryService()
        service._incidents = []
        result = service.retrieve_incidents("Inventory Failure", "High", True, "Warning")
        assert result == []


def test_agent_registry_invokes_rag_incident_memory_agent() -> None:
    registry = AgentRegistry()
    agent = registry.get_agent(node_types.RAG_INCIDENT_MEMORY)

    assert agent is not None
    assert agent.__class__.__name__ == "RAGIncidentMemoryAgent"

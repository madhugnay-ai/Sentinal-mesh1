import tempfile
from pathlib import Path

from services.incident_memory import IncidentMemoryService


def test_store_and_retrieve_similar_incident(tmp_path: Path) -> None:
    temp_file = tmp_path / "incidents_test.json"
    service = IncidentMemoryService(incidents_path=temp_file)

    incident = {
        "failure_category": "Provider",
        "severity": "High",
        "recoverable": False,
        "workflow_health": "Failed",
        "symptoms": ["Missing API key", "Unauthorized"],
        "root_cause": "Credentials missing",
        "resolution": "Provide API credentials",
        "recommended_action": "Verify provider API key",
        "provider": "Groq",
        "model": "llama-3.1-8b-instant",
    }

    stored = service.store_incident(incident)
    assert stored.get("incident_id")

    matches = service.retrieve_incidents("Provider", "High", False, "Failed")
    assert matches
    assert any(m.get("incident_id") == stored.get("incident_id") for m in matches)


def test_unrelated_incident_does_not_match(tmp_path: Path) -> None:
    temp_file = tmp_path / "incidents_test2.json"
    service = IncidentMemoryService(incidents_path=temp_file)

    inv = {
        "failure_category": "Inventory Failure",
        "severity": "High",
        "recoverable": True,
        "workflow_health": "Warning",
        "symptoms": ["Out of stock"],
        "root_cause": "No stock",
        "resolution": "Switch warehouse",
    }
    service.store_incident(inv)

    matches = service.retrieve_incidents("Provider", "High", False, "Failed")
    assert matches == []


def test_retrieval_case_insensitive_and_substring(tmp_path: Path) -> None:
    temp_file = tmp_path / "incidents_test3.json"
    service = IncidentMemoryService(incidents_path=temp_file)

    inc = {
        "failure_category": "provider failure",
        "severity": "Medium",
        "recoverable": False,
        "workflow_health": "Failed",
        "symptoms": ["missing api key"],
        "root_cause": "No key",
        "resolution": "Add API key",
    }
    service.store_incident(inc)

    matches = service.retrieve_incidents("Provider", "Medium", False, "Failed")
    assert matches
    assert matches[0].get("resolution") == "Add API key"

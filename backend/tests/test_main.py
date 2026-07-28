import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_workflow() -> None:
    payload = {
        "name": "Demo Workflow",
        "description": "Test workflow",
        "nodes": [{"id": "n1", "type": "agent", "data": {"label": "Planner"}}],
        "edges": [],
    }

    response = client.post("/workflows", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == payload["name"]
    assert body["description"] == payload["description"]
    assert body["workflow_id"]


def test_read_update_delete_workflow() -> None:
    create_response = client.post(
        "/workflows",
        json={
            "name": "Editable Workflow",
            "description": "Original description",
            "nodes": [],
            "edges": [],
        },
    )
    workflow_id = create_response.json()["workflow_id"]

    read_response = client.get(f"/workflows/{workflow_id}")
    assert read_response.status_code == 200
    assert read_response.json()["name"] == "Editable Workflow"

    update_response = client.put(
        f"/workflows/{workflow_id}",
        json={"name": "Updated Workflow", "description": "Updated description", "nodes": [], "edges": []},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Workflow"

    delete_response = client.delete(f"/workflows/{workflow_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/workflows/{workflow_id}")
    assert missing_response.status_code == 404


def test_execute_workflow_endpoint() -> None:
    create_response = client.post(
        "/workflows",
        json={
            "name": "Execution Test Workflow",
            "description": "Workflow execution route test",
            "nodes": [
                {"id": "req", "type": "Requirement Validation"},
                {"id": "inv", "type": "Inventory"},
                {"id": "vendor", "type": "Vendor Selection"},
                {"id": "budget", "type": "Budget Validation"},
                {"id": "approval", "type": "Approval"},
                {"id": "po", "type": "Purchase Order"},
                {"id": "supervisor", "type": "Supervisor"},
                {"id": "failure", "type": "Failure Detection"},
                {"id": "rag", "type": "RAG Incident Memory"},
                {"id": "healing", "type": "Auto Healing"},
            ],
            "edges": [
                {"source": "req", "target": "inv"},
                {"source": "inv", "target": "vendor"},
                {"source": "vendor", "target": "budget"},
                {"source": "budget", "target": "approval"},
                {"source": "approval", "target": "po"},
                {"source": "po", "target": "supervisor"},
                {"source": "supervisor", "target": "failure"},
                {"source": "failure", "target": "rag"},
                {"source": "rag", "target": "healing"},
            ],
            "requested_items": [{"item": "Laptop", "quantity": 1}],
            "available_budget": 100000,
            "vendor_strategy": "lowest_cost",
            "approval_threshold": 50000,
        },
    )
    workflow_id = create_response.json()["workflow_id"]

    execute_response = client.post(f"/workflows/{workflow_id}/execute")

    assert execute_response.status_code == 200
    body = execute_response.json()
    assert body["execution_status"]
    assert body["workflow_health"]
    assert body["workflow_summary"]
    assert isinstance(body["completed_stages"], list)
    assert isinstance(body["failed_stages"], list)
    assert isinstance(body["incident_matches"], list)
    assert isinstance(body["recommended_resolution"], str)
    assert isinstance(body["healing_strategy"], str)
    assert isinstance(body["healing_status"], str)
    assert isinstance(body["execution_log"], list)


def test_invalid_workflow_id() -> None:
    response = client.get("/workflows/not-a-uuid")
    assert response.status_code == 400
    assert "Invalid workflow_id" in response.json()["detail"]

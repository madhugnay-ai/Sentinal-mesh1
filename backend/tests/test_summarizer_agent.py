import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.email_trigger import EmailTriggerAgent
from agents.summarizer_agent import SummarizerAgent
from services.workflow_service import WorkflowService
from graph.state import WorkflowState


def make_state(node_id: str, workflow: dict, overrides: dict | None = None) -> WorkflowState:
    state: WorkflowState = {
        "workflow_id": "wf-summarizer",
        "current_node": node_id,
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow,
        "email_subject": "Customer reported a billing outage",
        "email_body": "The billing service is failing for several customers today.",
        "input_text": "The billing service is failing for several customers today.",
    }
    if overrides:
        state.update(overrides)
    return state


def build_summarizer_node() -> dict:
    return {
        "id": "summarizer1",
        "data": {
            "kind": "summarizer",
            "label": "Summarizer",
            "provider": "Groq",
            "model": "llama-3.1-8b-instant",
            "inputField": "email_body",
            "instructions": "Summarize the incoming content clearly and concisely.",
            "temperature": 0.2,
            "maxTokens": 256,
        },
    }


def test_summarizer_agent_uses_configured_input_and_stores_summary(monkeypatch) -> None:
    import agents.summarizer_agent as summarizer_agent

    captured: dict[str, object] = {}

    def fake_generate(self, prompt, input_text, model, temperature, max_tokens, api_key=None):
        captured["input_text"] = input_text
        captured["model"] = model
        captured["temperature"] = temperature
        captured["max_tokens"] = max_tokens
        return "Summary of the billing issue."

    monkeypatch.setattr(summarizer_agent.GroqProvider, "generate_text", fake_generate)

    workflow = {"nodes": [build_summarizer_node()], "edges": []}
    state = make_state("summarizer1", workflow)

    result = SummarizerAgent().execute(state)

    assert result["execution_status"] == "completed"
    assert result["summary"] == "Summary of the billing issue."
    assert captured["input_text"] == "The billing service is failing for several customers today."
    assert captured["model"] == "llama-3.1-8b-instant"
    assert captured["temperature"] == 0.2
    assert captured["max_tokens"] == 256


def test_summarizer_workflow_service_exposes_summary(monkeypatch) -> None:
    import agents.summarizer_agent as summarizer_agent

    monkeypatch.setattr(
        summarizer_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "A concise incident summary.",
    )

    def fake_trigger_execute(self, state):
        state["email_subject"] = "Billing outage"
        state["email_body"] = "The billing service is failing for several customers today."
        state["input_text"] = state["email_body"]
        state["execution_status"] = "received"
        state.setdefault("execution_log", []).append("Email trigger injected context")
        return state

    monkeypatch.setattr(EmailTriggerAgent, "execute", fake_trigger_execute)

    service = WorkflowService()
    workflow = {
        "name": "Summarizer workflow",
        "description": "Summarizer test",
        "nodes": [
            {"id": "trigger1", "data": {"kind": "email-trigger"}},
            build_summarizer_node(),
        ],
        "edges": [{"source": "trigger1", "target": "summarizer1"}],
    }

    class Payload:
        name = workflow["name"]
        description = workflow["description"]
        nodes = workflow["nodes"]
        edges = workflow["edges"]

        def model_dump(self, exclude=None):
            return {}

    created = service.create_workflow(Payload())
    result = service.execute_workflow(created.workflow_id)

    assert result["execution_status"] == "completed"
    assert result["summary"] == "A concise incident summary."
    assert result["node_outputs"]
    assert any(entry.get("outputs", {}).get("summary") == "A concise incident summary." for entry in result["node_outputs"])
    assert result["completed_stages"] == ["Email Trigger", "Summarizer"]


def test_summarizer_failure_propagates_to_failed_nodes(monkeypatch) -> None:
    import agents.summarizer_agent as summarizer_agent

    def raise_error(self, prompt, input_text, model, temperature, max_tokens, api_key=None):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(summarizer_agent.GroqProvider, "generate_text", raise_error)

    workflow = {"nodes": [build_summarizer_node()], "edges": []}
    state = make_state("summarizer1", workflow)

    result = SummarizerAgent().execute(state)

    assert result["execution_status"] == "failed"
    assert result.get("failed_node_ids") == ["summarizer1"]
    assert any("provider unavailable" in error for error in result["errors"])

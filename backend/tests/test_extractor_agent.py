import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.extractor_agent import ExtractorAgent
from services.workflow_service import WorkflowService


def make_state(current_node: str, workflow_data: dict, initial_state: dict | None = None) -> dict:
    state = {
        "workflow_id": "wf-extractor",
        "current_node": current_node,
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow_data,
    }
    if initial_state:
        state.update(initial_state)
    return state


def build_extractor_node(
    extraction_fields=None,
    input_field: str = "email_subject_and_body",
    provider: str = "Groq",
    model: str = "llama-3.1-8b-instant",
) -> dict:
    return {
        "id": "extractor1",
        "data": {
            "kind": "extractor",
            "provider": provider,
            "model": model,
            "inputField": input_field,
            "extractionFields": ["service", "status", "location", "urgency"] if extraction_fields is None else extraction_fields,
            "instructions": "Extract the requested fields into a JSON object.",
            "temperature": 0.0,
            "maxTokens": 256,
        },
    }


def test_extractor_is_registered(monkeypatch) -> None:
    agent = AgentRegistry().get_agent("Extractor")
    assert agent is not None
    assert isinstance(agent, ExtractorAgent)


def test_extractor_executes_with_email_trigger_context(monkeypatch) -> None:
    import agents.extractor_agent as extractor_agent
    from agents.email_trigger import EmailTriggerAgent

    monkeypatch.setattr(
        extractor_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: '{"service": "payment service", "status": "unavailable"}',
    )

    def fake_trigger_execute(self, state):
        state["email_subject"] = "Payment service outage"
        state["email_body"] = "The payment service has been unavailable since 2:15 PM."
        state["input_text"] = state["email_body"]
        state["execution_status"] = "received"
        state.setdefault("execution_log", []).append("Email trigger injected context")
        return state

    monkeypatch.setattr(EmailTriggerAgent, "execute", fake_trigger_execute)

    workflow = {
        "nodes": [
            {"id": "trigger1", "data": {"kind": "email-trigger"}},
            build_extractor_node(),
        ],
        "edges": [{"source": "trigger1", "target": "extractor1"}],
    }

    state = make_state("trigger1", workflow, {"execution_status": "pending"})
    state = fake_trigger_execute(EmailTriggerAgent, {**state, "current_node": "trigger1"})
    result = ExtractorAgent().execute({**state, "current_node": "extractor1"})

    assert result["execution_status"] == "completed"
    assert result["extracted_data"]["service"] == "payment service"


def test_extractor_uses_selected_input_field(monkeypatch) -> None:
    import agents.extractor_agent as extractor_agent

    captured = {}

    def fake_generate_text(self, prompt, input_text, model, temperature, max_tokens, api_key=None):
        captured["input_text"] = input_text
        return '{"service": "checkout"}'

    monkeypatch.setattr(extractor_agent.GroqProvider, "generate_text", fake_generate_text)

    workflow = {"nodes": [build_extractor_node(input_field="email_subject")], "edges": []}
    state = make_state("extractor1", workflow, {"email_subject": "Checkout issue", "email_body": "Ignore this body"})

    ExtractorAgent().execute(state)

    assert captured["input_text"] == "Checkout issue"


def test_extractor_respects_configured_fields(monkeypatch) -> None:
    import agents.extractor_agent as extractor_agent

    monkeypatch.setattr(
        extractor_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: '{"service": "billing", "urgency": "high"}',
    )

    workflow = {"nodes": [build_extractor_node(extraction_fields=["service", "urgency"])], "edges": []}
    state = make_state("extractor1", workflow, {"input_text": "Billing escalation"})

    result = ExtractorAgent().execute(state)

    assert list(result["extracted_data"].keys()) == ["service", "urgency"]


def test_extractor_parses_markdown_fenced_json(monkeypatch) -> None:
    import agents.extractor_agent as extractor_agent

    monkeypatch.setattr(
        extractor_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: '```json\n{"service": "payment service", "status": "unavailable"}\n```',
    )

    workflow = {"nodes": [build_extractor_node(extraction_fields=["service", "status"])], "edges": []}
    state = make_state("extractor1", workflow, {"input_text": "Payment service outage"})

    result = ExtractorAgent().execute(state)

    assert result["execution_status"] == "completed"
    assert result["extracted_data"] == {"service": "payment service", "status": "unavailable"}


def test_extractor_handles_invalid_json(monkeypatch) -> None:
    import agents.extractor_agent as extractor_agent

    monkeypatch.setattr(
        extractor_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: 'not json',
    )

    workflow = {"nodes": [build_extractor_node()], "edges": []}
    state = make_state("extractor1", workflow, {"input_text": "Invalid output"})

    result = ExtractorAgent().execute(state)

    assert result["execution_status"] == "failed"
    assert any("Invalid JSON" in error for error in result["errors"])
    assert result.get("failed_node_ids") == ["extractor1"]


def test_extractor_skips_on_no_messages(monkeypatch) -> None:
    workflow = {"nodes": [build_extractor_node()], "edges": []}
    state = make_state("extractor1", workflow, {"execution_status": "no_messages"})

    result = ExtractorAgent().execute(state)

    assert result["execution_status"] == "no_messages"
    assert result["current_node"] == "extractor1"


def test_extractor_workflow_service_exposes_extracted_data(monkeypatch) -> None:
    import agents.extractor_agent as extractor_agent
    from agents.email_trigger import EmailTriggerAgent

    monkeypatch.setattr(
        extractor_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: '{"service": "payment service", "status": "unavailable"}',
    )

    def fake_trigger_execute(self, state):
        state["email_subject"] = "Payment service outage"
        state["email_body"] = "The payment service has been unavailable since 2:15 PM."
        state["input_text"] = state["email_body"]
        state["execution_status"] = "received"
        state.setdefault("execution_log", []).append("Email trigger injected context")
        return state

    monkeypatch.setattr(EmailTriggerAgent, "execute", fake_trigger_execute)

    service = WorkflowService()
    workflow = {
        "name": "Extractor workflow",
        "description": "Extractor test",
        "nodes": [
            {"id": "trigger1", "data": {"kind": "email-trigger"}},
            build_extractor_node(),
        ],
        "edges": [{"source": "trigger1", "target": "extractor1"}],
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

    assert result["extracted_data"]["service"] == "payment service"
    assert set(result["extracted_data"].keys()) == {"service", "status"}
    assert result["execution_status"] == "completed"
    assert result["extractor_fields"] == ["service", "status", "location", "urgency"]

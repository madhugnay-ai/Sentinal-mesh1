import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.classifier_agent import ClassifierAgent
from graph.graph_builder import GraphBuilder


def make_state(current_node: str, workflow_data: dict, initial_state: dict | None = None) -> dict:
    state = {
        "workflow_id": "wf-classifier",
        "current_node": current_node,
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow_data,
    }
    if initial_state:
        state.update(initial_state)
    return state


def build_classifier_node(
    categories=None,
    input_field: str = "email_subject_and_body",
    provider: str = "Groq",
    model: str = "llama-3.1-8b-instant",
) -> dict:
    return {
        "id": "classifier1",
        "data": {
            "kind": "classifier",
            "provider": provider,
            "model": model,
            "inputField": input_field,
            "categories": ["critical", "support", "general"] if categories is None else categories,
            "instructions": "Classify the incoming content into exactly one configured category.",
            "temperature": 0.0,
            "maxTokens": 128,
        },
    }


def test_classifier_agent_classifies_critical_semantically(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    monkeypatch.setattr(
        classifier_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "critical",
    )

    workflow = {"nodes": [build_classifier_node()], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": "The production server stopped responding and customers cannot place orders."})

    result = ClassifierAgent().execute(state)

    assert result["classification"] == "critical"
    assert result["execution_status"] == "completed"


def test_classifier_agent_classifies_support_semantically(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    monkeypatch.setattr(
        classifier_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "support",
    )

    workflow = {"nodes": [build_classifier_node()], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": "I cannot configure my account after the latest update and need assistance."})

    result = ClassifierAgent().execute(state)

    assert result["classification"] == "support"


def test_classifier_agent_classifies_general(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    monkeypatch.setattr(
        classifier_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "general",
    )

    workflow = {"nodes": [build_classifier_node()], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": "Please send the project status report when convenient."})

    result = ClassifierAgent().execute(state)

    assert result["classification"] == "general"


def test_classifier_agent_normalizes_case(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    monkeypatch.setattr(
        classifier_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "Critical",
    )

    workflow = {"nodes": [build_classifier_node()], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": "A production outage needs attention."})

    result = ClassifierAgent().execute(state)

    assert result["classification"] == "critical"


def test_classifier_agent_normalizes_whitespace(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    monkeypatch.setattr(
        classifier_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "  support  ",
    )

    workflow = {"nodes": [build_classifier_node()], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": "The account setup is broken."})

    result = ClassifierAgent().execute(state)

    assert result["classification"] == "support"


def test_classifier_agent_rejects_invalid_category(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    monkeypatch.setattr(
        classifier_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "billing",
    )

    workflow = {"nodes": [build_classifier_node()], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": "A billing issue needs review."})

    result = ClassifierAgent().execute(state)

    assert result["execution_status"] == "failed"
    assert any("Invalid classification" in error for error in result["errors"])


def test_classifier_agent_requires_categories(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    monkeypatch.setattr(
        classifier_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "critical",
    )

    workflow = {"nodes": [build_classifier_node(categories=[])], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": "Critical issue"})

    result = ClassifierAgent().execute(state)

    assert result["execution_status"] == "failed"
    assert any("At least one category" in error for error in result["errors"])


def test_classifier_agent_requires_input(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    monkeypatch.setattr(
        classifier_agent.GroqProvider,
        "generate_text",
        lambda self, prompt, input_text, model, temperature, max_tokens, api_key=None: "critical",
    )

    workflow = {"nodes": [build_classifier_node()], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": ""})

    result = ClassifierAgent().execute(state)

    assert result["execution_status"] == "failed"
    assert any("No input available" in error for error in result["errors"])


def test_classifier_agent_handles_provider_failure(monkeypatch) -> None:
    import agents.classifier_agent as classifier_agent

    def raise_error(self, prompt, input_text, model, temperature, max_tokens, api_key=None):
        raise ValueError("provider unavailable")

    monkeypatch.setattr(classifier_agent.GroqProvider, "generate_text", raise_error)

    workflow = {"nodes": [build_classifier_node()], "edges": []}
    state = make_state("classifier1", workflow, {"input_text": "A support issue needs review."})

    result = ClassifierAgent().execute(state)

    assert result["execution_status"] == "failed"
    assert any("provider unavailable" in error for error in result["errors"])


def test_classifier_graph_builder_executes_only_selected_branch(monkeypatch) -> None:
    class DummyAgent:
        def __init__(self) -> None:
            self.executed_nodes: list[str] = []

        def execute(self, state):
            self.executed_nodes.append(state["current_node"])
            state.setdefault("execution_log", []).append("dummy executed")
            state["execution_status"] = "completed"
            return state

    dummy_agent = DummyAgent()
    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Classifier":
            return ClassifierAgent()
        if node_type == "Send Email":
            return dummy_agent
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-classifier-branch",
        "nodes": [
            {
                "id": "classifier1",
                "data": {
                    "kind": "classifier",
                    "provider": "Groq",
                    "model": "llama-3.1-8b-instant",
                    "inputField": "input_text",
                    "categories": ["critical", "support", "general"],
                },
            },
            {"id": "critical_target", "data": {"kind": "send-email"}},
            {"id": "support_target", "data": {"kind": "send-email"}},
            {"id": "general_target", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "classifier1", "sourceHandle": "critical", "target": "critical_target"},
            {"source": "classifier1", "sourceHandle": "support", "target": "support_target"},
            {"source": "classifier1", "sourceHandle": "general", "target": "general_target"},
        ],
    }

    for classification in ["critical", "support", "general"]:
        dummy_agent.executed_nodes = []
        state = make_state("classifier1", workflow, {
            "input_text": "The production server is down.",
            "execution_status": "pending",
        })

        monkeypatch.setattr(ClassifierAgent, "execute", lambda self, state, classification=classification: {
            **state,
            "classification": classification,
            "classifier_categories": ["critical", "support", "general"],
            "execution_status": "completed",
            "execution_log": state.get("execution_log", []) + [f"Classifier completed: category={classification}"],
        })

        graph = builder.build_graph(workflow)
        final_state = graph.invoke(state)

        expected_target = f"{classification}_target"
        unexpected_targets = [name for name in ["critical_target", "support_target", "general_target"] if name != expected_target]

        assert final_state["classification"] == classification
        assert expected_target in dummy_agent.executed_nodes
        for unexpected_target in unexpected_targets:
            assert unexpected_target not in dummy_agent.executed_nodes


def test_classifier_graph_builder_terminates_safely_for_unmapped_category(monkeypatch) -> None:
    class DummyAgent:
        def __init__(self) -> None:
            self.executed_nodes: list[str] = []

        def execute(self, state):
            self.executed_nodes.append(state["current_node"])
            state.setdefault("execution_log", []).append("dummy executed")
            state["execution_status"] = "completed"
            return state

    dummy_agent = DummyAgent()
    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Classifier":
            return ClassifierAgent()
        if node_type == "Send Email":
            return dummy_agent
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-classifier-end",
        "nodes": [
            {
                "id": "classifier1",
                "data": {
                    "kind": "classifier",
                    "provider": "Groq",
                    "model": "llama-3.1-8b-instant",
                    "inputField": "input_text",
                    "categories": ["critical", "support", "general"],
                },
            },
            {"id": "critical_target", "data": {"kind": "send-email"}},
            {"id": "support_target", "data": {"kind": "send-email"}},
            {"id": "general_target", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "classifier1", "sourceHandle": "critical", "target": "critical_target"},
            {"source": "classifier1", "sourceHandle": "support", "target": "support_target"},
            {"source": "classifier1", "sourceHandle": "general", "target": "general_target"},
        ],
    }

    state = make_state("classifier1", workflow, {
        "input_text": "The production server is down.",
        "execution_status": "pending",
    })

    monkeypatch.setattr(ClassifierAgent, "execute", lambda self, state: {
        **state,
        "classification": "billing",
        "classifier_categories": ["critical", "support", "general"],
        "execution_status": "completed",
        "execution_log": state.get("execution_log", []) + ["Classifier completed: category=billing"],
    })

    graph = builder.build_graph(workflow)
    final_state = graph.invoke(state)

    assert final_state["classification"] == "billing"
    assert "critical_target" not in dummy_agent.executed_nodes
    assert "support_target" not in dummy_agent.executed_nodes
    assert "general_target" not in dummy_agent.executed_nodes

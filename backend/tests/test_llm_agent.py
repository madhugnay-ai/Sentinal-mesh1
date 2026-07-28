from agents.llm_agent import LLMAgent


def test_llm_agent_uses_provider_and_stores_response(monkeypatch) -> None:
    agent = LLMAgent()

    class FakeProvider:
        def generate_text(self, prompt: str, input_text: str, model: str, temperature: float, max_tokens: int, api_key: str | None = None) -> str:
            assert prompt == "Summarize this email"
            assert input_text == "Invoice ready for approval"
            assert model == "gpt-4.1-mini"
            assert temperature == 0.2
            assert max_tokens == 200
            return "A concise summary"

    monkeypatch.setattr(agent, "_get_provider", lambda provider_name: FakeProvider())

    state = {
        "workflow_data": {
            "nodes": [
                {
                    "id": "llm-1",
                    "data": {
                        "kind": "llm",
                        "provider": "OpenAI",
                        "model": "gpt-4.1-mini",
                        "prompt": "Summarize this email",
                        "temperature": 0.2,
                        "maxTokens": 200,
                    },
                }
            ]
        },
        "current_node": "llm-1",
        "email_messages": [{"body": "Invoice ready for approval"}],
    }

    result = agent.execute(state)

    assert result["llm_output"] == "A concise summary"
    assert result["llm_provider"] == "OpenAI"
    assert result["execution_status"] == "completed"


def test_llm_agent_records_errors_for_provider_failure(monkeypatch) -> None:
    agent = LLMAgent()

    class FailingProvider:
        def generate_text(self, prompt: str, input_text: str, model: str, temperature: float, max_tokens: int, api_key: str | None = None) -> str:
            raise ValueError("Invalid API key")

    monkeypatch.setattr(agent, "_get_provider", lambda provider_name: FailingProvider())

    state = {
        "workflow_data": {
            "nodes": [
                {
                    "id": "llm-2",
                    "data": {
                        "kind": "llm",
                        "provider": "Gemini",
                        "model": "gemini-2.0-flash",
                        "prompt": "Summarize this email",
                        "temperature": 0.1,
                        "maxTokens": 100,
                    },
                }
            ]
        },
        "current_node": "llm-2",
        "email_messages": [{"body": "Customer request"}],
    }

    result = agent.execute(state)

    assert result["execution_status"] == "failed"
    assert any("Invalid API key" in error for error in result["errors"])

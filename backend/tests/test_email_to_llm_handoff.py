import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.email_trigger import EmailTriggerAgent
from agents.llm_agent import LLMAgent, GroqProvider


def test_email_to_llm_handoff(monkeypatch) -> None:
    # Prepare fake messages returned by GmailService via EmailTrigger._fetch_emails
    messages = [
        {"message_id": "m1", "sender": "a@example.com", "recipient": "me@example.com", "subject": "Old", "body": "Old message", "received_at": "2020-01-01T00:00:00Z", "unread": True},
        {"message_id": "m2", "sender": "b@example.com", "recipient": "me@example.com", "subject": "New", "body": "Selected message body", "received_at": "2020-01-02T00:00:00Z", "unread": True},
    ]

    # Monkeypatch EmailTriggerAgent._fetch_emails to return our messages
    monkeypatch.setattr(EmailTriggerAgent, "_fetch_emails", lambda self, cfg: messages)

    email_agent = EmailTriggerAgent()
    state = {
        "workflow_data": {"nodes": [{"id": "email1", "data": {"kind": "email-trigger"}}, {"id": "llm1", "data": {"kind": "llm", "provider": "Groq", "model": "llama-3.1-8b-instant", "prompt": "Do something"}}], "edges": [{"source": "email1", "target": "llm1"}]},
        "current_node": "email1",
        "execution_log": [],
        "execution_status": "pending",
    }

    # Run email trigger
    result = email_agent.execute(state)

    assert result["email_message_id"] == "m2"
    assert result["email_body"] == "Selected message body"
    assert result["input_text"] == "Selected message body"

    # Now monkeypatch GroqProvider.generate_text to capture the passed input_text
    captured = {}

    def fake_generate_text(self, prompt, input_text, model, temperature, max_tokens, api_key=None):
        captured["input_text"] = input_text
        return "fake-response"

    monkeypatch.setattr(GroqProvider, "generate_text", fake_generate_text)

    llm_agent = LLMAgent()
    # set current_node to the llm node and run
    result["current_node"] = "llm1"
    llm_result = llm_agent.execute(result)

    assert llm_result["llm_output"] == "fake-response"
    # Ensure provider received the exact input_text from EmailTrigger
    assert captured.get("input_text") == "Selected message body"
    # Ensure our safe log entry exists
    assert any("LLM input prepared:" in entry for entry in llm_result.get("execution_log", []))

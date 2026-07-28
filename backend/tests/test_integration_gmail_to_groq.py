import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from agents.email_trigger import EmailTriggerAgent
from agents.llm_agent import LLMAgent, GroqProvider
from agents.agent_registry import AgentRegistry


def test_full_handoff_gmail_to_groq(monkeypatch) -> None:
    # Mock GmailService.fetch_messages to return a single normalized message dict
    message_body = "The project review meeting is Friday at 3 PM. Complete API integration and testing before the meeting."

    def fake_fetch(self, account=None, label=None, unread_only=False, subject_filter=None, max_results=5):
        return [
            {
                "message_id": "test-msg-1",
                "sender": "alice@example.com",
                "recipient": "me@example.com",
                "subject": "SentinelMesh Workflow Test",
                "body": message_body,
                "received_at": "2026-07-28T00:00:00Z",
                "unread": True,
            }
        ]

    monkeypatch.setattr("agents.email_trigger.EmailTriggerAgent._fetch_emails", fake_fetch)

    # capture input_text passed to GroqProvider.generate_text
    captured = {}

    def fake_generate_text(self, prompt, input_text, model, temperature, max_tokens, api_key=None):
        captured["input_text"] = input_text
        return "summarized"

    monkeypatch.setattr(GroqProvider, "generate_text", fake_generate_text)

    # Build workflow: email1 -> llm1
    email_agent = EmailTriggerAgent()
    state = {
        "workflow_data": {"nodes": [{"id": "email1", "data": {"kind": "email-trigger"}}, {"id": "llm1", "data": {"kind": "llm", "provider": "Groq", "model": "llama-3.1-8b-instant", "prompt": "Summarize the incoming email in 2-3 sentences."}}], "edges": [{"source": "email1", "target": "llm1"}]},
        "current_node": "email1",
        "execution_log": [],
        "execution_status": "pending",
    }

    # run email trigger
    result = email_agent.execute(state)

    assert result["email_message_id"] == "test-msg-1"
    assert result["email_body"] == message_body
    assert result["input_text"] == message_body

    # run llm
    result["current_node"] = "llm1"
    llm = LLMAgent()
    out = llm.execute(result)

    assert out["llm_output"] == "summarized"
    assert captured.get("input_text") == message_body
    # ensure LLM logged safe diagnostics
    assert any("LLM input prepared:" in entry for entry in out.get("execution_log", []))
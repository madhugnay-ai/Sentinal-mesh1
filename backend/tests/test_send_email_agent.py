import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.send_email_agent import SendEmailAgent
from graph.state import WorkflowState


class DummySMTP:
    started_tls = False

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged_in = False
        self.sent_message = None
        self.tls_started = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        self.tls_started = True
        type(self).started_tls = True

    def login(self, username, password):
        self.logged_in = True

    def send_message(self, message):
        self.sent_message = message

    def quit(self):
        return None


def make_state() -> WorkflowState:
    return {
        "workflow_data": {
            "nodes": [
                {
                    "id": "send-email-1",
                    "data": {
                        "recipientEmail": "recipient@example.com",
                        "subject": "Test subject",
                        "body": "Fallback body",
                        "useLlmOutput": True,
                    },
                }
            ]
        },
        "current_node": "send-email-1",
        "llm_output": "LLM generated summary",
        "recipient_email": "recipient@example.com",
        "email_subject": "Workflow update",
    }


def test_successful_email_send(monkeypatch: pytest.MonkeyPatch) -> None:
    DummySMTP.started_tls = False
    monkeypatch.setattr("agents.send_email_agent.smtplib.SMTP", DummySMTP)
    # ensure Gmail API is not used in this SMTP-focused test
    class NoGmail:
        def can_send(self) -> bool:
            return False

        def is_connected(self) -> bool:
            return False

    monkeypatch.setattr("agents.send_email_agent.GmailService", NoGmail)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    monkeypatch.setenv("SMTP_FROM", "sender@example.com")

    agent = SendEmailAgent()
    state = make_state()

    result = agent.execute(state)

    assert result["email_sent"] is True
    assert result["email_status"] == "sent"
    assert result["email_sent_at"]
    assert result["email_error"] in (None, "")
    assert DummySMTP.started_tls is True


def test_gmail_api_send_path(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeGmailService:
        def __init__(self) -> None:
            self.sent_message = None

        def can_send(self) -> bool:
            return True

        def send_message(self, message) -> dict[str, str]:
            self.sent_message = message
            return {"id": "sent-message-id"}

    monkeypatch.setattr("agents.send_email_agent.GmailService", FakeGmailService)

    agent = SendEmailAgent()
    state = make_state()

    result = agent.execute(state)

    assert result["email_sent"] is True
    assert result["email_status"] == "sent"
    assert result["email_error"] in (None, "")
    assert result["execution_log"][-1].endswith("via Gmail API.")


def test_authentication_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class AuthFailSMTP:
        def __init__(self, host, port, timeout=None):
            raise RuntimeError("boom")

    monkeypatch.setattr("agents.send_email_agent.smtplib.SMTP", AuthFailSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    monkeypatch.setenv("SMTP_FROM", "sender@example.com")
    class NoGmail:
        def can_send(self) -> bool:
            return False

        def is_connected(self) -> bool:
            return False

    monkeypatch.setattr("agents.send_email_agent.GmailService", NoGmail)

    agent = SendEmailAgent()
    state = make_state()

    result = agent.execute(state)

    assert result["email_sent"] is False
    assert result["email_status"] == "failed"
    assert "auth" in str(result["email_error"]).lower()


def test_invalid_recipient() -> None:
    agent = SendEmailAgent()
    state = make_state()
    state["recipient_email"] = "not-an-email"

    result = agent.execute(state)

    assert result["email_sent"] is False
    assert result["email_status"] == "failed"
    assert "recipient" in str(result["email_error"]).lower()


def test_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class TimeoutSMTP:
        def __init__(self, host, port, timeout=None):
            raise TimeoutError("timed out")

    monkeypatch.setattr("agents.send_email_agent.smtplib.SMTP", TimeoutSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    monkeypatch.setenv("SMTP_FROM", "sender@example.com")
    class NoGmail:
        def can_send(self) -> bool:
            return False

        def is_connected(self) -> bool:
            return False

    monkeypatch.setattr("agents.send_email_agent.GmailService", NoGmail)

    agent = SendEmailAgent()
    state = make_state()

    result = agent.execute(state)

    assert result["email_sent"] is False
    assert result["email_status"] == "failed"
    assert "timeout" in str(result["email_error"]).lower()

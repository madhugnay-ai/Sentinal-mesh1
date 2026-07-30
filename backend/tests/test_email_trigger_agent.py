from agents.email_trigger import EmailTriggerAgent


def _build_state() -> dict:
    return {
        "workflow_data": {
            "nodes": [
                {
                    "id": "email-trigger-1",
                    "data": {
                        "kind": "email-trigger",
                        "emailAccount": "demo@example.com",
                        "folder": "INBOX",
                        "unreadOnly": True,
                        "subjectFilter": "Invoice",
                    },
                }
            ]
        },
        "current_node": "email-trigger-1",
    }


def test_email_trigger_agent_collects_email_and_populates_state(monkeypatch) -> None:
    agent = EmailTriggerAgent()

    sample_messages = [
        {
            "message_id": "msg-1",
            "sender": "ops@example.com",
            "recipient": "demo@example.com",
            "subject": "Invoice ready",
            "body": "Your invoice is attached.",
            "received_at": "2026-07-24T10:00:00Z",
            "unread": True,
        }
    ]

    monkeypatch.setattr(agent, "_fetch_emails", lambda config: sample_messages)

    result = agent.execute(_build_state())

    assert result["email_messages"][0]["sender"] == "ops@example.com"
    assert result["email_messages"][0]["subject"] == "Invoice ready"
    assert result["email_messages"][0]["body"] == "Your invoice is attached."
    assert result["email_messages"][0]["received_at"] == "2026-07-24T10:00:00Z"
    assert result["email_message_id"] == "msg-1"
    assert result["email_sender"] == "ops@example.com"
    assert result["email_recipient"] == "demo@example.com"
    assert result["email_subject"] == "Invoice ready"
    assert result["email_body"] == "Your invoice is attached."
    assert result["email_received_at"] == "2026-07-24T10:00:00Z"
    assert result["input_text"] == "Your invoice is attached."
    assert result["execution_status"] == "received"


def test_email_trigger_agent_respects_unread_only_filter(monkeypatch) -> None:
    agent = EmailTriggerAgent()
    messages = [
        {"message_id": "msg-1", "sender": "ops@example.com", "subject": "Invoice ready", "body": "A", "unread": True},
        {"message_id": "msg-2", "sender": "ops@example.com", "subject": "Invoice ready", "body": "B", "unread": False},
    ]

    monkeypatch.setattr(agent, "_fetch_emails", lambda config: messages)

    result = agent.execute(_build_state())

    assert len(result["email_messages"]) == 1
    assert result["email_messages"][0]["message_id"] == "msg-1"


def test_email_trigger_agent_applies_subject_filter(monkeypatch) -> None:
    agent = EmailTriggerAgent()
    messages = [
        {"message_id": "msg-1", "sender": "ops@example.com", "subject": "Invoice ready", "body": "A"},
        {"message_id": "msg-2", "sender": "ops@example.com", "subject": "Alert", "body": "B"},
    ]

    monkeypatch.setattr(agent, "_fetch_emails", lambda config: messages)

    result = agent.execute(_build_state())

    assert len(result["email_messages"]) == 1
    assert result["email_messages"][0]["subject"] == "Invoice ready"


def test_email_trigger_agent_selects_newest_matching_email(monkeypatch) -> None:
    agent = EmailTriggerAgent()
    messages = [
        {"message_id": "msg-1", "sender": "ops@example.com", "recipient": "demo@example.com", "subject": "Invoice ready", "body": "Older message", "received_at": "2026-07-24T09:00:00Z", "unread": True},
        {"message_id": "msg-2", "sender": "ops@example.com", "recipient": "demo@example.com", "subject": "Invoice ready", "body": "Newest message", "received_at": "2026-07-24T10:00:00Z", "unread": True},
    ]

    monkeypatch.setattr(agent, "_fetch_emails", lambda config: messages)

    result = agent.execute(_build_state())

    assert result["email_message_id"] == "msg-2"
    assert result["email_subject"] == "Invoice ready"
    assert result["email_body"] == "Newest message"
    assert result["input_text"] == "Newest message"
    assert result["execution_status"] == "received"
    assert any("Email trigger matched:" in entry for entry in result["execution_log"]) or any(
        "Email trigger matched:" in entry for entry in result.get("execution_log", [])
    )


def test_email_trigger_agent_prefers_gmail_internal_date_over_api_order(monkeypatch) -> None:
    agent = EmailTriggerAgent()
    messages = [
        {
            "message_id": "msg-older",
            "sender": "ops@example.com",
            "recipient": "demo@example.com",
            "subject": "Invoice ready",
            "body": "Older message",
            "internalDate": "1710000000000",
            "unread": True,
        },
        {
            "message_id": "msg-newer",
            "sender": "ops@example.com",
            "recipient": "demo@example.com",
            "subject": "Invoice ready",
            "body": "Newest message",
            "internalDate": "1720000000000",
            "unread": True,
        },
    ]

    monkeypatch.setattr(agent, "_fetch_emails", lambda config: messages)

    result = agent.execute(_build_state())

    assert result["email_message_id"] == "msg-newer"
    assert result["email_body"] == "Newest message"
    assert any("Selected subject: Invoice ready" in entry for entry in result["execution_log"])


def test_email_trigger_agent_only_sets_one_input_text_value(monkeypatch) -> None:
    agent = EmailTriggerAgent()
    messages = [
        {"message_id": "msg-1", "sender": "ops@example.com", "recipient": "demo@example.com", "subject": "Invoice ready", "body": "First", "received_at": "2026-07-24T09:00:00Z", "unread": True},
        {"message_id": "msg-2", "sender": "ops@example.com", "recipient": "demo@example.com", "subject": "Invoice ready", "body": "Second", "received_at": "2026-07-24T10:00:00Z", "unread": True},
    ]

    monkeypatch.setattr(agent, "_fetch_emails", lambda config: messages)

    result = agent.execute(_build_state())

    assert result["input_text"] == "Second"
    assert result["email_message_id"] == "msg-2"
    assert len(result["email_messages"]) == 2


def test_email_trigger_agent_returns_no_messages_when_none_match(monkeypatch) -> None:
    agent = EmailTriggerAgent()
    monkeypatch.setattr(agent, "_fetch_emails", lambda config: [])

    result = agent.execute(_build_state())

    assert result["email_messages"] == []
    assert result["execution_status"] == "no_messages"
    assert result["input_text"] == ""


def test_email_trigger_agent_handles_authentication_failure(monkeypatch) -> None:
    agent = EmailTriggerAgent()

    class AuthError(Exception):
        pass

    monkeypatch.setattr(agent, "_fetch_emails", lambda config: (_ for _ in ()).throw(AuthError("auth failed")))

    result = agent.execute(_build_state())

    assert result["execution_status"] == "failed"
    assert "auth failed" in result["errors"][0]


def test_email_trigger_agent_handles_malformed_messages(monkeypatch) -> None:
    agent = EmailTriggerAgent()
    malformed_messages = [{"message_id": "msg-1", "body": None}]
    monkeypatch.setattr(agent, "_fetch_emails", lambda config: malformed_messages)

    result = agent.execute(_build_state())

    assert result["email_messages"][0]["body"] == ""
    assert result["execution_status"] == "received"

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from agents.base_agent import BaseAgent
from graph.state import WorkflowState
from services.gmail_service import GmailService

logger = logging.getLogger(__name__)


class EmailTriggerAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id
        self._gmail_service = GmailService()

    def _fetch_emails(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        if not self._gmail_service.client_id or not self._gmail_service.client_secret:
            raise ValueError("Google OAuth credentials are not configured")

        max_messages = max(1, min(int((config.get("maxMessages") or 5)), 5))
        logger.info("Email trigger requesting Gmail messages", extra={"max_messages": max_messages})
        started_at = time.perf_counter()
        messages = self._gmail_service.fetch_messages(
            account=config.get("emailAccount"),
            label=config.get("folder"),
            unread_only=bool(config.get("unreadOnly", True)),
            subject_filter=config.get("subjectFilter"),
            max_results=max_messages,
        )
        logger.info("Email trigger completed Gmail fetch", extra={"message_count": len(messages), "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2)})
        return messages

    def execute(self, state: WorkflowState) -> WorkflowState:
        workflow_data = state.get("workflow_data") or {}
        nodes = workflow_data.get("nodes") or []
        node_config: dict[str, Any] | None = None

        for node in nodes if isinstance(nodes, list) else []:
            if isinstance(node, dict) and node.get("id") == state.get("current_node"):
                data = node.get("data") if isinstance(node.get("data"), dict) else {}
                node_config = data
                break

        config = {
            "emailAccount": (node_config or {}).get("emailAccount") if node_config else None,
            "folder": (node_config or {}).get("folder") or "INBOX",
            "unreadOnly": (node_config or {}).get("unreadOnly", True),
            "subjectFilter": (node_config or {}).get("subjectFilter") or "",
            "maxMessages": 5,
        }

        try:
            messages = self._fetch_emails(config)
        except Exception as exc:  # pragma: no cover - defensive for mocked and runtime failures
            state["errors"] = [str(exc)]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Email trigger failed: {exc}"
            )
            return state

        filtered_messages: list[dict[str, Any]] = []

        for message in messages if isinstance(messages, list) else []:
            if not isinstance(message, dict):
                continue

            subject = str(message.get("subject") or "")
            unread = bool(message.get("unread", True))

            normalized_message = {
                "message_id": message.get("message_id"),
                "sender": message.get("sender") or "",
                "recipient": message.get("recipient") or "",
                "subject": message.get("subject") or "",
                "body": message.get("body") or "",
                "received_at": message.get("received_at") or message.get("receivedTime") or "",
                "unread": unread,
            }

            is_malformed = not any(
                [
                    normalized_message["sender"],
                    normalized_message["recipient"],
                    normalized_message["subject"],
                    normalized_message["body"],
                ]
            )
            if config.get("subjectFilter") and config["subjectFilter"].lower() not in subject.lower() and not is_malformed:
                continue
            if config.get("unreadOnly", True) and not unread and not is_malformed:
                continue

            normalized_message = {
                "message_id": message.get("message_id"),
                "sender": message.get("sender") or "",
                "recipient": message.get("recipient") or "",
                "subject": message.get("subject") or "",
                "body": message.get("body") or "",
                "received_at": message.get("received_at") or message.get("receivedTime") or "",
                "unread": unread,
            }
            if (
                not normalized_message["message_id"]
                and not normalized_message["sender"]
                and not normalized_message["subject"]
                and not normalized_message["body"]
            ):
                continue
            filtered_messages.append(normalized_message)

        state["email_messages"] = filtered_messages
        state["email_trigger_config"] = config
        if filtered_messages:
            # select the newest message by received_at
            selected_message = max(
                filtered_messages,
                key=lambda message: str(message.get("received_at") or ""),
            )
            body_text = selected_message.get("body") or ""
            state["email_message_id"] = selected_message.get("message_id")
            state["email_sender"] = selected_message.get("sender")
            state["email_recipient"] = selected_message.get("recipient")
            state["email_subject"] = selected_message.get("subject")
            state["email_body"] = body_text
            state["email_received_at"] = selected_message.get("received_at") or ""
            state["input_text"] = body_text
            # safe diagnostic: do not log bodies, only lengths
            body_chars = len(body_text)
            input_chars = len(str(state.get("input_text") or ""))
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Email trigger selected 1 email for processing: body_chars={body_chars} input_chars={input_chars}"
            )
        else:
            state["email_message_id"] = None
            state["email_sender"] = None
            state["email_recipient"] = None
            state["email_subject"] = None
            state["email_body"] = None
            state["email_received_at"] = None
            state["input_text"] = ""
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Email trigger found no matching messages."
            )

        state["execution_status"] = "received" if filtered_messages else "no_messages"
        return state

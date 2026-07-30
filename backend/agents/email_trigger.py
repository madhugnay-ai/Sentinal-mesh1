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

    def _get_timestamp_value(self, message: dict[str, Any]) -> int | None:
        for key in ("timestamp_ms", "internalDate", "received_at", "receivedTime"):
            value = message.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    continue
                if stripped.isdigit():
                    return int(stripped)
        return None

    def _select_newest_message(self, messages: list[dict[str, Any]]) -> dict[str, Any] | None:
        timestamped_messages = [message for message in messages if self._get_timestamp_value(message) is not None]
        if timestamped_messages:
            return max(timestamped_messages, key=lambda message: self._get_timestamp_value(message) or 0)

        fallback_messages = [message for message in messages if isinstance(message, dict)]
        if not fallback_messages:
            return None

        return max(
            fallback_messages,
            key=lambda message: str(message.get("received_at") or message.get("receivedTime") or message.get("internalDate") or ""),
        )

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
                "received_at": message.get("received_at") or message.get("receivedTime") or message.get("internalDate") or "",
                "internalDate": message.get("internalDate") or message.get("received_at") or message.get("receivedTime") or "",
                "timestamp_ms": self._get_timestamp_value(message),
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
            selected_message = self._select_newest_message(filtered_messages)
            if selected_message is None:
                selected_message = filtered_messages[0]
            body_text = selected_message.get("body") or ""
            selected_timestamp = str(
                selected_message.get("internalDate")
                or selected_message.get("received_at")
                or selected_message.get("receivedTime")
                or ""
            )
            state["email_message_id"] = selected_message.get("message_id")
            state["email_sender"] = selected_message.get("sender")
            state["email_recipient"] = selected_message.get("recipient")
            state["email_subject"] = selected_message.get("subject")
            state["email_body"] = body_text
            state["email_received_at"] = selected_timestamp
            state["input_text"] = body_text
            body_chars = len(body_text)
            input_chars = len(str(state.get("input_text") or ""))
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Email trigger matched: {len(filtered_messages)}; Selected subject: {selected_message.get('subject') or ''}; Selected internalDate/timestamp: {selected_timestamp}; body_chars={body_chars}; input_chars={input_chars}"
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
                f"{datetime.now(timezone.utc).isoformat()} Email trigger matched: 0; Selected subject: <none>; Selected internalDate/timestamp: <none>; body_chars=0; input_chars=0"
            )

        state["execution_status"] = "received" if filtered_messages else "no_messages"
        return state

from __future__ import annotations

import os
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from agents.base_agent import BaseAgent
from graph.state import WorkflowState
from services.gmail_service import GmailService


class SendEmailAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def _get_node_config(self, state: WorkflowState) -> dict[str, Any]:
        workflow_data = state.get("workflow_data") or {}
        nodes = workflow_data.get("nodes") or []

        for node in nodes if isinstance(nodes, list) else []:
            if isinstance(node, dict) and node.get("id") == state.get("current_node"):
                data = node.get("data") if isinstance(node.get("data"), dict) else {}
                return dict(data)

        return {}

    def _resolve_body(self, state: WorkflowState, config: dict[str, Any]) -> str:
        if state.get("llm_output") and bool(config.get("useLlmOutput", True)):
            return str(state["llm_output"])
        return str(config.get("body") or "")

    def _validate_recipient(self, recipient: str) -> bool:
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", recipient))

    def _build_message(self, recipient: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        return message

    def execute(self, state: WorkflowState) -> WorkflowState:
        config = self._get_node_config(state)
        recipient = str(state.get("recipient_email") or config.get("recipientEmail") or "").strip()
        subject = str(state.get("email_subject") or config.get("subject") or "SentinelMesh Notification").strip()
        body = self._resolve_body(state, config)

        if not self._validate_recipient(recipient):
            state["email_sent"] = False
            state["email_sent_at"] = None
            state["email_status"] = "failed"
            state["email_error"] = "Invalid recipient email address."
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Send Email failed: invalid recipient."
            )
            return state

        message = self._build_message(recipient, subject, body)
        gmail_service = GmailService()

        if gmail_service.can_send():
            try:
                gmail_service.send_message(message)
            except (ValueError, OSError) as exc:
                state["email_sent"] = False
                state["email_sent_at"] = None
                state["email_status"] = "failed"
                state["email_error"] = str(exc)
                state.setdefault("execution_log", []).append(
                    f"{datetime.now(timezone.utc).isoformat()} Send Email failed via Gmail API: {exc}"
                )
                return state
            except Exception as exc:  # pragma: no cover - defensive for network failures
                state["email_sent"] = False
                state["email_sent_at"] = None
                state["email_status"] = "failed"
                state["email_error"] = str(exc)
                state.setdefault("execution_log", []).append(
                    f"{datetime.now(timezone.utc).isoformat()} Send Email failed via Gmail API: {exc}"
                )
                return state

            state["email_sent"] = True
            state["email_sent_at"] = datetime.now(timezone.utc).isoformat()
            state["email_status"] = "sent"
            state["email_error"] = None
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Send Email completed for {recipient} via Gmail API."
            )
            return state

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587") or "587")
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", "")

        if not smtp_host or not smtp_from:
            state["email_sent"] = False
            state["email_sent_at"] = None
            state["email_status"] = "failed"
            state["email_error"] = "SMTP configuration is incomplete."
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Send Email failed: missing SMTP configuration."
            )
            return state

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp_client:
                if smtp_username and smtp_password:
                    smtp_client.starttls()
                    smtp_client.login(smtp_username, smtp_password)
                smtp_client.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            state["email_sent"] = False
            state["email_sent_at"] = None
            state["email_status"] = "failed"
            state["email_error"] = f"SMTP authentication failed: {exc}"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Send Email failed: authentication error."
            )
            return state
        except TimeoutError as exc:
            state["email_sent"] = False
            state["email_sent_at"] = None
            state["email_status"] = "failed"
            state["email_error"] = f"SMTP timeout: {exc}"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Send Email failed: timeout."
            )
            return state
        except smtplib.SMTPConnectError as exc:
            state["email_sent"] = False
            state["email_sent_at"] = None
            state["email_status"] = "failed"
            state["email_error"] = f"SMTP connection failed: {exc}"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Send Email failed: connection error."
            )
            return state
        except (smtplib.SMTPException, OSError, ValueError) as exc:
            state["email_sent"] = False
            state["email_sent_at"] = None
            state["email_status"] = "failed"
            state["email_error"] = str(exc)
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Send Email failed: {exc}"
            )
            return state
        except Exception as exc:
            state["email_sent"] = False
            state["email_sent_at"] = None
            state["email_status"] = "failed"
            state["email_error"] = f"SMTP authentication failed: {exc}"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Send Email failed: unexpected SMTP error."
            )
            return state

        state["email_sent"] = True
        state["email_sent_at"] = datetime.now(timezone.utc).isoformat()
        state["email_status"] = "sent"
        state["email_error"] = None
        state.setdefault("execution_log", []).append(
            f"{datetime.now(timezone.utc).isoformat()} Send Email completed for {recipient}."
        )
        return state

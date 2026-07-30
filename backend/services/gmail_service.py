from __future__ import annotations

import base64
import json
import logging
import os
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GmailService:
    READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
    SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

    def __init__(self, token_store_path: str | None = None) -> None:
        self.token_store_path = Path(token_store_path or os.getenv("GMAIL_TOKEN_PATH", ".gmail_tokens.json"))
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
        self._tokens: dict[str, Any] | None = None

    def _load_tokens(self) -> dict[str, Any]:
        if self._tokens is not None:
            return self._tokens
        if not self.token_store_path.exists():
            return {}
        try:
            with self.token_store_path.open("r", encoding="utf-8") as handle:
                self._tokens = json.load(handle)
                return self._tokens
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_tokens(self, tokens: dict[str, Any]) -> None:
        self._tokens = tokens
        try:
            with self.token_store_path.open("w", encoding="utf-8") as handle:
                json.dump(tokens, handle, indent=2)
        except OSError:
            return

    def clear_tokens(self) -> None:
        self._tokens = None
        try:
            if self.token_store_path.exists():
                self.token_store_path.unlink()
        except OSError:
            return

    def is_connected(self) -> bool:
        tokens = self._load_tokens()
        return bool(tokens.get("access_token") or tokens.get("refresh_token"))

    def can_send(self) -> bool:
        tokens = self._load_tokens()
        return self.is_connected() and self._token_has_scope(tokens)

    def _scope_string(self) -> str:
        return f"{self.READONLY_SCOPE} {self.SEND_SCOPE}"

    def _token_has_scope(self, tokens: dict[str, Any] | None = None) -> bool:
        token_data = tokens or self._load_tokens()
        scopes = token_data.get("scope", "")
        if isinstance(scopes, str):
            return self.SEND_SCOPE in scopes.split()
        return False

    def _ensure_send_scope(self) -> None:
        tokens = self._load_tokens()
        if not tokens:
            raise ValueError("Gmail authentication is not configured")
        if not self._token_has_scope(tokens):
            raise ValueError("Gmail OAuth authorization must be repeated to include the gmail.send scope")

    def get_auth_url(self) -> str:
        if not self.client_id or not self.redirect_uri:
            raise ValueError("Google OAuth credentials are not configured")
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self._scope_string(),
            "access_type": "offline",
            "prompt": "consent",
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + "&".join(
            f"{key}={value}" for key, value in params.items()
        )

    def exchange_code(self, code: str) -> dict[str, Any]:
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise ValueError("Google OAuth credentials are not configured")
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        with httpx.Client(timeout=15.0) as client:
            response = client.post("https://oauth2.googleapis.com/token", data=payload)
            response.raise_for_status()
            token_data = response.json()
        if token_data.get("expires_in"):
            token_data["expires_at"] = int(time.time()) + int(token_data["expires_in"])
        token_data.setdefault("scope", self._scope_string())
        self._save_tokens(token_data)
        return token_data

    def refresh_access_token(self) -> dict[str, Any]:
        tokens = self._load_tokens()
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise ValueError("No refresh token available")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        with httpx.Client(timeout=15.0) as client:
            response = client.post("https://oauth2.googleapis.com/token", data=payload)
            response.raise_for_status()
            token_data = response.json()
        token_data["refresh_token"] = refresh_token
        if token_data.get("expires_in"):
            token_data["expires_at"] = int(time.time()) + int(token_data["expires_in"])
        token_data.setdefault("scope", self._scope_string())
        self._save_tokens(token_data)
        return token_data

    def _get_access_token(self) -> str:
        tokens = self._load_tokens()
        if not tokens:
            raise ValueError("Gmail authentication is not configured")
        if tokens.get("expires_at") and tokens["expires_at"] <= int(__import__("time").time()):
            tokens = self.refresh_access_token()
        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("No access token available")
        return str(access_token)

    def send_message(self, message: EmailMessage, account: str | None = None) -> dict[str, Any]:
        self._ensure_send_scope()
        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        payload = {"raw": encoded}
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def fetch_messages(self, account: str | None = None, label: str | None = None, unread_only: bool = False, subject_filter: str | None = None, max_results: int = 5) -> list[dict[str, Any]]:
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials are not configured")

        bounded_max_results = max(1, min(int(max_results or 5), 5))
        started_at = time.perf_counter()
        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        query_parts: list[str] = []
        if unread_only:
            query_parts.append("is:unread")
        if label:
            query_parts.append(f"label:{label}")
        if subject_filter:
            query_parts.append(f"subject:{subject_filter}")
        query = " ".join(query_parts) if query_parts else ""

        logger.info("Starting Gmail message fetch", extra={"query": query or None, "max_results": bounded_max_results})

        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"q": query, "maxResults": bounded_max_results} if query else {"maxResults": bounded_max_results},
            )
            response.raise_for_status()
            payload = response.json()

        messages = payload.get("messages") or []
        result: list[dict[str, Any]] = []
        for index, message_ref in enumerate(messages[:bounded_max_results], start=1):
            message_id = message_ref.get("id")
            if not message_id:
                continue
            with httpx.Client(timeout=5.0) as client:
                detail_response = client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                    headers=headers,
                    params={"format": "full"},
                )
                detail_response.raise_for_status()
                detail = detail_response.json()
            result.append(self._normalize_message(detail))
            logger.info("Fetched Gmail message detail", extra={"message_index": index, "message_id": message_id})

        logger.info("Completed Gmail message fetch", extra={"message_count": len(result), "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2)})
        return result

    def _normalize_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {item.get("name", "").lower(): item.get("value", "") for item in payload.get("payload", {}).get("headers", []) if isinstance(item, dict)}
        payload_root = payload.get("payload", {}) or {}
        body = self._extract_plain_text_body(payload_root)

        # Safe diagnostics: report presence and sizes but never log actual content
        try:
            mime = payload_root.get("mimeType")
            plain_chars = 0
            html_chars = 0
            # check top-level body
            if isinstance(payload_root.get("body", {}), dict):
                data = payload_root.get("body", {}).get("data", "") or ""
                if data:
                    # rough guess by attempting decode; ignore content
                    decoded = self._decode_base64(data)
                    if payload_root.get("mimeType") == "text/plain":
                        plain_chars = len(decoded)
                    elif payload_root.get("mimeType") == "text/html":
                        html_chars = len(decoded)

            # scan parts for counts
            for part in payload_root.get("parts") or []:
                if not isinstance(part, dict):
                    continue
                p_mime = part.get("mimeType")
                p_data = part.get("body", {}).get("data", "") or ""
                if p_data:
                    try:
                        decoded = self._decode_base64(p_data)
                        if p_mime == "text/plain":
                            plain_chars += len(decoded)
                        elif p_mime == "text/html":
                            html_chars += len(decoded)
                    except Exception:
                        pass

            logger.info(
                "Gmail normalized message diagnostics",
                extra={
                    "message_id": payload.get("id"),
                    "mimeType": mime,
                    "body_chars": len(body or ""),
                    "plain_text_chars": plain_chars,
                    "html_chars": html_chars,
                },
            )
        except Exception:
            # never fail normalization due to diagnostics
            pass

        internal_date = payload.get("internalDate")
        return {
            "message_id": payload.get("id"),
            "sender": headers.get("from", ""),
            "recipient": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "body": body,
            "received_at": internal_date,
            "internalDate": internal_date,
            "timestamp_ms": self._normalize_timestamp_ms(internal_date),
            "unread": True,
        }

    def _normalize_timestamp_ms(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if stripped.isdigit():
                return int(stripped)
        return None

    def _extract_plain_text_body(self, payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return ""
        # Prefer explicit text/plain bodies
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return self._decode_base64(data)

        # If only HTML is present, fall back to extracting and cleaning HTML
        if payload.get("mimeType") == "text/html":
            data = payload.get("body", {}).get("data", "")
            if data:
                html_text = self._decode_base64(data)
                return self._html_to_text(html_text)

        # Walk parts (multipart/alternative, nested multiparts)
        html_fallback: str | None = None
        for part in payload.get("parts") or []:
            if not isinstance(part, dict):
                continue
            mime = part.get("mimeType")
            if mime == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return self._decode_base64(data)
            if mime == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    # keep as a potential fallback if no plain text is found
                    html_fallback = self._html_to_text(self._decode_base64(data))
            # recurse into nested parts
            nested_text = self._extract_plain_text_body(part)
            if nested_text:
                return nested_text

        if html_fallback:
            return html_fallback

        return ""

    def _html_to_text(self, html_content: str) -> str:
        # Minimal HTML-to-text conversion: unescape entities and strip tags
        try:
            import html as _html_module
            import re

            text = _html_module.unescape(html_content)
            # remove script/style blocks
            text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", text)
            # remove tags
            text = re.sub(r"<[^>]+>", "", text)
            # condense whitespace
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except Exception:
            return ""

    def _decode_base64(self, value: str) -> str:
        import base64

        # base64url strings from Gmail may omit padding; add correct padding
        s = value or ""
        # remove whitespace
        s = s.strip()
        # compute required padding
        padding = (-len(s)) % 4
        if padding:
            s += "=" * padding
        try:
            return base64.urlsafe_b64decode(s.encode("utf-8")).decode("utf-8", errors="replace")
        except Exception:
            # fallback: try standard b64decode
            try:
                return base64.b64decode(s.encode("utf-8")).decode("utf-8", errors="replace")
            except Exception:
                return ""

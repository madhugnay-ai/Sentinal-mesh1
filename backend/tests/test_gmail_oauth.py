from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from services.gmail_service import GmailService


class FakeResponse:
    def __init__(self, payload: dict | None = None, status_code: int = 200) -> None:
        self._payload = payload or {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("request failed")

    def json(self) -> dict:
        return self._payload


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    token_path = tmp_path / "gmail_tokens.json"
    app.state.gmail_token_path = str(token_path)
    return TestClient(app)


def test_gmail_service_builds_authorization_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/gmail/oauth/callback")
    service = GmailService(token_store_path="/tmp/gmail_tokens.json")

    auth_url = service.get_auth_url()

    assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
    assert "client_id=client-id" in auth_url
    assert "scope=https://www.googleapis.com/auth/gmail.readonly" in auth_url


def test_gmail_service_exchange_code_stores_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    token_path = tmp_path / "gmail_tokens.json"
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/gmail/oauth/callback")

    def fake_post(self, url: str, data: dict | None = None, **kwargs: object) -> FakeResponse:
        assert url == "https://oauth2.googleapis.com/token"
        assert data["grant_type"] == "authorization_code"
        return FakeResponse({"access_token": "access", "refresh_token": "refresh", "expires_in": 3600})

    monkeypatch.setattr("services.gmail_service.httpx.Client.post", fake_post)

    service = GmailService(token_store_path=str(token_path))
    tokens = service.exchange_code("test-code")

    assert tokens["access_token"] == "access"
    assert token_path.exists()
    stored_tokens = json.loads(token_path.read_text(encoding="utf-8"))
    assert stored_tokens["refresh_token"] == "refresh"
    assert "gmail.send" in stored_tokens["scope"]


def test_gmail_service_reports_connection_status(tmp_path: Path) -> None:
    token_path = tmp_path / "gmail_tokens.json"
    service = GmailService(token_store_path=str(token_path))
    service._save_tokens({"access_token": "access"})

    assert service.is_connected() is True


def test_gmail_service_refreshes_access_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    token_path = tmp_path / "gmail_tokens.json"
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")

    def fake_post(self, url: str, data: dict | None = None, **kwargs: object) -> FakeResponse:
        assert url == "https://oauth2.googleapis.com/token"
        assert data["grant_type"] == "refresh_token"
        return FakeResponse({"access_token": "new-access", "expires_in": 3600})

    monkeypatch.setattr("services.gmail_service.httpx.Client.post", fake_post)

    service = GmailService(token_store_path=str(token_path))
    service._save_tokens({"refresh_token": "refresh"})
    refreshed = service.refresh_access_token()

    assert refreshed["access_token"] == "new-access"
    assert service._load_tokens()["refresh_token"] == "refresh"


def test_authorize_endpoint_returns_auth_url(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/gmail/oauth/callback")

    response = client.get("/gmail/oauth/authorize")

    assert response.status_code == 200
    assert response.json()["auth_url"].startswith("https://accounts.google.com/o/oauth2/v2/auth")


def test_callback_endpoint_exchange_code_and_redirects(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/gmail/oauth/callback")

    def fake_post(self, url: str, data: dict | None = None, **kwargs: object) -> FakeResponse:
        return FakeResponse({"access_token": "access", "refresh_token": "refresh", "expires_in": 3600})

    monkeypatch.setattr("services.gmail_service.httpx.Client.post", fake_post)

    response = client.get("/gmail/oauth/callback?code=test-code", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].startswith("http://localhost:5173/gmail/oauth/callback")


def test_status_endpoint_reports_connection_state(client: TestClient, tmp_path: Path) -> None:
    token_path = tmp_path / "gmail_tokens.json"
    client.app.state.gmail_token_path = str(token_path)

    response = client.get("/gmail/oauth/status")

    assert response.status_code == 200
    assert response.json()["connected"] is False

    GmailService(token_store_path=str(token_path))._save_tokens({"access_token": "access"})
    response = client.get("/gmail/oauth/status")

    assert response.status_code == 200
    assert response.json()["connected"] is True


def test_disconnect_endpoint_removes_tokens(client: TestClient, tmp_path: Path) -> None:
    token_path = tmp_path / "gmail_tokens.json"
    client.app.state.gmail_token_path = str(token_path)
    GmailService(token_store_path=str(token_path))._save_tokens({"access_token": "access"})

    response = client.delete("/gmail/oauth/disconnect")

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert not token_path.exists()


def test_gmail_service_requires_send_scope_for_sending(tmp_path: Path) -> None:
    token_path = tmp_path / "gmail_tokens.json"
    service = GmailService(token_store_path=str(token_path))
    service._save_tokens({"access_token": "access", "scope": "https://www.googleapis.com/auth/gmail.readonly"})

    with pytest.raises(ValueError, match="gmail.send"):
        service.send_message(__import__("email.message").message.EmailMessage())


def test_gmail_service_limits_message_fetches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    token_path = tmp_path / "gmail_tokens.json"
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    requests: list[tuple[str, dict | None, dict | None]] = []

    class FakeHttpClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.timeout = kwargs.get("timeout")

        def __enter__(self) -> "FakeHttpClient":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def get(self, url: str, headers: dict | None = None, params: dict | None = None) -> FakeResponse:
            requests.append((url, params, headers))
            if url.endswith("/messages"):
                return FakeResponse({"messages": [{"id": f"msg-{index}"} for index in range(10)]})
            return FakeResponse({"id": "msg-0", "payload": {"headers": [], "body": {}}})

        def post(self, url: str, data: dict | None = None, **kwargs: object) -> FakeResponse:
            return FakeResponse({"access_token": "access", "expires_in": 3600})

    monkeypatch.setattr("services.gmail_service.httpx.Client", FakeHttpClient)

    service = GmailService(token_store_path=str(token_path))
    service._save_tokens({"access_token": "access"})

    result = service.fetch_messages(unread_only=True, max_results=5)

    assert len(result) == 5
    assert requests[0][1] is not None
    assert requests[0][1]["maxResults"] == 5

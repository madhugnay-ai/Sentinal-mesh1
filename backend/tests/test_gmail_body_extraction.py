from services.gmail_service import GmailService


def _encode_bytes(s: str) -> str:
    import base64

    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii")


def test_extract_plain_text_from_text_plain() -> None:
    svc = GmailService()
    payload = {"mimeType": "text/plain", "body": {"data": _encode_bytes("The project review meeting is Wednesday at 3 PM.")}}
    assert svc._extract_plain_text_body(payload) == "The project review meeting is Wednesday at 3 PM."


def test_extract_text_from_html_only() -> None:
    svc = GmailService()
    html = "<p>The project review meeting is <b>Wednesday</b> at 3 PM.</p>"
    payload = {"mimeType": "text/html", "body": {"data": _encode_bytes(html)}}
    text = svc._extract_plain_text_body(payload)
    assert "project review" in text.lower()
    assert "Wednesday" in text


def test_extract_prefers_text_plain_in_multipart() -> None:
    svc = GmailService()
    parts = [
        {"mimeType": "text/plain", "body": {"data": _encode_bytes("Plain part")}},
        {"mimeType": "text/html", "body": {"data": _encode_bytes("<p>HTML part</p>")}},
    ]
    payload = {"mimeType": "multipart/alternative", "parts": parts}
    assert svc._extract_plain_text_body(payload) == "Plain part"


def test_extract_from_nested_multipart() -> None:
    svc = GmailService()
    nested = {"mimeType": "multipart/mixed", "parts": [{"mimeType": "text/plain", "body": {"data": _encode_bytes("Nested text")}}]}
    payload = {"mimeType": "multipart/mixed", "parts": [nested]}
    assert svc._extract_plain_text_body(payload) == "Nested text"


def test_extract_returns_empty_for_empty_payload() -> None:
    svc = GmailService()
    assert svc._extract_plain_text_body({}) == ""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from services.gmail_service import GmailService

router = APIRouter(prefix="/gmail/oauth", tags=["gmail"])


def _get_service(request: Request) -> GmailService:
    token_path = getattr(request.app.state, "gmail_token_path", None)
    return GmailService(token_store_path=token_path)


@router.get("/authorize")
def authorize_gmail(request: Request) -> dict[str, str]:
    service = _get_service(request)
    try:
        auth_url = service.get_auth_url()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return {"auth_url": auth_url}


@router.get("/callback")
def gmail_callback(request: Request, code: str | None = None, error: str | None = None) -> RedirectResponse:
    if error:
        return RedirectResponse(url="http://localhost:5173/gmail/oauth/callback?status=error", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code is missing")

    service = _get_service(request)
    try:
        service.exchange_code(code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive for network failures
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return RedirectResponse(url="http://localhost:5173/gmail/oauth/callback?status=success", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/status")
def gmail_status(request: Request) -> dict[str, Any]:
    service = _get_service(request)
    return {"connected": service.is_connected(), "configured": bool(service.client_id and service.client_secret and service.redirect_uri)}


@router.delete("/disconnect")
def disconnect_gmail(request: Request) -> dict[str, Any]:
    service = _get_service(request)
    service.clear_tokens()
    return {"connected": False, "configured": bool(service.client_id and service.client_secret and service.redirect_uri)}

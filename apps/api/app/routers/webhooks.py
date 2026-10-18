import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.webhook_service import WebhookService

logger = logging.getLogger("wapiflow.routers.webhooks")
router = APIRouter(prefix="/webhooks", tags=["Meta Webhooks"])


@router.get(
    "/whatsapp",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Meta WhatsApp Cloud API Webhook Handshake Verification",
)
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
) -> Response:
    """
    Handles Meta webhook verification handshake.
    Meta sends hub.mode, hub.challenge, and hub.verify_token.
    If hub.verify_token matches META_VERIFY_TOKEN, returns hub.challenge as plain text.
    """
    challenge = WebhookService.verify_handshake(
        mode=hub_mode,
        token=hub_verify_token,
        challenge=hub_challenge,
    )
    return PlainTextResponse(content=challenge, status_code=status.HTTP_200_OK)


@router.post(
    "/whatsapp",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Meta WhatsApp Webhook Event Ingestion",
)
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Receives incoming Meta WhatsApp events (inbound messages, delivery receipts, errors).
    Validates HMAC-SHA256 signature in X-Hub-Signature-256 header.
    Stores raw events and normalizes into conversations and messages.
    """
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256") or request.headers.get("x-hub-signature-256")

    return await WebhookService.process_webhook(
        db=db,
        raw_body=raw_body,
        signature_header=signature_header,
    )

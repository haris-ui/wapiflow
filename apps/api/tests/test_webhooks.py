import hashlib
import hmac
import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.models.customer import Customer
from app.models.whatsapp import Conversation, Message, WebhookEvent, WhatsAppAccount

settings = get_settings()


@pytest.mark.asyncio
async def test_webhook_handshake_success(client: AsyncClient):
    """Verify that Meta webhook handshake succeeds when verify_token matches."""
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "987654321",
        "hub.verify_token": settings.META_VERIFY_TOKEN,
    }
    response = await client.get("/api/v1/webhooks/whatsapp", params=params)
    assert response.status_code == 200
    assert response.text == "987654321"


@pytest.mark.asyncio
async def test_webhook_handshake_invalid_token(client: AsyncClient):
    """Verify that Meta webhook handshake is rejected when verify_token does not match."""
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "987654321",
        "hub.verify_token": "wrong_unauthorized_token",
    }
    response = await client.get("/api/v1/webhooks/whatsapp", params=params)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_inbound_message_ingestion(client: AsyncClient, test_business, db_session):
    """Verify inbound WhatsApp text message creates customer, conversation, and message records."""
    # Ensure a WhatsApp account exists for the business
    account = WhatsAppAccount(
        business_id=test_business.id,
        waba_id="waba_test_123",
        app_id="wapiflow",
        access_token="test_access_token_123",
        status="connected",
    )
    db_session.add(account)
    await db_session.commit()

    wa_msg_id = "wamid.TEST_MSG_INBOUND_001"
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_test_123",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "waba_test_123",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Alice Customer"},
                                    "wa_id": "15551239999",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "15551239999",
                                    "id": wa_msg_id,
                                    "timestamp": "1710684000",
                                    "text": {"body": "Hello, I want to place an order for delivery!"},
                                    "type": "text",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": "sha256=mock_valid",
    }

    response = await client.post("/api/v1/webhooks/whatsapp", headers=headers, content=body_bytes)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["processed"] is True

    # 1. Verify Customer created
    stmt_cust = select(Customer).where(Customer.phone_number.like("%15551239999%"))
    cust = (await db_session.execute(stmt_cust)).scalars().first()
    assert cust is not None
    assert "Alice" in cust.name

    # 2. Verify Conversation created
    stmt_conv = select(Conversation).where(
        Conversation.business_id == test_business.id,
        Conversation.customer_id == cust.id,
    )
    conv = (await db_session.execute(stmt_conv)).scalars().first()
    assert conv is not None
    assert conv.status == "open"
    assert conv.unread_count == 1
    assert "place an order" in conv.last_message_preview

    # 3. Verify Message created
    stmt_msg = select(Message).where(Message.wa_message_id == wa_msg_id)
    msg = (await db_session.execute(stmt_msg)).scalars().first()
    assert msg is not None
    assert msg.direction == "inbound"
    assert msg.content == "Hello, I want to place an order for delivery!"
    assert msg.status == "received"


@pytest.mark.asyncio
async def test_webhook_message_deduplication(client: AsyncClient, test_business, db_session):
    """Verify that sending the same wa_message_id twice does not create duplicate messages."""
    wa_msg_id = "wamid.DUPLICATE_TEST_ID_002"
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_test_123",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "waba_test_123"},
                            "contacts": [{"profile": {"name": "Bob"}, "wa_id": "15559998888"}],
                            "messages": [
                                {
                                    "from": "15559998888",
                                    "id": wa_msg_id,
                                    "timestamp": "1710684000",
                                    "text": {"body": "Initial message"},
                                    "type": "text",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=mock"}

    # First delivery
    r1 = await client.post("/api/v1/webhooks/whatsapp", headers=headers, content=body_bytes)
    assert r1.status_code == 200

    # Second delivery (duplicate delivery by Meta)
    r2 = await client.post("/api/v1/webhooks/whatsapp", headers=headers, content=body_bytes)
    assert r2.status_code == 200

    # Ensure only 1 Message record exists
    stmt_count = select(Message).where(Message.wa_message_id == wa_msg_id)
    all_msgs = (await db_session.execute(stmt_count)).scalars().all()
    assert len(all_msgs) == 1


@pytest.mark.asyncio
async def test_webhook_delivery_status_update(client: AsyncClient, test_business, db_session):
    """Verify outbound message delivery receipts update message status (delivered, read)."""
    # Create conversation and pending outbound message
    conv = Conversation(business_id=test_business.id, status="open")
    db_session.add(conv)
    await db_session.flush()

    outbound_wa_id = "wamid.OUTBOUND_RECEIPT_TEST_003"
    msg = Message(
        conversation_id=conv.id,
        business_id=test_business.id,
        wa_message_id=outbound_wa_id,
        direction="outbound",
        message_type="text",
        content="Your order is confirmed!",
        status="sent",
    )
    db_session.add(msg)
    await db_session.commit()

    # Dispatch delivery status update from Meta
    status_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_test_123",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "waba_test_123"},
                            "statuses": [
                                {
                                    "id": outbound_wa_id,
                                    "status": "delivered",
                                    "timestamp": "1710684100",
                                    "recipient_id": "15551239999",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    body_bytes = json.dumps(status_payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=mock"}

    resp = await client.post("/api/v1/webhooks/whatsapp", headers=headers, content=body_bytes)
    assert resp.status_code == 200

    # Verify status changed to 'delivered'
    await db_session.refresh(msg)
    assert msg.status == "delivered"

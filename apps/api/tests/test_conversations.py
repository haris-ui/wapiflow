import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.customer import Customer
from app.models.product import Product
from app.models.whatsapp import Conversation, Message


@pytest.mark.asyncio
async def test_list_and_filter_conversations(client: AsyncClient, test_business, auth_headers, db_session):
    """Test listing conversations with filters."""
    # Create customer and conversations
    cust = Customer(
        business_id=test_business.id,
        name="Charlie Brown",
        phone_number="+15554443333",
    )
    db_session.add(cust)
    await db_session.flush()

    conv1 = Conversation(
        business_id=test_business.id,
        customer_id=cust.id,
        status="open",
        last_message_preview="Hello there",
    )
    conv2 = Conversation(
        business_id=test_business.id,
        customer_id=cust.id,
        status="resolved",
        last_message_preview="Resolved conversation",
    )
    db_session.add_all([conv1, conv2])
    await db_session.commit()

    # List all
    res = await client.get(
        f"/api/v1/businesses/{test_business.id}/conversations",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2

    # Filter by open status
    res_open = await client.get(
        f"/api/v1/businesses/{test_business.id}/conversations?status=open",
        headers=auth_headers,
    )
    assert res_open.status_code == 200
    for item in res_open.json()["items"]:
        assert item["status"] == "open"


@pytest.mark.asyncio
async def test_send_message_and_internal_note(client: AsyncClient, test_business, auth_headers, db_session):
    """Test sending outbound messages and private internal team notes."""
    cust = Customer(business_id=test_business.id, name="Dave", phone_number="+15557778888")
    db_session.add(cust)
    await db_session.flush()

    conv = Conversation(business_id=test_business.id, customer_id=cust.id, status="open")
    db_session.add(conv)
    await db_session.commit()

    # 1. Send internal note
    note_resp = await client.post(
        f"/api/v1/businesses/{test_business.id}/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "Customer requested urgent dispatch tomorrow.", "is_internal_note": True},
    )
    assert note_resp.status_code == 201
    note_data = note_resp.json()
    assert note_data["is_internal_note"] is True
    assert "urgent dispatch" in note_data["content"]

    # 2. Send regular outbound WhatsApp message
    msg_resp = await client.post(
        f"/api/v1/businesses/{test_business.id}/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "Your package is prepared!", "is_internal_note": False},
    )
    assert msg_resp.status_code == 201
    msg_data = msg_resp.json()
    assert msg_data["is_internal_note"] is False
    assert msg_data["direction"] == "outbound"
    assert "package is prepared" in msg_data["content"]

    # 3. Fetch messages list
    history_resp = await client.get(
        f"/api/v1/businesses/{test_business.id}/conversations/{conv.id}/messages",
        headers=auth_headers,
    )
    assert history_resp.status_code == 200
    assert history_resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_conversation_status_update(client: AsyncClient, test_business, auth_headers, db_session):
    """Test resolving and reopening conversations."""
    conv = Conversation(business_id=test_business.id, status="open")
    db_session.add(conv)
    await db_session.commit()

    # Resolve conversation
    res = await client.patch(
        f"/api/v1/businesses/{test_business.id}/conversations/{conv.id}",
        headers=auth_headers,
        json={"status": "resolved"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "resolved"

    # Reopen conversation
    res2 = await client.patch(
        f"/api/v1/businesses/{test_business.id}/conversations/{conv.id}",
        headers=auth_headers,
        json={"status": "open"},
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "open"


@pytest.mark.asyncio
async def test_quick_order_creation_from_conversation(client: AsyncClient, test_business, auth_headers, db_session):
    """Test creating an order directly from an active conversation thread."""
    # Create product
    prod = Product(
        business_id=test_business.id,
        name="Guatemala Roast",
        sku="GUA-001",
        price=18.50,
        stock_quantity=50,
    )
    cust = Customer(business_id=test_business.id, name="Emma", phone_number="+15553332222")
    db_session.add_all([prod, cust])
    await db_session.flush()

    conv = Conversation(business_id=test_business.id, customer_id=cust.id, status="open")
    db_session.add(conv)
    await db_session.commit()

    # Create quick order
    order_payload = {
        "items": [{"product_id": str(prod.id), "quantity": 2}],
        "notes": "Requested delivery after 5 PM",
        "fulfillment_address": "4th Ave, Seattle",
    }
    resp = await client.post(
        f"/api/v1/businesses/{test_business.id}/conversations/{conv.id}/orders",
        headers=auth_headers,
        json=order_payload,
    )
    assert resp.status_code == 201
    order_data = resp.json()
    assert float(order_data["total_amount"]) == 37.00
    assert order_data["customer_id"] == str(cust.id)

    # Check that confirmation note was recorded in conversation
    stmt_notes = select(Message).where(
        Message.conversation_id == conv.id,
        Message.is_internal_note.is_(True),
    )
    notes = (await db_session.execute(stmt_notes)).scalars().all()
    assert len(notes) >= 1
    assert "Order" in notes[0].content


@pytest.mark.asyncio
async def test_conversation_tenant_isolation(
    client: AsyncClient,
    test_business,
    auth_headers,
    test_user_factory,
    test_business_factory,
    db_session,
):
    """Strict test: Tenant B cannot access Tenant A's conversations or messages."""
    # Tenant A conversation
    conv_a = Conversation(business_id=test_business.id, status="open")
    db_session.add(conv_a)
    await db_session.commit()

    # Tenant B and User B
    user_b = await test_user_factory(email="tenant_b_user@example.com")
    biz_b = await test_business_factory(owner_user_id=user_b.id, name="Tenant B Co")

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "tenant_b_user@example.com", "password": "Password123!"},
    )
    token_b = login_resp.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. User B tries to access Tenant A's conversation list under Business A -> 403 Forbidden
    res_list = await client.get(
        f"/api/v1/businesses/{test_business.id}/conversations",
        headers=headers_b,
    )
    assert res_list.status_code == 403

    # 2. User B tries to view Tenant A's conversation under Business B -> 404 Not Found
    res_detail = await client.get(
        f"/api/v1/businesses/{biz_b.id}/conversations/{conv_a.id}",
        headers=headers_b,
    )
    assert res_detail.status_code == 404

    # 3. User B tries to post a message to Tenant A's conversation -> 403 / 404
    res_msg = await client.post(
        f"/api/v1/businesses/{biz_b.id}/conversations/{conv_a.id}/messages",
        headers=headers_b,
        json={"content": "Malicious intrusion attempt", "is_internal_note": True},
    )
    assert res_msg.status_code == 404

import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.customer import Customer
from app.models.order import Order
from app.models.product import Product
from app.models.whatsapp import Conversation, Message, WhatsAppAccount, WhatsAppPhoneNumber


@pytest.mark.asyncio
async def test_presigned_upload_url_generation(client: AsyncClient, test_business, auth_headers):
    """Test generating presigned upload URL for a catalog image."""
    payload = {
        "filename": "espresso_machine.jpg",
        "content_type": "image/jpeg",
        "folder": "products",
    }
    response = await client.post(
        f"/api/v1/businesses/{test_business.id}/media/presigned",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "upload_url" in data
    assert "public_url" in data
    assert "key" in data
    assert str(test_business.id) in data["key"]
    assert "products" in data["key"]


@pytest.mark.asyncio
async def test_unsupported_file_type_rejection(client: AsyncClient, test_business, auth_headers):
    """Test that unauthorized executable or dangerous MIME types are blocked."""
    payload = {
        "filename": "malicious.exe",
        "content_type": "application/x-msdownload",
        "folder": "products",
    }
    response = await client.post(
        f"/api/v1/businesses/{test_business.id}/media/presigned",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["message"]


@pytest.mark.asyncio
async def test_direct_multipart_upload_and_serving(client: AsyncClient, test_business, auth_headers):
    """Test direct multipart upload and retrieval of media asset."""
    file_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"  # mock jpeg header
    files = {
        "file": ("test_banner.jpg", io.BytesIO(file_content), "image/jpeg"),
    }
    data = {"folder": "products"}

    # Upload
    response = await client.post(
        f"/api/v1/businesses/{test_business.id}/media/upload",
        files=files,
        data=data,
        headers=auth_headers,
    )
    assert response.status_code == 201
    media_data = response.json()
    assert media_data["filename"] == "test_banner.jpg"
    assert media_data["content_type"] == "image/jpeg"
    assert media_data["size_bytes"] == len(file_content)
    assert str(test_business.id) in media_data["key"]

    # Verify that the public local URL can be fetched
    public_url = media_data["url"]
    get_res = await client.get(public_url)
    assert get_res.status_code == 200
    assert get_res.content == file_content


@pytest.mark.asyncio
async def test_tenant_isolated_media_deletion(
    client: AsyncClient,
    create_user,
    create_business,
    test_business,
    auth_headers,
):
    """Test that businesses cannot delete media keys belonging to other tenants."""
    file_content = b"fake-png-content"
    files = {"file": ("biz_a.png", io.BytesIO(file_content), "image/png")}

    # Biz A uploads a file
    res_a = await client.post(
        f"/api/v1/businesses/{test_business.id}/media/upload",
        files=files,
        headers=auth_headers,
    )
    assert res_a.status_code == 201
    key_a = res_a.json()["key"]

    # Biz B (separate tenant) attempts to delete Biz A's media key
    user_b, headers_b = await create_user("biz_b_owner@example.com")
    biz_b_id = await create_business(
        user_b, "Biz B", f"biz-b-media-{uuid.uuid4().hex[:6]}"
    )

    del_res_forbidden = await client.delete(
        f"/api/v1/businesses/{biz_b_id}/media",
        params={"key": key_a},
        headers=headers_b,
    )
    assert del_res_forbidden.status_code == 403
    assert "outside your tenant boundary" in del_res_forbidden.json()["message"]

    # Biz A deletes own media
    del_res_ok = await client.delete(
        f"/api/v1/businesses/{test_business.id}/media",
        params={"key": key_a},
        headers=auth_headers,
    )
    assert del_res_ok.status_code == 200
    assert del_res_ok.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_order_status_transition_whatsapp_notification(client: AsyncClient, test_business, auth_headers, db_session):
    """Test automated WhatsApp notification dispatch when order status transitions."""
    # 1. Connect a WhatsApp Account to test_business
    account = WhatsAppAccount(
        business_id=test_business.id,
        waba_id="waba_notify_test",
        app_id="app_notify_test",
        access_token="test_access_token",
        status="connected",
    )
    db_session.add(account)

    # 2. Create customer with phone
    cust = Customer(
        business_id=test_business.id,
        name="John Notification",
        phone_number="+15559876543",
    )
    # 3. Create product
    prod = Product(
        business_id=test_business.id,
        name="Cold Brew Kit",
        sku="CB-001",
        price=24.00,
        stock_quantity=10,
    )
    db_session.add_all([cust, prod])
    await db_session.flush()

    # 4. Create Order
    create_payload = {
        "customer_id": str(cust.id),
        "items": [{"product_id": str(prod.id), "quantity": 1}],
    }
    create_res = await client.post(
        f"/api/v1/businesses/{test_business.id}/orders",
        json=create_payload,
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    order_id = create_res.json()["id"]

    # 5. Transition order from pending -> confirmed
    trans_payload = {
        "new_status": "confirmed",
        "notes": "Payment confirmed via card",
    }
    trans_res = await client.patch(
        f"/api/v1/businesses/{test_business.id}/orders/{order_id}/status",
        json=trans_payload,
        headers=auth_headers,
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["status"] == "confirmed"

    # 6. Verify an outbound message was generated in the conversation thread
    stmt_msgs = (
        select(Message)
        .where(
            Message.business_id == test_business.id,
            Message.direction == "outbound",
            Message.content.like("%CONFIRMED%"),
        )
    )
    msgs = (await db_session.execute(stmt_msgs)).scalars().all()
    assert len(msgs) >= 1
    assert "CONFIRMED" in msgs[0].content


@pytest.mark.asyncio
async def test_manual_order_notification_endpoint(client: AsyncClient, test_business, auth_headers, db_session):
    """Test manual notification dispatch endpoint POST /{order_id}/notify."""
    # Setup WhatsApp account
    account = WhatsAppAccount(
        business_id=test_business.id,
        waba_id="waba_manual_test",
        app_id="app_manual_test",
        access_token="test_token",
        status="connected",
    )
    cust = Customer(
        business_id=test_business.id,
        name="Mary Manual",
        phone_number="+15558889999",
    )
    prod = Product(
        business_id=test_business.id,
        name="Espresso Beans",
        sku="ESP-002",
        price=15.00,
        stock_quantity=20,
    )
    db_session.add_all([account, cust, prod])
    await db_session.flush()

    create_payload = {
        "customer_id": str(cust.id),
        "items": [{"product_id": str(prod.id), "quantity": 2}],
    }
    create_res = await client.post(
        f"/api/v1/businesses/{test_business.id}/orders",
        json=create_payload,
        headers=auth_headers,
    )
    order_id = create_res.json()["id"]

    # Call manual notify
    notify_res = await client.post(
        f"/api/v1/businesses/{test_business.id}/orders/{order_id}/notify",
        params={"custom_message": "Custom WhatsApp message: Your espresso beans are on the way!"},
        headers=auth_headers,
    )
    assert notify_res.status_code == 200
    assert notify_res.json()["status"] == "ok"

    # Verify message in database
    stmt_msg = select(Message).where(
        Message.business_id == test_business.id,
        Message.content.like("%Custom WhatsApp message%"),
    )
    msg = (await db_session.execute(stmt_msg)).scalars().first()
    assert msg is not None
    assert "Your espresso beans are on the way!" in msg.content

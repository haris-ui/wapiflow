import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_order_calculates_totals(client: AsyncClient, create_user, create_business):
    """Test order creation snapshots prices, computes subtotal and total correctly."""
    user_id, headers = await create_user("order_user@example.com")
    business_id = await create_business(user_id, "Order Biz", "order-biz")

    # Create two products
    p1 = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "Book", "sku": "BK-1", "price": 20.00, "stock_quantity": 10},
        headers=headers,
    )
    p2 = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "Pen", "sku": "PN-1", "price": 5.00, "stock_quantity": 50},
        headers=headers,
    )
    p1_id = p1.json()["id"]
    p2_id = p2.json()["id"]

    order_payload = {
        "items": [
            {"product_id": p1_id, "quantity": 2},  # 2 * 20 = 40.00
            {"product_id": p2_id, "quantity": 3},  # 3 * 5 = 15.00
        ],
        "customer_name": "Alice Customer",
        "customer_phone": "+15551234567",
        "shipping_fee": 10.00,
        "discount_amount": 5.00,
        "fulfillment_address": "123 Main Street",
        "idempotency_key": "order-key-101",
    }

    response = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json=order_payload,
        headers=headers,
    )
    assert response.status_code == 201
    order_data = response.json()

    # Subtotal = 40 + 15 = 55.00, Total = 55 - 5 + 10 = 60.00
    assert float(order_data["subtotal"]) == 55.00
    assert float(order_data["discount_amount"]) == 5.00
    assert float(order_data["shipping_fee"]) == 10.00
    assert float(order_data["total_amount"]) == 60.00
    assert order_data["status"] == "pending"
    assert len(order_data["items"]) == 2
    assert len(order_data["status_history"]) == 1
    assert order_data["status_history"][0]["new_status"] == "pending"


@pytest.mark.asyncio
async def test_order_foreign_product_rejection(client: AsyncClient, create_user, create_business):
    """Test creating an order with a product from another business returns 422."""
    user_a, headers_a = await create_user("owner_a@example.com")
    biz_a = await create_business(user_a, "Biz A", "biz-a")

    user_b, headers_b = await create_user("owner_b@example.com")
    biz_b = await create_business(user_b, "Biz B", "biz-b")

    # Create product in Biz B
    prod_b = await client.post(
        f"/api/v1/businesses/{biz_b}/products",
        json={"name": "Biz B Exclusive Item", "sku": "B-EXCL", "price": 99.00},
        headers=headers_b,
    )
    prod_b_id = prod_b.json()["id"]

    # Try creating order in Biz A containing Biz B's product
    order_payload = {
        "items": [{"product_id": prod_b_id, "quantity": 1}],
    }
    response = await client.post(
        f"/api/v1/businesses/{biz_a}/orders",
        json=order_payload,
        headers=headers_a,
    )
    assert response.status_code == 422
    assert "Products not found or belong to another business" in response.json()["message"]


@pytest.mark.asyncio
async def test_order_duplicate_idempotency_key(client: AsyncClient, create_user, create_business):
    """Test duplicate idempotency key returns 409 Conflict."""
    user_id, headers = await create_user("idem_user@example.com")
    business_id = await create_business(user_id, "Idem Biz", "idem-biz")

    p = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "Widget", "sku": "WDG-1", "price": 10.00},
        headers=headers,
    )
    p_id = p.json()["id"]

    order_payload = {
        "items": [{"product_id": p_id, "quantity": 1}],
        "idempotency_key": "unique-idem-token-xyz",
    }

    res1 = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json=order_payload,
        headers=headers,
    )
    assert res1.status_code == 201

    # Second submission with same idempotency key
    res2 = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json=order_payload,
        headers=headers,
    )
    assert res2.status_code == 409
    assert "idempotency key already exists" in res2.json()["message"]


@pytest.mark.asyncio
async def test_order_status_transitions_and_history(client: AsyncClient, create_user, create_business):
    """Test valid and invalid order status transitions and history tracking."""
    user_id, headers = await create_user("status_user@example.com")
    business_id = await create_business(user_id, "Status Biz", "status-biz")

    p = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "Camera", "sku": "CAM-1", "price": 150.00},
        headers=headers,
    )
    order_res = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json={"items": [{"product_id": p.json()["id"], "quantity": 1}]},
        headers=headers,
    )
    order_id = order_res.json()["id"]

    # 1. Invalid transition directly from pending to delivered -> 422
    invalid_trans = await client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
        json={"new_status": "delivered", "notes": "Premature attempt"},
        headers=headers,
    )
    assert invalid_trans.status_code == 422
    assert "Invalid status transition" in invalid_trans.json()["message"]

    # 2. Valid transition: pending -> confirmed -> 200
    res_conf = await client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
        json={"new_status": "confirmed", "notes": "Customer confirmed over WhatsApp"},
        headers=headers,
    )
    assert res_conf.status_code == 200
    order_data = res_conf.json()
    assert order_data["status"] == "confirmed"
    assert len(order_data["status_history"]) == 2
    assert order_data["status_history"][1]["previous_status"] == "pending"
    assert order_data["status_history"][1]["new_status"] == "confirmed"

    # 3. Valid transition: confirmed -> preparing -> 200
    res_prep = await client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
        json={"new_status": "preparing"},
        headers=headers,
    )
    assert res_prep.status_code == 200
    assert res_prep.json()["status"] == "preparing"

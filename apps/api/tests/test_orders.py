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


@pytest.mark.asyncio
async def test_order_creation_auto_creates_customer_and_decrements_stock(
    client: AsyncClient, create_user, create_business
):
    """Inline customer_phone/name auto-creates a customer and decrements product stock."""
    user_id, headers = await create_user("stock_owner@example.com")
    business_id = await create_business(
        user_id, "Stock Biz", f"stock-biz-{uuid.uuid4().hex[:6]}"
    )
    prod_res = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "Widget", "sku": "WID-1", "price": 12.00, "stock_quantity": 10},
        headers=headers,
    )
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]
    payload = {
        "items": [{"product_id": prod_id, "quantity": 3}],
        "customer_name": "Walk-in Customer",
        "customer_phone": "+15550001111",
        "fulfillment_address": "1 Nowhere Street",
    }
    res = await client.post(
        f"/api/v1/businesses/{business_id}/orders", json=payload, headers=headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "pending"
    assert data["items"][0]["quantity"] == 3
    assert float(data["total_amount"]) == 36.00
    assert data["customer"]["name"] == "Walk-in Customer"
    assert data["customer"]["phone_number"] == "+15550001111"
    prod_get = await client.get(
        f"/api/v1/businesses/{business_id}/products/{prod_id}", headers=headers
    )
    assert prod_get.json()["stock_quantity"] == 7


@pytest.mark.asyncio
async def test_order_empty_items_rejected(client: AsyncClient, create_user, create_business):
    """Creating an order with no line items returns 422."""
    user_id, headers = await create_user("empty_items@example.com")
    business_id = await create_business(
        user_id, "Empty Biz", f"empty-biz-{uuid.uuid4().hex[:6]}"
    )
    response = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json={"items": []},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_order_invalid_status_transition_matrix(
    client: AsyncClient, create_user, create_business
):
    """Every invalid status transition returns 422 with a clear message."""
    user_id, headers = await create_user("matrix@example.com")
    business_id = await create_business(
        user_id, "Matrix Biz", f"matrix-biz-{uuid.uuid4().hex[:6]}"
    )
    prod_res = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "Thing", "sku": "TH-1", "price": 5.00},
        headers=headers,
    )
    prod_id = prod_res.json()["id"]
    order_res = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json={"items": [{"product_id": prod_id, "quantity": 1}]},
        headers=headers,
    )
    order_id = order_res.json()["id"]

    # pending cannot jump ahead to preparing/ready_for_dispatch/shipped/delivered
    for target in ["preparing", "ready_for_dispatch", "shipped", "delivered"]:
        resp = await client.patch(
            f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
            json={"new_status": target},
            headers=headers,
        )
        assert resp.status_code == 422, f"pending -> {target} should be rejected"
        assert "Invalid status transition" in resp.json()["message"]

    # Walk the valid chain to delivered
    for target in ["confirmed", "preparing", "ready_for_dispatch", "shipped", "delivered"]:
        resp = await client.patch(
            f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
            json={"new_status": target},
            headers=headers,
        )
        assert resp.status_code == 200, f"transition to {target} should succeed"
        assert resp.json()["status"] == target

    # delivered is terminal: no further transitions allowed
    resp = await client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
        json={"new_status": "preparing"},
        headers=headers,
    )
    assert resp.status_code == 422
    resp = await client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
        json={"new_status": "cancelled"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_order_cancellation_restores_stock(
    client: AsyncClient, create_user, create_business
):
    """Cancelling an order restores auto-decremented inventory."""
    user_id, headers = await create_user("cancel_owner@example.com")
    business_id = await create_business(
        user_id, "Cancel Biz", f"cancel-biz-{uuid.uuid4().hex[:6]}"
    )
    prod_res = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "Gadget", "sku": "GAD-1", "price": 9.00, "stock_quantity": 10},
        headers=headers,
    )
    prod_id = prod_res.json()["id"]

    order_res = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json={"items": [{"product_id": prod_id, "quantity": 4}]},
        headers=headers,
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    prod_after_order = await client.get(
        f"/api/v1/businesses/{business_id}/products/{prod_id}", headers=headers
    )
    assert prod_after_order.json()["stock_quantity"] == 6

    cancel_res = await client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
        json={"new_status": "cancelled", "notes": "Customer changed mind"},
        headers=headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"
    assert len(cancel_res.json()["status_history"]) == 2

    prod_after_cancel = await client.get(
        f"/api/v1/businesses/{business_id}/products/{prod_id}", headers=headers
    )
    assert prod_after_cancel.json()["stock_quantity"] == 10


@pytest.mark.asyncio
async def test_order_list_pagination_and_status_filter(
    client: AsyncClient, create_user, create_business
):
    """Orders are paginated and filterable by status."""
    user_id, headers = await create_user("list_owner@example.com")
    business_id = await create_business(
        user_id, "List Biz", f"list-biz-{uuid.uuid4().hex[:6]}"
    )
    prod_res = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "P", "sku": "P-1", "price": 1.00},
        headers=headers,
    )
    prod_id = prod_res.json()["id"]

    for _ in range(5):
        await client.post(
            f"/api/v1/businesses/{business_id}/orders",
            json={"items": [{"product_id": prod_id, "quantity": 1}]},
            headers=headers,
        )

    res = await client.get(
        f"/api/v1/businesses/{business_id}/orders?page=1&page_size=2",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3
    assert data["has_next"] is True
    assert len(data["items"]) == 2

    res = await client.get(
        f"/api/v1/businesses/{business_id}/orders?status=pending", headers=headers
    )
    assert res.status_code == 200
    assert all(item["status"] == "pending" for item in res.json()["items"])


@pytest.mark.asyncio
async def test_order_update_notes_and_address(
    client: AsyncClient, create_user, create_business
):
    """Non-status order fields (notes, fulfillment_address) can be updated."""
    user_id, headers = await create_user("update_owner@example.com")
    business_id = await create_business(
        user_id, "Update Biz", f"update-biz-{uuid.uuid4().hex[:6]}"
    )
    prod_res = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "U", "sku": "U-1", "price": 1.00},
        headers=headers,
    )
    prod_id = prod_res.json()["id"]
    order_res = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json={"items": [{"product_id": prod_id, "quantity": 1}]},
        headers=headers,
    )
    order_id = order_res.json()["id"]

    update_res = await client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}",
        json={"notes": "Please call ahead", "fulfillment_address": "2 Updated Ave"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["notes"] == "Please call ahead"
    assert update_res.json()["fulfillment_address"] == "2 Updated Ave"
    assert update_res.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_order_number_uses_business_prefix(
    client: AsyncClient, create_user, create_business
):
    """Generated order numbers carry the business order prefix."""
    user_id, headers = await create_user("prefix_owner@example.com")
    business_id = await create_business(
        user_id, "Prefix Biz", f"prefix-biz-{uuid.uuid4().hex[:6]}"
    )
    prod_res = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "X", "sku": "X-1", "price": 1.00},
        headers=headers,
    )
    prod_id = prod_res.json()["id"]
    order_res = await client.post(
        f"/api/v1/businesses/{business_id}/orders",
        json={"items": [{"product_id": prod_id, "quantity": 1}]},
        headers=headers,
    )
    assert order_res.status_code == 201
    assert order_res.json()["order_number"].startswith("WF-")

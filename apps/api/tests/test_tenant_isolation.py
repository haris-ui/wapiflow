import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_isolation_products_and_orders(client: AsyncClient, create_user, create_business):
    """
    CRITICAL TENANT ISOLATION TEST:
    Verifies that User A (Tenant A) is strictly barred from accessing, reading,
    modifying, or creating resources within Business B (Tenant B).
    """
    # 1. Setup Tenant A
    user_a, headers_a = await create_user("tenant_a@example.com", "Tenant A Owner")
    biz_a = await create_business(user_a, "Alpha Enterprises", "alpha-enterprises")

    # 2. Setup Tenant B
    user_b, headers_b = await create_user("tenant_b@example.com", "Tenant B Owner")
    biz_b = await create_business(user_b, "Beta Logistics", "beta-logistics")

    # 3. Create Product in Business B
    res_b_prod = await client.post(
        f"/api/v1/businesses/{biz_b}/products",
        json={"name": "Beta Gadget", "sku": "BETA-01", "price": 49.99},
        headers=headers_b,
    )
    assert res_b_prod.status_code == 201
    prod_b_id = res_b_prod.json()["id"]

    # 4. Create Order in Business B
    res_b_order = await client.post(
        f"/api/v1/businesses/{biz_b}/orders",
        json={
            "items": [{"product_id": prod_b_id, "quantity": 1}],
            "customer_name": "Beta Customer",
            "customer_phone": "+1987654321",
        },
        headers=headers_b,
    )
    assert res_b_order.status_code == 201
    order_b_id = res_b_order.json()["id"]

    # -------------------------------------------------------------
    # ASSERTION 1: User A CANNOT list Business B's products
    # -------------------------------------------------------------
    leak_products = await client.get(
        f"/api/v1/businesses/{biz_b}/products",
        headers=headers_a,
    )
    assert leak_products.status_code == 403
    assert "Not an active member of this business" in leak_products.json()["message"]

    # -------------------------------------------------------------
    # ASSERTION 2: User A CANNOT get single product from Business B
    # -------------------------------------------------------------
    leak_single_prod = await client.get(
        f"/api/v1/businesses/{biz_b}/products/{prod_b_id}",
        headers=headers_a,
    )
    assert leak_single_prod.status_code == 403

    # -------------------------------------------------------------
    # ASSERTION 3: User A CANNOT list Business B's orders
    # -------------------------------------------------------------
    leak_orders = await client.get(
        f"/api/v1/businesses/{biz_b}/orders",
        headers=headers_a,
    )
    assert leak_orders.status_code == 403

    # -------------------------------------------------------------
    # ASSERTION 4: User A CANNOT get single order from Business B
    # -------------------------------------------------------------
    leak_single_order = await client.get(
        f"/api/v1/businesses/{biz_b}/orders/{order_b_id}",
        headers=headers_a,
    )
    assert leak_single_order.status_code == 403

    # -------------------------------------------------------------
    # ASSERTION 5: User A CANNOT create an order in Business B
    # -------------------------------------------------------------
    leak_create_order = await client.post(
        f"/api/v1/businesses/{biz_b}/orders",
        json={"items": [{"product_id": prod_b_id, "quantity": 1}]},
        headers=headers_a,
    )
    assert leak_create_order.status_code == 403

    # -------------------------------------------------------------
    # ASSERTION 6: User A CANNOT update Business B's order status
    # -------------------------------------------------------------
    leak_update_status = await client.patch(
        f"/api/v1/businesses/{biz_b}/orders/{order_b_id}/status",
        json={"new_status": "confirmed"},
        headers=headers_a,
    )
    assert leak_update_status.status_code == 403

    # -------------------------------------------------------------
    # ASSERTION 7: User A CANNOT view Business B details
    # -------------------------------------------------------------
    leak_biz_detail = await client.get(
        f"/api/v1/businesses/{biz_b}",
        headers=headers_a,
    )
    assert leak_biz_detail.status_code == 403

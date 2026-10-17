import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_customer_crud_and_search(client: AsyncClient, create_user, create_business):
    """Test creating, listing, searching, and updating customers."""
    user_id, headers = await create_user("cust_owner@example.com")
    business_id = await create_business(user_id, "Customer Hub", "customer-hub")

    # 1. Create customer
    customer_payload = {
        "name": "Jane Doe",
        "phone_number": "+14155552671",
        "email": "jane@example.com",
        "delivery_address": "456 Market St, San Francisco, CA",
        "notes": "VIP client",
    }
    create_res = await client.post(
        f"/api/v1/businesses/{business_id}/customers",
        json=customer_payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    cust_data = create_res.json()
    assert cust_data["name"] == "Jane Doe"
    assert cust_data["phone_number"] == "+14155552671"
    cust_id = cust_data["id"]

    # 2. Duplicate phone rejection in same business
    dup_res = await client.post(
        f"/api/v1/businesses/{business_id}/customers",
        json=customer_payload,
        headers=headers,
    )
    assert dup_res.status_code == 409

    # 3. Get customer detail
    get_res = await client.get(
        f"/api/v1/businesses/{business_id}/customers/{cust_id}",
        headers=headers,
    )
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["id"] == cust_id
    assert "recent_orders" in detail

    # 4. Update customer
    update_res = await client.patch(
        f"/api/v1/businesses/{business_id}/customers/{cust_id}",
        json={"notes": "Updated VIP notes", "name": "Jane Smith"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Jane Smith"
    assert update_res.json()["notes"] == "Updated VIP notes"

    # 5. List and search customers
    list_res = await client.get(
        f"/api/v1/businesses/{business_id}/customers?search=Jane",
        headers=headers,
    )
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == cust_id

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_product(client: AsyncClient, create_user, create_business):
    """Test creating a product and retrieving it by ID."""
    user_id, headers = await create_user("prod_owner@example.com")
    business_id = await create_business(user_id, "Product Shop", "product-shop")

    payload = {
        "name": "Wireless Headset",
        "sku": "WH-100",
        "description": "Noise-cancelling bluetooth headset",
        "price": 89.99,
        "compare_at_price": 109.99,
        "cost_price": 45.00,
        "stock_quantity": 50,
        "track_inventory": True,
    }

    # Create product
    res_create = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json=payload,
        headers=headers,
    )
    assert res_create.status_code == 201
    prod_data = res_create.json()
    assert prod_data["name"] == "Wireless Headset"
    assert prod_data["sku"] == "WH-100"
    assert float(prod_data["price"]) == 89.99
    assert prod_data["stock_quantity"] == 50
    prod_id = prod_data["id"]

    # Get product
    res_get = await client.get(
        f"/api/v1/businesses/{business_id}/products/{prod_id}",
        headers=headers,
    )
    assert res_get.status_code == 200
    assert res_get.json()["id"] == prod_id


@pytest.mark.asyncio
async def test_duplicate_sku_rejection(client: AsyncClient, create_user, create_business):
    """Test duplicate SKU in same business returns 409 Conflict."""
    user_id, headers = await create_user("sku_owner@example.com")
    business_id = await create_business(user_id, "SKU Shop", "sku-shop")

    payload = {
        "name": "Item A",
        "sku": "UNIQUE-SKU",
        "price": 10.00,
    }
    res1 = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json=payload,
        headers=headers,
    )
    assert res1.status_code == 201

    res2 = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json=payload,
        headers=headers,
    )
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_list_and_search_products(client: AsyncClient, create_user, create_business):
    """Test listing products with pagination and text search."""
    user_id, headers = await create_user("search_owner@example.com")
    business_id = await create_business(user_id, "Search Shop", "search-shop")

    for i in range(3):
        await client.post(
            f"/api/v1/businesses/{business_id}/products",
            json={
                "name": f"Gadget #{i+1}",
                "sku": f"GDG-00{i+1}",
                "price": 15.00 * (i + 1),
            },
            headers=headers,
        )

    # List all
    res_list = await client.get(
        f"/api/v1/businesses/{business_id}/products",
        headers=headers,
    )
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Search for specific gadget
    res_search = await client.get(
        f"/api/v1/businesses/{business_id}/products?search=GDG-002",
        headers=headers,
    )
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["sku"] == "GDG-002"


@pytest.mark.asyncio
async def test_archive_product(client: AsyncClient, create_user, create_business):
    """Test archiving a product marks is_archived=True without hard deletion."""
    user_id, headers = await create_user("archive_owner@example.com")
    business_id = await create_business(user_id, "Archive Shop", "archive-shop")

    res_create = await client.post(
        f"/api/v1/businesses/{business_id}/products",
        json={"name": "To Archive", "sku": "ARC-1", "price": 25.00},
        headers=headers,
    )
    prod_id = res_create.json()["id"]

    res_delete = await client.delete(
        f"/api/v1/businesses/{business_id}/products/{prod_id}",
        headers=headers,
    )
    assert res_delete.status_code == 200
    archived_data = res_delete.json()
    assert archived_data["is_archived"] is True
    assert archived_data["is_active"] is False

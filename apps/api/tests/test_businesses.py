import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_business_crud_and_members(client: AsyncClient, create_user):
    """Test business creation, listing, updating, member invitation, and detail retrieval."""
    user_id, headers = await create_user("biz_boss@example.com", "Boss User")

    # 1. Create business
    biz_create_payload = {
        "name": "Acme WhatsApp Store",
        "currency": "EUR",
        "timezone": "Europe/London",
        "phone_number": "+44123456789",
    }
    create_res = await client.post(
        "/api/v1/businesses",
        json=biz_create_payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    biz_data = create_res.json()
    assert biz_data["name"] == "Acme WhatsApp Store"
    assert biz_data["currency"] == "EUR"
    assert biz_data["role"] == "owner"
    assert biz_data["settings"] is not None
    assert biz_data["subscription"] is not None
    biz_id = biz_data["id"]

    # 2. List user businesses
    list_res = await client.get("/api/v1/businesses", headers=headers)
    assert list_res.status_code == 200
    biz_list = list_res.json()
    assert len(biz_list) >= 1
    assert any(b["id"] == biz_id for b in biz_list)

    # 3. Get business detail
    detail_res = await client.get(f"/api/v1/businesses/{biz_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == biz_id

    # 4. Update business (Owner)
    update_res = await client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"name": "Acme Global Store", "timezone": "Europe/Berlin"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Acme Global Store"

    # 5. List members
    members_res = await client.get(f"/api/v1/businesses/{biz_id}/members", headers=headers)
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"
    assert members[0]["email"] == "biz_boss@example.com"

    # 6. Invite member
    invite_res = await client.post(
        f"/api/v1/businesses/{biz_id}/members/invite",
        json={"email": "staff_member@example.com", "role": "staff"},
        headers=headers,
    )
    assert invite_res.status_code == 201
    assert invite_res.json()["role"] == "staff"
    assert invite_res.json()["email"] == "staff_member@example.com"

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.business import BusinessInvitation, BusinessMember
from app.models.customer import Customer
from app.models.whatsapp import Conversation, ConversationTyping


@pytest.mark.asyncio
async def test_invite_create_and_accept(client: AsyncClient, create_user, create_business):
    """Owner invites a member with the agent role."""
    owner_id, headers = await create_user("owner@example.com")
    biz_id = await create_business(owner_id, "Biz A", f"biz-a-{uuid.uuid4().hex[:6]}")

    res = await client.post(
        f"/api/v1/businesses/{biz_id}/team/invites",
        json={"email": "agent@example.com", "role": "agent"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "agent@example.com"
    assert data["role"] == "agent"
    assert data["status"] == "pending"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_invite_accept_with_valid_token(client: AsyncClient, create_user, create_business, db_session):
    """Accepting an invite with a valid token creates an active membership."""
    owner_id, headers = await create_user("owner2@example.com")
    biz_id = await create_business(owner_id, "Biz B", f"biz-b-{uuid.uuid4().hex[:6]}")

    token = "accept-token-12345"
    invite = BusinessInvitation(
        id=uuid.uuid4(),
        business_id=biz_id,
        email="invitee@example.com",
        role="viewer",
        token=token,
        invited_by=owner_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(invite)
    await db_session.commit()

    invitee_id, invitee_headers = await create_user("invitee@example.com")

    accept_res = await client.post(
        f"/api/v1/businesses/{biz_id}/team/invites/accept",
        json={"token": token},
        headers=invitee_headers,
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"
    assert accept_res.json()["role"] == "viewer"

    stmt = select(BusinessMember).where(
        BusinessMember.business_id == biz_id,
        BusinessMember.user_id == invitee_id,
        BusinessMember.is_active.is_(True),
    )
    member = (await db_session.execute(stmt)).scalars().first()
    assert member is not None
    assert member.role == "viewer"


@pytest.mark.asyncio
async def test_invite_accept_expired_token(client: AsyncClient, create_user, create_business, db_session):
    """Accepting an expired invitation returns 410."""
    owner_id, headers = await create_user("owner3@example.com")
    biz_id = await create_business(owner_id, "Biz C", f"biz-c-{uuid.uuid4().hex[:6]}")

    token = "expired-token-67890"
    invite = BusinessInvitation(
        id=uuid.uuid4(),
        business_id=biz_id,
        email="expired@example.com",
        role="staff",
        token=token,
        invited_by=owner_id,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(invite)
    await db_session.commit()

    invitee_id, invitee_headers = await create_user("expired@example.com")

    res = await client.post(
        f"/api/v1/businesses/{biz_id}/team/invites/accept",
        json={"token": token},
        headers=invitee_headers,
    )
    assert res.status_code == 410


@pytest.mark.asyncio
async def test_invite_accept_invalid_token(client: AsyncClient, create_user, create_business):
    """Accepting with a non-existent token returns 404."""
    owner_id, headers = await create_user("owner4@example.com")
    biz_id = await create_business(owner_id, "Biz D", f"biz-d-{uuid.uuid4().hex[:6]}")

    res = await client.post(
        f"/api/v1/businesses/{biz_id}/team/invites/accept",
        json={"token": "does-not-exist"},
        headers=headers,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_invite_list_and_revoke(client: AsyncClient, create_user, create_business):
    """Owner can list and revoke pending invitations."""
    owner_id, headers = await create_user("owner5@example.com")
    biz_id = await create_business(owner_id, "Biz E", f"biz-e-{uuid.uuid4().hex[:6]}")

    await client.post(
        f"/api/v1/businesses/{biz_id}/team/invites",
        json={"email": "revoke@example.com", "role": "staff"},
        headers=headers,
    )

    list_res = await client.get(
        f"/api/v1/businesses/{biz_id}/team/invites", headers=headers
    )
    assert list_res.status_code == 200
    invites = list_res.json()
    assert len(invites) >= 1
    invite_id = invites[0]["id"]

    revoke_res = await client.delete(
        f"/api/v1/businesses/{biz_id}/team/invites/{invite_id}", headers=headers
    )
    assert revoke_res.status_code == 200


@pytest.mark.asyncio
async def test_member_role_update(client: AsyncClient, create_user, create_business, db_session):
    """Owner can update a member's role."""
    owner_id, headers = await create_user("owner6@example.com")
    biz_id = await create_business(owner_id, "Biz F", f"biz-f-{uuid.uuid4().hex[:6]}")

    member_id = uuid.uuid4()
    member = BusinessMember(
        id=member_id,
        business_id=biz_id,
        user_id=uuid.uuid4(),
        role="staff",
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()

    res = await client.patch(
        f"/api/v1/businesses/{biz_id}/team/members/{member_id}/role",
        json={"role": "agent"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["role"] == "agent"


@pytest.mark.asyncio
async def test_list_activity_logs(client: AsyncClient, create_user, create_business, db_session):
    """Activity logs are listed paginated for a business."""
    owner_id, headers = await create_user("owner13@example.com")
    biz_id = await create_business(owner_id, "Biz M", f"biz-m-{uuid.uuid4().hex[:6]}")

    from app.models.business import AgentActivityLog
    db_session.add(
        AgentActivityLog(
            id=uuid.uuid4(),
            business_id=biz_id,
            user_id=owner_id,
            action="conversation_assign",
            resource_type="conversation",
            resource_id=uuid.uuid4(),
        )
    )
    await db_session.commit()

    res = await client.get(
        f"/api/v1/businesses/{biz_id}/team/activity", headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1



@pytest.mark.asyncio
async def test_list_members(client: AsyncClient, create_user, create_business, db_session):
    """Listing members returns all active members with emails."""
    owner_id, headers = await create_user("owner7@example.com")
    biz_id = await create_business(owner_id, "Biz G", f"biz-g-{uuid.uuid4().hex[:6]}")

    res = await client.get(f"/api/v1/businesses/{biz_id}/team/members", headers=headers)
    assert res.status_code == 200
    members = res.json()
    assert any(m["email"] == "owner7@example.com" for m in members)


@pytest.mark.asyncio
async def test_activity_logging_on_assign(
    client: AsyncClient, create_user, create_business, db_session
):
    """Assigning a conversation creates an agent activity log entry."""
    owner_id, headers = await create_user("owner8@example.com")
    biz_id = await create_business(owner_id, "Biz H", f"biz-h-{uuid.uuid4().hex[:6]}")

    cust = Customer(business_id=biz_id, name="Cust", phone_number="+15551112222")
    db_session.add(cust)
    await db_session.flush()

    conv = Conversation(business_id=biz_id, customer_id=cust.id, status="open")
    db_session.add(conv)
    await db_session.commit()
    conv_id = conv.id

    agent_id, agent_headers = await create_user("agent@example.com")
    member = BusinessMember(
        id=uuid.uuid4(),
        business_id=biz_id,
        user_id=agent_id,
        role="agent",
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()

    assign_res = await client.post(
        f"/api/v1/businesses/{biz_id}/conversations/{conv_id}/assign",
        json={"user_id": str(agent_id)},
        headers=headers,
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_to"] == str(agent_id)

    from app.models.business import AgentActivityLog
    stmt = select(AgentActivityLog).where(
        AgentActivityLog.business_id == biz_id,
        AgentActivityLog.action == "conversation_assign",
    )
    logs = (await db_session.execute(stmt)).scalars().all()
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_unassign_conversation(client: AsyncClient, create_user, create_business, db_session):
    """Unassigning a conversation sets assigned_to to null."""
    owner_id, headers = await create_user("owner9@example.com")
    biz_id = await create_business(owner_id, "Biz I", f"biz-i-{uuid.uuid4().hex[:6]}")

    cust = Customer(business_id=biz_id, name="Cust2", phone_number="+15553334444")
    db_session.add(cust)
    await db_session.flush()

    conv = Conversation(
        business_id=biz_id, customer_id=cust.id, status="open", assigned_to=uuid.uuid4()
    )
    db_session.add(conv)
    await db_session.commit()
    conv_id = conv.id

    unassign_res = await client.post(
        f"/api/v1/businesses/{biz_id}/conversations/{conv_id}/assign",
        json={"user_id": None},
        headers=headers,
    )
    assert unassign_res.status_code == 200
    assert unassign_res.json()["assigned_to"] is None


@pytest.mark.asyncio
async def test_my_conversations_filter(client: AsyncClient, create_user, create_business, db_session):
    """'mine=true' returns only conversations assigned to the current user."""
    owner_id, headers = await create_user("owner10@example.com")
    biz_id = await create_business(owner_id, "Biz J", f"biz-j-{uuid.uuid4().hex[:6]}")

    cust = Customer(business_id=biz_id, name="Cust3", phone_number="+15555556666")
    db_session.add(cust)
    await db_session.flush()

    agent_id, agent_headers = await create_user("agent10@example.com")
    member = BusinessMember(
        id=uuid.uuid4(),
        business_id=biz_id,
        user_id=agent_id,
        role="agent",
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()

    conv_a = Conversation(
        business_id=biz_id, customer_id=cust.id, status="open", assigned_to=agent_id
    )
    conv_b = Conversation(business_id=biz_id, customer_id=cust.id, status="open", assigned_to=None)
    db_session.add_all([conv_a, conv_b])
    await db_session.commit()

    res = await client.get(
        f"/api/v1/businesses/{biz_id}/conversations?mine=true", headers=agent_headers
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert all(item["assigned_to"] == str(agent_id) for item in items)
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_typing_indicator_set_and_get(
    client: AsyncClient, create_user, create_business, db_session
):
    """Agent can set typing state and dashboard can fetch who is typing."""
    owner_id, headers = await create_user("owner11@example.com")
    biz_id = await create_business(owner_id, "Biz K", f"biz-k-{uuid.uuid4().hex[:6]}")

    cust = Customer(business_id=biz_id, name="Cust4", phone_number="+15557778888")
    db_session.add(cust)
    await db_session.flush()

    conv = Conversation(business_id=biz_id, customer_id=cust.id, status="open")
    db_session.add(conv)
    await db_session.commit()
    conv_id = conv.id

    agent_id, agent_headers = await create_user("agent11@example.com")
    member = BusinessMember(
        id=uuid.uuid4(),
        business_id=biz_id,
        user_id=agent_id,
        role="agent",
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()

    set_res = await client.post(
        f"/api/v1/businesses/{biz_id}/team/conversations/{conv_id}/typing",
        json={"is_typing": True},
        headers=agent_headers,
    )
    assert set_res.status_code == 200
    assert set_res.json()["is_typing"] is True

    get_res = await client.get(
        f"/api/v1/businesses/{biz_id}/team/conversations/{conv_id}/typing",
        headers=agent_headers,
    )
    assert get_res.status_code == 200
    typing_users = get_res.json()
    assert any(u["user_id"] == str(agent_id) and u["is_typing"] is True for u in typing_users)

    clear_res = await client.post(
        f"/api/v1/businesses/{biz_id}/team/conversations/{conv_id}/typing",
        json={"is_typing": False},
        headers=agent_headers,
    )
    assert clear_res.status_code == 200
    assert clear_res.json()["is_typing"] is False


@pytest.mark.asyncio
async def test_typing_indicator_tenant_isolation(
    client: AsyncClient, create_user, create_business, db_session
):
    """Agent from Tenant B cannot set typing in Tenant A's conversation."""
    owner_a, headers_a = await create_user("owner_a_typing@example.com")
    biz_a = await create_business(owner_a, "Biz TA", f"biz-ta-{uuid.uuid4().hex[:6]}")

    owner_b, headers_b = await create_user("owner_b_typing@example.com")
    biz_b = await create_business(owner_b, "Biz TB", f"biz-tb-{uuid.uuid4().hex[:6]}")

    cust = Customer(business_id=biz_a, name="CustTA", phone_number="+15559990000")
    db_session.add(cust)
    await db_session.flush()

    conv = Conversation(business_id=biz_a, customer_id=cust.id, status="open")
    db_session.add(conv)
    await db_session.commit()
    conv_id = conv.id

    res = await client.post(
        f"/api/v1/businesses/{biz_b}/team/conversations/{conv_id}/typing",
        json={"is_typing": True},
        headers=headers_b,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_agent_cannot_invite(
    client: AsyncClient, create_user, create_business, db_session
):
    """Agent role cannot create invitations (owner/manager only)."""
    owner_id, headers = await create_user("owner12@example.com")
    biz_id = await create_business(owner_id, "Biz L", f"biz-l-{uuid.uuid4().hex[:6]}")

    agent_id, agent_headers = await create_user("agent12@example.com")
    db_session.add(
        BusinessMember(
            id=uuid.uuid4(),
            business_id=biz_id,
            user_id=agent_id,
            role="agent",
            is_active=True,
        )
    )
    await db_session.commit()

    res = await client.post(
        f"/api/v1/businesses/{biz_id}/team/invites",
        json={"email": "nope@example.com", "role": "staff"},
        headers=agent_headers,
    )
    assert res.status_code == 403





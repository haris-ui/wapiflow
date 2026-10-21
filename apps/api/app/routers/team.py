import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    CurrentUser,
    TenantContext,
    get_current_user,
    get_tenant_context,
    require_role,
)
from app.schemas.business import BusinessMemberResponse
from app.schemas.common import PaginatedResponse
from app.schemas.team import (
    AgentActivityLogResponse,
    BusinessInviteAccept,
    BusinessInviteCreate,
    BusinessInviteResponse,
    ConversationTypingResponse,
    ConversationTypingSet,
    PaginatedActivityLogResponse,
    TeamMemberRoleUpdate,
)
from app.services.team_service import TeamService

router = APIRouter(
    prefix="/businesses/{business_id}/team",
    tags=["Team & Multi-Agent"],
)


@router.post(
    "/invites",
    response_model=BusinessInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a team member to the business (Owner/Manager)",
)
async def invite_member(
    invite_in: BusinessInviteCreate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
    db: AsyncSession = Depends(get_db),
) -> BusinessInviteResponse:
    """Create a pending invitation for a team member."""
    return await TeamService.invite_member(db, business_id, tenant.user_id, invite_in)


@router.post(
    "/invites/accept",
    response_model=BusinessInviteResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept a pending invitation",
)
async def accept_invite(
    accept_in: BusinessInviteAccept,
    business_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BusinessInviteResponse:
    """Accept a pending invitation and join the business."""
    return await TeamService.accept_invite(
        db, current_user.id, business_id, accept_in.token
    )


@router.get(
    "/invites",
    response_model=List[BusinessInviteResponse],
    status_code=status.HTTP_200_OK,
    summary="List pending invitations for the business",
)
async def list_invites(
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> List[BusinessInviteResponse]:
    """List all invitations for the business."""
    return await TeamService.list_invites(db, business_id)


@router.delete(
    "/invites/{invite_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke a pending invitation (Owner/Manager)",
)
async def revoke_invite(
    invite_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a pending invitation."""
    return await TeamService.revoke_invite(db, business_id, invite_id)


@router.patch(
    "/members/{member_id}/role",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Update a team member's role (Owner only)",
)
async def update_member_role(
    member_id: uuid.UUID,
    role_in: TeamMemberRoleUpdate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner"])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update the role of a team member."""
    return await TeamService.update_member_role(
        db, business_id, member_id, role_in.role, tenant.user_id
    )


@router.get(
    "/members",
    response_model=List[BusinessMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List business team members",
)
async def list_members(
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> List[BusinessMemberResponse]:
    """List all active team members of the business."""
    from app.services.business_service import BusinessService

    return await BusinessService.list_members(db, business_id)


@router.get(
    "/activity",
    response_model=PaginatedActivityLogResponse,
    status_code=status.HTTP_200_OK,
    summary="List agent activity logs",
)
async def list_activity_logs(
    business_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> PaginatedActivityLogResponse:
    """List paginated agent activity logs for the business."""
    return await TeamService.list_activity_logs(db, business_id, page, page_size)


@router.post(
    "/conversations/{conversation_id}/typing",
    response_model=ConversationTypingResponse,
    status_code=status.HTTP_200_OK,
    summary="Set or clear typing indicator in a conversation",
)
async def set_typing(
    conversation_id: uuid.UUID,
    typing_in: ConversationTypingSet,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ConversationTypingResponse:
    """Set or clear the typing state for the current user in a conversation."""
    return await TeamService.set_typing(
        db, tenant, conversation_id, typing_in.is_typing
    )


@router.get(
    "/conversations/{conversation_id}/typing",
    response_model=List[ConversationTypingResponse],
    status_code=status.HTTP_200_OK,
    summary="Get users currently typing in a conversation",
)
async def get_typing(
    conversation_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationTypingResponse]:
    """Return users currently typing in the conversation."""
    return await TeamService.get_typing(db, business_id, conversation_id)

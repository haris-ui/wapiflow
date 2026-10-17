import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    CurrentUser,
    TenantContext,
    get_current_user,
    get_tenant_context,
    require_role,
)
from app.schemas.business import (
    BusinessCreate,
    BusinessListItem,
    BusinessMemberInvite,
    BusinessMemberResponse,
    BusinessResponse,
    BusinessUpdate,
)
from app.services.business_service import BusinessService

router = APIRouter(prefix="/businesses", tags=["Businesses"])


@router.post(
    "",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new business tenant",
)
async def create_business(
    business_in: BusinessCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BusinessResponse:
    """Create a new business tenant workspace with owner privileges."""
    return await BusinessService.create_business(db, current_user.id, business_in)


@router.get(
    "",
    response_model=List[BusinessListItem],
    status_code=status.HTTP_200_OK,
    summary="List all businesses for authenticated user",
)
async def list_businesses(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[BusinessListItem]:
    """Retrieve all businesses where the authenticated user is an active team member."""
    return await BusinessService.list_user_businesses(db, current_user.id)


@router.get(
    "/{business_id}",
    response_model=BusinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get business tenant details",
)
async def get_business(
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> BusinessResponse:
    """Get full details of a business tenant after verifying membership."""
    return await BusinessService.get_business_detail(db, business_id, tenant.user_id)


@router.patch(
    "/{business_id}",
    response_model=BusinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Update business tenant (Owner/Manager only)",
)
async def update_business(
    business_in: BusinessUpdate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
    db: AsyncSession = Depends(get_db),
) -> BusinessResponse:
    """Update settings and profile for a business tenant."""
    return await BusinessService.update_business(db, business_id, business_in)


@router.get(
    "/{business_id}/members",
    response_model=List[BusinessMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List business team members",
)
async def list_members(
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> List[BusinessMemberResponse]:
    """List all team members of the business."""
    return await BusinessService.list_members(db, business_id)


@router.post(
    "/{business_id}/members/invite",
    response_model=BusinessMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite team member by email (Owner only)",
)
async def invite_member(
    invite_in: BusinessMemberInvite,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner"])),
    db: AsyncSession = Depends(get_db),
) -> BusinessMemberResponse:
    """Invite an existing user or newly registered email as business team member."""
    return await BusinessService.invite_member(db, business_id, invite_in)

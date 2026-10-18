import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import TenantContext, get_tenant_context, require_role
from app.schemas.whatsapp import (
    TestMessageRequest,
    WhatsAppAccountConnect,
    WhatsAppAccountResponse,
    WhatsAppConfigInfo,
)
from app.services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/businesses/{business_id}/whatsapp", tags=["WhatsApp Settings"])


@router.get(
    "",
    response_model=WhatsAppConfigInfo,
    status_code=status.HTTP_200_OK,
    summary="Get WhatsApp connection status and webhook config",
)
async def get_whatsapp_config(
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> WhatsAppConfigInfo:
    """Retrieve WhatsApp connection status, registered phone numbers, and webhook configuration."""
    return await WhatsAppService.get_config_info(db, tenant)


@router.post(
    "/connect",
    response_model=WhatsAppAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Connect or update Meta WhatsApp Cloud API credentials",
)
async def connect_whatsapp(
    data: WhatsAppAccountConnect,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
    db: AsyncSession = Depends(get_db),
) -> WhatsAppAccountResponse:
    """Connect WABA ID, Phone Number, and permanent System User Access Token to tenant."""
    return await WhatsAppService.connect_account(db, tenant, data)


@router.post(
    "/disconnect",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Disconnect WhatsApp integration",
)
async def disconnect_whatsapp(
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner"])),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Disconnect WhatsApp integration and clear access tokens (Owner only)."""
    return await WhatsAppService.disconnect_account(db, tenant)


@router.post(
    "/test",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Send a test WhatsApp message",
)
async def send_test_message(
    data: TestMessageRequest,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Dispatches a test message via Meta WhatsApp Cloud API to verify connection."""
    return await WhatsAppService.send_test_message(db, tenant, data)

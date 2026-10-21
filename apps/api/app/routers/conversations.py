import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import TenantContext, get_tenant_context
from app.schemas.common import PaginatedResponse
from app.schemas.conversation import (
    ConversationAssign,
    ConversationDetailResponse,
    ConversationQuickOrderCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.schemas.order import OrderResponse
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/businesses/{business_id}/conversations", tags=["Conversations & Inbox"])


@router.get(
    "",
    response_model=PaginatedResponse[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List conversations with filters and search",
)
async def list_conversations(
    business_id: uuid.UUID,
    status: Optional[str] = Query(None, description="Filter by status: open, resolved, snoozed"),
    search: Optional[str] = Query(None, description="Search by customer name, phone, or message"),
    assigned_to: Optional[uuid.UUID] = Query(None, description="Filter by assigned agent user ID"),
    mine: bool = Query(False, description="If true, only conversations assigned to the current user"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ConversationResponse]:
    """Retrieve paginated conversations for the business inbox."""
    return await ConversationService.get_conversations(
        db=db,
        tenant=tenant,
        status_filter=status,
        search=search,
        assigned_to=assigned_to,
        mine=mine,
        current_user_id=tenant.user_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{conversation_id}/assign",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign or unassign a conversation to an agent",
)
async def assign_conversation(
    conversation_id: uuid.UUID,
    assign_in: ConversationAssign,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Assign a conversation to an agent (or unassign when user_id is null)."""
    return await ConversationService.assign_conversation(
        db=db,
        tenant=tenant,
        conversation_id=conversation_id,
        user_id=assign_in.user_id,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation detail with customer orders",
)
async def get_conversation_detail(
    conversation_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    """Retrieve conversation detail, mark thread as read, and attach customer recent orders."""
    return await ConversationService.get_conversation_detail(db, tenant, conversation_id)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update conversation status or assigned staff",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    update_data: ConversationUpdate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Resolve, snooze, or reopen conversation, or assign to staff member."""
    return await ConversationService.update_conversation(db, tenant, conversation_id, update_data)


@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedResponse[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get chronological messages in a conversation",
)
async def get_messages(
    conversation_id: uuid.UUID,
    business_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MessageResponse]:
    """Retrieve messages for an active conversation thread."""
    return await ConversationService.get_messages(
        db=db,
        tenant=tenant,
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send outbound WhatsApp message or add internal note",
)
async def send_message(
    conversation_id: uuid.UUID,
    message_in: MessageCreate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Sends an outbound message to customer via WhatsApp Cloud API,
    or stores an internal team note (when is_internal_note=true).
    """
    return await ConversationService.send_message(db, tenant, conversation_id, message_in)


@router.post(
    "/{conversation_id}/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Quickly create an order from conversation context",
)
async def create_quick_order(
    conversation_id: uuid.UUID,
    order_in: ConversationQuickOrderCreate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Creates an order linked to the customer and conversation context.
    Automatically calculates totals, decrements inventory, and posts confirmation note.
    """
    return await ConversationService.create_order_from_conversation(
        db=db,
        tenant=tenant,
        conversation_id=conversation_id,
        order_in=order_in,
    )

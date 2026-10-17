import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import TenantContext, get_tenant_context
from app.schemas.common import PaginatedResponse
from app.schemas.order import (
    OrderCreate,
    OrderListItem,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/businesses/{business_id}/orders", tags=["Orders"])


@router.get(
    "",
    response_model=PaginatedResponse[OrderListItem],
    status_code=status.HTTP_200_OK,
    summary="List orders with filters and pagination",
)
async def list_orders(
    business_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    customer_id: Optional[uuid.UUID] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    payment_status: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OrderListItem]:
    """Retrieve paginated orders for the business tenant with comprehensive filters."""
    return await OrderService.get_orders(
        db=db,
        tenant=tenant,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        payment_status=payment_status,
        source=source,
    )


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order transactionally",
)
async def create_order(
    order_in: OrderCreate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Create a new order transactionally:
    - Validates product ownership
    - Computes totals on server
    - Records line items and initial status history
    - Adjusts stock levels if auto-decrement is enabled
    """
    return await OrderService.create_order(db, tenant, order_in)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get order details with line items and history",
)
async def get_order(
    order_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Retrieve complete order details including snapshot line items and transition history."""
    return await OrderService.get_order_detail(db, tenant, order_id)


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Transition order status",
)
async def transition_order_status(
    status_in: OrderStatusUpdate,
    order_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Transition order state according to valid lifecycle rules:
    pending -> confirmed, cancelled
    confirmed -> preparing, cancelled
    preparing -> ready_for_dispatch, cancelled
    ready_for_dispatch -> shipped, cancelled
    shipped -> delivered, cancelled
    """
    return await OrderService.transition_status(
        db=db,
        tenant=tenant,
        order_id=order_id,
        new_status=status_in.new_status,
        notes=status_in.notes,
        changed_by=tenant.user_id,
    )


@router.patch(
    "/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update order attributes",
)
async def update_order(
    order_in: OrderUpdate,
    order_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order fulfillment details and notes."""
    return await OrderService.update_order(db, tenant, order_id, order_in)

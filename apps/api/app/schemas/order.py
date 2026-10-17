import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.customer import CustomerResponse

VALID_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["preparing", "cancelled"],
    "preparing": ["ready_for_dispatch", "cancelled"],
    "ready_for_dispatch": ["shipped", "cancelled"],
    "shipped": ["delivered", "cancelled"],
    "delivered": [],
    "cancelled": [],
}


class OrderItemCreate(BaseSchema):
    """Payload to add an item to a new order."""

    product_id: uuid.UUID
    quantity: int = Field(..., gt=0, description="Quantity ordered (must be >= 1)")


class OrderItemResponse(BaseSchema):
    """Order line item response with product snapshot."""

    id: uuid.UUID
    order_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    product_name: str
    product_sku: str
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    created_at: datetime


class OrderStatusHistoryResponse(BaseSchema):
    """Audit log entry for order state transitions."""

    id: uuid.UUID
    order_id: uuid.UUID
    previous_status: Optional[str] = None
    new_status: str
    notes: Optional[str] = None
    changed_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime


class OrderCreate(BaseSchema):
    """Payload to create an order transactionally."""

    items: List[OrderItemCreate] = Field(..., min_length=1, description="List of items to order")
    customer_id: Optional[uuid.UUID] = None
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=32)
    notes: Optional[str] = None
    fulfillment_address: Optional[str] = None
    source: str = Field(default="manual", pattern="^(whatsapp|manual|web)$")
    idempotency_key: Optional[str] = Field(None, max_length=128)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    shipping_fee: Decimal = Field(default=Decimal("0.00"), ge=0)


class OrderUpdate(BaseSchema):
    """Permitted fields for non-status order updates."""

    notes: Optional[str] = None
    fulfillment_address: Optional[str] = None


class OrderStatusUpdate(BaseSchema):
    """Payload for transitioning order status."""

    new_status: str = Field(
        ...,
        pattern="^(pending|confirmed|preparing|ready_for_dispatch|shipped|delivered|cancelled)$",
    )
    notes: Optional[str] = None


class OrderListItem(BaseSchema):
    """Lightweight representation for paginated order lists."""

    id: uuid.UUID
    business_id: uuid.UUID
    order_number: str
    customer_id: Optional[uuid.UUID] = None
    customer_name: Optional[str] = None
    status: str
    payment_status: str
    source: str
    total_amount: Decimal
    currency: str
    items_count: int
    created_at: datetime


class OrderResponse(BaseSchema):
    """Complete detail response of an order."""

    id: uuid.UUID
    business_id: uuid.UUID
    order_number: str
    customer_id: Optional[uuid.UUID] = None
    customer: Optional[CustomerResponse] = None
    status: str
    payment_status: str
    source: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    shipping_fee: Decimal
    total_amount: Decimal
    currency: str
    notes: Optional[str] = None
    fulfillment_address: Optional[str] = None
    idempotency_key: Optional[str] = None
    items: List[OrderItemResponse] = Field(default_factory=list)
    status_history: List[OrderStatusHistoryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

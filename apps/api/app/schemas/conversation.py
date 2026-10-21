import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field
from app.schemas.common import BaseSchema
from app.schemas.order import OrderCreate, OrderItemCreate, OrderResponse


class MessageCreate(BaseSchema):
    """Schema for sending an outbound message or adding an internal note in a conversation."""

    content: str = Field(..., min_length=1, max_length=4096, description="Message text or note content")
    message_type: str = Field("text", description="Type: text, template, or image")
    is_internal_note: bool = Field(False, description="True if team-internal note (not sent to customer over WhatsApp)")


class MessageResponse(BaseSchema):
    """WhatsApp message representation."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    business_id: uuid.UUID
    wa_message_id: Optional[str] = None
    direction: str  # inbound, outbound
    message_type: str
    content: Optional[str] = None
    media_url: Optional[str] = None
    status: str  # pending, sent, delivered, read, failed
    error_message: Optional[str] = None
    is_internal_note: bool = False
    created_at: datetime


class ConversationCustomerInfo(BaseSchema):
    """Customer summary attached to conversation."""

    id: uuid.UUID
    name: str
    phone_number: str
    email: Optional[str] = None


class ConversationResponse(BaseSchema):
    """Conversation summary for the inbox list."""

    id: uuid.UUID
    business_id: uuid.UUID
    customer_id: Optional[uuid.UUID] = None
    customer: Optional[ConversationCustomerInfo] = None
    status: str  # open, resolved, snoozed
    assigned_to: Optional[uuid.UUID] = None
    unread_count: int = 0
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    """Detailed conversation view with customer and latest orders."""

    recent_orders: List[OrderResponse] = []


class ConversationUpdate(BaseSchema):
    """Schema to update conversation state."""

    status: Optional[str] = Field(None, description="One of: open, resolved, snoozed")
    assigned_to: Optional[uuid.UUID] = Field(None, description="Staff user ID to assign to")


class ConversationQuickOrderCreate(BaseSchema):
    """Quick order generation from conversation context."""

    items: List[OrderItemCreate] = Field(..., min_length=1, description="List of products and quantities")
    notes: Optional[str] = Field(None, max_length=1000, description="Order notes")
    fulfillment_address: Optional[str] = Field(None, max_length=500)
    idempotency_key: Optional[str] = Field(None, max_length=128)


class ConversationAssign(BaseSchema):
    """Payload to assign or unassign a conversation to an agent."""

    user_id: Optional[uuid.UUID] = Field(
        None, description="Agent user ID to assign; null to unassign"
    )

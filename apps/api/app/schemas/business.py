import uuid
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class BusinessCreate(BaseSchema):
    """Payload to create a new business tenant."""

    name: str = Field(..., min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    timezone: str = Field(default="UTC", max_length=64)


class BusinessUpdate(BaseSchema):
    """Payload to update an existing business tenant."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    timezone: Optional[str] = Field(None, max_length=64)
    logo_url: Optional[str] = Field(None, max_length=1024)


class BusinessSettingsResponse(BaseSchema):
    """Business operational configuration response."""

    id: uuid.UUID
    business_id: uuid.UUID
    auto_decrement_stock: bool
    order_prefix: str
    whatsapp_catalog_id: Optional[str] = None
    notification_phone: Optional[str] = None


class BusinessSettingsUpdate(BaseSchema):
    """Payload to update business operational settings."""

    auto_decrement_stock: Optional[bool] = None
    order_prefix: Optional[str] = Field(None, max_length=16)
    whatsapp_catalog_id: Optional[str] = Field(None, max_length=255)
    notification_phone: Optional[str] = Field(None, max_length=32)


class SubscriptionResponse(BaseSchema):
    """Business subscription status."""

    id: uuid.UUID
    business_id: uuid.UUID
    plan_tier: str
    status: str
    current_period_end: Optional[datetime] = None


class BusinessResponse(BaseSchema):
    """Full detail of a business tenant."""

    id: uuid.UUID
    name: str
    slug: str
    phone_number: Optional[str] = None
    currency: str
    timezone: str
    logo_url: Optional[str] = None
    is_active: bool
    role: Optional[str] = None
    settings: Optional[BusinessSettingsResponse] = None
    subscription: Optional[SubscriptionResponse] = None
    created_at: datetime
    updated_at: datetime


class BusinessListItem(BaseSchema):
    """Lightweight summary of a business for listing endpoints."""

    id: uuid.UUID
    name: str
    slug: str
    currency: str
    role: str
    is_active: bool
    created_at: datetime


class BusinessMemberResponse(BaseSchema):
    """Business team member details."""

    id: uuid.UUID
    business_id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime


class BusinessMemberInvite(BaseSchema):
    """Payload to invite a new team member to the business."""

    email: EmailStr
    role: str = Field(default="staff", pattern="^(manager|staff)$")

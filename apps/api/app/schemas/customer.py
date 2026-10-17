import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class CustomerCreate(BaseSchema):
    """Payload to create a new customer."""

    name: str = Field(..., min_length=1, max_length=255)
    phone_number: str = Field(..., min_length=7, max_length=32)
    email: Optional[EmailStr] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None


class CustomerUpdate(BaseSchema):
    """Payload to update an existing customer."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=32)
    email: Optional[EmailStr] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None


class CustomerResponse(BaseSchema):
    """Customer entity response."""

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    phone_number: str
    email: Optional[EmailStr] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    total_orders: int
    total_spend: Decimal
    created_at: datetime
    updated_at: datetime


class CustomerListItem(BaseSchema):
    """Lighter customer representation for customer lists."""

    id: uuid.UUID
    name: str
    phone_number: str
    email: Optional[EmailStr] = None
    total_orders: int
    total_spend: Decimal
    created_at: datetime


class CustomerDetailResponse(CustomerResponse):
    """Detailed customer information including recent order summary."""

    recent_orders: List[dict] = Field(default_factory=list)

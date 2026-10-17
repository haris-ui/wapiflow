import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field

from app.schemas.common import BaseSchema


class ProductCreate(BaseSchema):
    """Payload to create a new product."""

    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0, description="Unit selling price")
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    track_inventory: bool = True
    image_url: Optional[str] = Field(None, max_length=1024)
    is_active: bool = True


class ProductUpdate(BaseSchema):
    """Payload to update an existing product."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    track_inventory: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=1024)
    is_active: Optional[bool] = None


class ProductResponse(BaseSchema):
    """Full product details."""

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    sku: str
    description: Optional[str] = None
    price: Decimal
    compare_at_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    stock_quantity: int
    track_inventory: bool
    image_url: Optional[str] = None
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ProductListItem(BaseSchema):
    """Lighter representation for product catalogs/tables."""

    id: uuid.UUID
    name: str
    sku: str
    price: Decimal
    stock_quantity: int
    track_inventory: bool
    is_active: bool
    is_archived: bool
    image_url: Optional[str] = None


class InventoryMovementResponse(BaseSchema):
    """Stock adjustment record response."""

    id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    change_quantity: int
    movement_type: str
    notes: Optional[str] = None
    created_at: datetime

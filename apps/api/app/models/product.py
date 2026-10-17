import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.order import Order, OrderItem


class Product(Base, TimestampMixin):
    """Product catalog item belonging to a business tenant."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("business_id", "sku", name="uq_business_product_sku"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    compare_at_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    cost_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    track_inventory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="products",
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="product",
    )
    inventory_movements: Mapped[List["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class InventoryMovement(Base, TimestampMixin):
    """Audit log of stock level changes."""

    __tablename__ = "inventory_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("orders.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    change_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,  # order_fulfillment, order_cancellation, manual_adjustment, restock
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="inventory_movements",
    )
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="inventory_movements",
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        back_populates="inventory_movements",
    )

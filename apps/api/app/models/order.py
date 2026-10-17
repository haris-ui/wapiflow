import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.customer import Customer
    from app.models.product import Product, InventoryMovement
    from app.models.profile import Profile


class Order(Base, TimestampMixin):
    """Order record belonging to a business tenant."""

    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("business_id", "idempotency_key", name="uq_business_order_idempotency"),
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
    order_number: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("customers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",  # pending, confirmed, preparing, ready_for_dispatch, shipped, delivered, cancelled
        index=True,
        nullable=False,
    )
    payment_status: Mapped[str] = mapped_column(
        String(32),
        default="unpaid",  # unpaid, paid, refunded, partially_paid
        index=True,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(32),
        default="manual",  # whatsapp, manual, web
        index=True,
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    shipping_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    fulfillment_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(128),
        index=True,
        nullable=True,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="orders",
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="orders",
    )
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.created_at",
    )
    status_history: Mapped[List["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )
    inventory_movements: Mapped[List["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="order",
    )


class OrderItem(Base, TimestampMixin):
    """Line item in an order with snapshot product attributes."""

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    product_sku: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )
    product: Mapped[Optional["Product"]] = relationship(
        "Product",
        back_populates="order_items",
    )


class OrderStatusHistory(Base, TimestampMixin):
    """Audit log of order state transitions."""

    __tablename__ = "order_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    previous_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    new_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="status_history",
    )
    changed_by_profile: Mapped[Optional["Profile"]] = relationship(
        "Profile",
        back_populates="order_changes",
    )

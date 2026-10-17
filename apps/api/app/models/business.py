import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.product import Product, InventoryMovement
    from app.models.order import Order
    from app.models.customer import Customer
    from app.models.whatsapp import WhatsAppConnection


class Business(Base, TimestampMixin):
    """Business entity representing an isolated tenant in WapiFlow."""

    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(64),
        default="UTC",
        nullable=False,
    )
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    settings: Mapped[Optional["BusinessSettings"]] = relationship(
        "BusinessSettings",
        back_populates="business",
        uselist=False,
        cascade="all, delete-orphan",
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="business",
        uselist=False,
        cascade="all, delete-orphan",
    )
    members: Mapped[List["BusinessMember"]] = relationship(
        "BusinessMember",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    customers: Mapped[List["Customer"]] = relationship(
        "Customer",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    inventory_movements: Mapped[List["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    whatsapp_connection: Mapped[Optional["WhatsAppConnection"]] = relationship(
        "WhatsAppConnection",
        back_populates="business",
        uselist=False,
        cascade="all, delete-orphan",
    )


class BusinessMember(Base, TimestampMixin):
    """Membership connecting users to businesses with specific roles."""

    __tablename__ = "business_members"
    __table_args__ = (
        UniqueConstraint("business_id", "user_id", name="uq_business_member"),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        default="staff",  # owner, manager, staff
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="members",
    )
    profile: Mapped["Profile"] = relationship(
        "Profile",
        back_populates="memberships",
    )


class BusinessSettings(Base, TimestampMixin):
    """Per-business operational configurations."""

    __tablename__ = "business_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    auto_decrement_stock: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    order_prefix: Mapped[str] = mapped_column(
        String(16),
        default="WF-",
        nullable=False,
    )
    whatsapp_catalog_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    notification_phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="settings",
    )


class Subscription(Base, TimestampMixin):
    """Business subscription tier and billing status."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    plan_tier: Mapped[str] = mapped_column(
        String(32),
        default="free",  # free, starter, pro, enterprise
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",  # active, past_due, canceled
        nullable=False,
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="subscription",
    )

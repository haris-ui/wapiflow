import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.product import Product, InventoryMovement
    from app.models.order import Order
    from app.models.customer import Customer
    from app.models.whatsapp import WhatsAppAccount


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
    whatsapp_account: Mapped[Optional["WhatsAppAccount"]] = relationship(
        "WhatsAppAccount",
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
        default="staff",  # owner, manager, staff, agent, viewer
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


class BusinessInvitation(Base, TimestampMixin):
    """Pending team-member invitation for a business tenant."""

    __tablename__ = "business_invitations"
    __table_args__ = (
        UniqueConstraint("business_id", "email", name="uq_business_invitation_business_email"),
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
    email: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        default="staff",
        nullable=False,  # manager, staff, agent, viewer
    )
    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business")
    inviter: Mapped[Optional["Profile"]] = relationship("Profile")


class AgentActivityLog(Base):
    """Immutable audit log of agent/team activity within a business tenant."""

    __tablename__ = "agent_activity_logs"

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
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("profiles.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,  # invite_accept, conversation_assign, conversation_unassign, status_change, message_send, typing_start, typing_stop
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business")
    user: Mapped[Optional["Profile"]] = relationship("Profile")


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

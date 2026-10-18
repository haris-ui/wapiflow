import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.order import Order
    from app.models.whatsapp import Conversation


class Customer(Base, TimestampMixin):
    """Customer entity per business tenant."""

    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("business_id", "phone_number", name="uq_business_customer_phone"),
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
    phone_number: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    delivery_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    total_orders: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_spend: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="customers",
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="customer",
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

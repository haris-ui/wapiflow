import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.customer import Customer


class WhatsAppConnection(Base, TimestampMixin):
    """WhatsApp Cloud API configuration per business tenant."""

    __tablename__ = "whatsapp_connections"

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
    phone_number_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    waba_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    display_phone_number: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    quality_rating: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    webhook_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    access_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="whatsapp_connection",
    )


class WhatsAppMessage(Base, TimestampMixin):
    """Audit log of inbound and outbound WhatsApp conversations."""

    __tablename__ = "whatsapp_messages"

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
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("customers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    wa_message_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,  # inbound, outbound
    )
    sender_phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    recipient_phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    message_type: Mapped[str] = mapped_column(
        String(32),
        default="text",
        nullable=False,
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="sent",
        nullable=False,  # sent, delivered, read, failed, received
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="whatsapp_messages",
    )

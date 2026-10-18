import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.customer import Customer
    from app.models.profile import Profile


class WhatsAppAccount(Base, TimestampMixin):
    """WhatsApp Business Account (WABA) configuration per business tenant."""

    __tablename__ = "whatsapp_accounts"

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
    waba_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    app_id: Mapped[str] = mapped_column(
        String(128),
        default="wapiflow",
        nullable=False,
    )
    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="disconnected",
        nullable=False,  # connected, disconnected, error
    )
    webhook_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="whatsapp_account",
    )
    phone_numbers: Mapped[List["WhatsAppPhoneNumber"]] = relationship(
        "WhatsAppPhoneNumber",
        back_populates="account",
        cascade="all, delete-orphan",
    )


class WhatsAppPhoneNumber(Base, TimestampMixin):
    """Specific phone number configured under a WhatsApp Business Account."""

    __tablename__ = "whatsapp_phone_numbers"

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
    whatsapp_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("whatsapp_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    display_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    quality_rating: Mapped[Optional[str]] = mapped_column(
        String(32),
        default="UNKNOWN",
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    account: Mapped["WhatsAppAccount"] = relationship(
        "WhatsAppAccount",
        back_populates="phone_numbers",
    )


class Conversation(Base, TimestampMixin):
    """Chat thread between a business tenant and a customer."""

    __tablename__ = "conversations"

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
    whatsapp_phone_number_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("whatsapp_phone_numbers.id", ondelete="SET NULL"),
        nullable=True,
    )
    wa_conversation_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="open",
        nullable=False,  # open, resolved, snoozed
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        nullable=True,
    )
    unread_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_message_preview: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="conversations",
        lazy="joined",
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base, TimestampMixin):
    """WhatsApp message (inbound, outbound) or internal team note."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    wa_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )
    direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,  # inbound, outbound
    )
    message_type: Mapped[str] = mapped_column(
        String(32),
        default="text",
        nullable=False,  # text, image, audio, video, document, template, interactive, unknown
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    media_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    media_r2_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    media_mime_type: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,  # pending, sent, delivered, read, failed
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    sent_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        nullable=True,
    )
    is_internal_note: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )


class WebhookEvent(Base):
    """Raw incoming webhook payloads for auditing, replay, and idempotency."""

    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("businesses.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    wa_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    processing_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,  # pending, processing, processed, failed, duplicate
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


# Backward compatibility aliases
WhatsAppConnection = WhatsAppAccount
WhatsAppMessage = Message

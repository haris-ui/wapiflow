import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field
from app.schemas.common import BaseSchema


class WhatsAppPhoneNumberResponse(BaseSchema):
    """WhatsApp phone number details."""

    id: uuid.UUID
    phone_number: str
    display_name: Optional[str] = None
    quality_rating: Optional[str] = "UNKNOWN"
    status: str
    is_primary: bool
    created_at: datetime


class WhatsAppAccountConnect(BaseSchema):
    """Payload to connect or update a WhatsApp Business Account."""

    waba_id: str = Field(..., min_length=3, max_length=128, description="Meta WhatsApp Business Account ID")
    phone_number: str = Field(..., min_length=6, max_length=32, description="E.164 phone number, e.g. +15551234567")
    phone_number_id: Optional[str] = Field(None, max_length=128, description="Meta Phone Number ID (from WhatsApp Manager)")
    access_token: str = Field(..., min_length=10, description="System User permanent access token")
    display_name: Optional[str] = Field(None, max_length=128, description="Display name for WhatsApp account")


class WhatsAppAccountResponse(BaseSchema):
    """WhatsApp Account status for a business tenant."""

    id: uuid.UUID
    business_id: uuid.UUID
    waba_id: str
    app_id: str
    status: str  # connected, disconnected, error
    webhook_verified_at: Optional[datetime] = None
    phone_numbers: List[WhatsAppPhoneNumberResponse] = []
    created_at: datetime
    updated_at: datetime


class WhatsAppConfigInfo(BaseSchema):
    """Webhook connection and configuration details."""

    webhook_callback_url: str
    verify_token: str
    is_connected: bool
    account: Optional[WhatsAppAccountResponse] = None


class TestMessageRequest(BaseSchema):
    """Request to send a test WhatsApp message to verify connectivity."""

    recipient_phone: str = Field(..., min_length=6, max_length=32, description="Recipient phone number with country code")
    message: str = Field("Hello from WapiFlow! Your WhatsApp Business integration is working perfectly. 🚀", min_length=1, max_length=1024)

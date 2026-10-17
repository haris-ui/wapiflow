import uuid
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class RegisterRequest(BaseSchema):
    """Payload for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters password")
    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)


class LoginRequest(BaseSchema):
    """Payload for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    """JWT response after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: uuid.UUID
    email: EmailStr


class UserProfileResponse(BaseSchema):
    """User profile data returned to client."""

    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseSchema):
    """Updatable user profile fields."""

    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)
    avatar_url: Optional[str] = Field(None, max_length=1024)

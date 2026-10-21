import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class TeamMemberRoleUpdate(BaseSchema):
    """Payload to update a team member's role (Owner only)."""

    role: str = Field(
        ...,
        pattern="^(owner|manager|staff|agent|viewer)$",
        description="New role for the team member",
    )


class BusinessInviteCreate(BaseSchema):
    """Payload to invite a new team member to the business."""

    email: EmailStr
    role: str = Field(
        default="staff",
        pattern="^(manager|staff|agent|viewer)$",
        description="Role to assign once the invitation is accepted",
    )


class BusinessInviteResponse(BaseSchema):
    """Invitation record returned to the inviter."""

    id: uuid.UUID
    business_id: uuid.UUID
    email: str
    role: str
    status: str  # pending, accepted, expired, revoked
    expires_at: Optional[datetime] = None
    created_at: datetime


class BusinessInviteAccept(BaseSchema):
    """Payload to accept a pending invitation."""

    token: str


class AgentActivityLogResponse(BaseSchema):
    """Immutable agent activity log entry."""

    id: uuid.UUID
    business_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[uuid.UUID] = None
    created_at: datetime


class ConversationTypingSet(BaseSchema):
    """Payload to set or clear a user's typing state in a conversation."""

    is_typing: bool


class ConversationTypingResponse(BaseSchema):
    """Typing-indicator state for a user in a conversation."""

    conversation_id: uuid.UUID
    user_id: uuid.UUID
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    is_typing: bool
    updated_at: datetime


class PaginatedActivityLogResponse(BaseSchema):
    """Paginated envelope for agent activity logs."""

    items: List[AgentActivityLogResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
    has_next: bool

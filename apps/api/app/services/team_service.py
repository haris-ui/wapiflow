import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import TenantContext
from app.models.business import (
    AgentActivityLog,
    Business,
    BusinessInvitation,
    BusinessMember,
)
from app.models.profile import Profile
from app.models.whatsapp import Conversation, ConversationTyping
from app.schemas.common import PaginatedResponse
from app.schemas.team import (
    AgentActivityLogResponse,
    BusinessInviteAccept,
    BusinessInviteCreate,
    BusinessInviteResponse,
    ConversationTypingResponse,
    PaginatedActivityLogResponse,
    TeamMemberRoleUpdate,
)

INVITE_TTL_HOURS = 168  # 7 days


class TeamService:
    """Team membership, invitation, activity-log, and typing-indicator service."""

    # ------------------------------------------------------------------
    # Invitations
    # ------------------------------------------------------------------
    @staticmethod
    async def invite_member(
        db: AsyncSession,
        business_id: uuid.UUID,
        invited_by: uuid.UUID,
        invite_in: BusinessInviteCreate,
    ) -> BusinessInviteResponse:
        """Create a pending invitation scoped to the business."""
        email_clean = invite_in.email.lower().strip()

        # Prevent inviting someone who is already an active member
        stmt_mem = select(BusinessMember).where(
            BusinessMember.business_id == business_id,
            BusinessMember.user_id == select(Profile.id).where(
                Profile.email == email_clean
            ).scalar_subquery(),
            BusinessMember.is_active.is_(True),
        )
        if (await db.execute(stmt_mem)).scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already an active member of this business",
            )

        # Revoke any existing pending invitation for this email/business
        stmt_existing = select(BusinessInvitation).where(
            BusinessInvitation.business_id == business_id,
            BusinessInvitation.email == email_clean,
            BusinessInvitation.accepted_at.is_(None),
        )
        existing = (await db.execute(stmt_existing)).scalars().first()
        if existing:
            existing.expires_at = datetime.now(timezone.utc)
            db.add(existing)

        token = uuid.uuid4().hex
        invitation = BusinessInvitation(
            id=uuid.uuid4(),
            business_id=business_id,
            email=email_clean,
            role=invite_in.role,
            token=token,
            invited_by=invited_by,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=INVITE_TTL_HOURS),
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)

        return BusinessInviteResponse(
            id=invitation.id,
            business_id=invitation.business_id,
            email=invitation.email,
            role=invitation.role,
            status="pending",
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
        )

    @staticmethod
    async def accept_invite(
        db: AsyncSession,
        user_id: uuid.UUID,
        business_id: uuid.UUID,
        token: str,
    ) -> BusinessInviteResponse:
        """Accept a pending invitation and create the membership."""
        stmt = select(BusinessInvitation).where(
            BusinessInvitation.token == token,
            BusinessInvitation.business_id == business_id,
            BusinessInvitation.accepted_at.is_(None),
        )
        invitation = (await db.execute(stmt)).scalars().first()
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found or already accepted",
            )

        now = datetime.now(timezone.utc)
        if invitation.expires_at and invitation.expires_at.replace(tzinfo=None) < now.replace(
            tzinfo=None
        ):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invitation has expired",
            )

        stmt_mem = select(BusinessMember).where(
            BusinessMember.business_id == business_id,
            BusinessMember.user_id == user_id,
        )
        member = (await db.execute(stmt_mem)).scalars().first()
        if not member:
            member = BusinessMember(
                id=uuid.uuid4(),
                business_id=business_id,
                user_id=user_id,
                role=invitation.role,
                is_active=True,
            )
            db.add(member)
        else:
            member.is_active = True
            member.role = invitation.role

        invitation.accepted_at = now
        await db.commit()
        await db.refresh(member)

        return BusinessInviteResponse(
            id=invitation.id,
            business_id=invitation.business_id,
            email=invitation.email,
            role=invitation.role,
            status="accepted",
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
        )

    @staticmethod
    async def list_invites(
        db: AsyncSession, business_id: uuid.UUID
    ) -> List[BusinessInviteResponse]:
        """List invitations for a business."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(BusinessInvitation)
            .where(BusinessInvitation.business_id == business_id)
            .order_by(BusinessInvitation.created_at.desc())
        )
        result = await db.execute(stmt)
        invites = result.scalars().all()

        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        return [
            BusinessInviteResponse(
                id=inv.id,
                business_id=inv.business_id,
                email=inv.email,
                role=inv.role,
                status=(
                    "accepted"
                    if inv.accepted_at
                    else (
                        "expired"
                        if inv.expires_at
                        and inv.expires_at.replace(tzinfo=None) < now_naive
                        else "pending"
                    )
                ),
                expires_at=inv.expires_at,
                created_at=inv.created_at,
            )
            for inv in invites
        ]

    @staticmethod
    async def revoke_invite(
        db: AsyncSession, business_id: uuid.UUID, invite_id: uuid.UUID
    ) -> dict:
        """Revoke/delete a pending invitation."""
        stmt = select(BusinessInvitation).where(
            BusinessInvitation.id == invite_id,
            BusinessInvitation.business_id == business_id,
            BusinessInvitation.accepted_at.is_(None),
        )
        invitation = (await db.execute(stmt)).scalars().first()
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending invitation not found",
            )
        await db.delete(invitation)
        await db.commit()
        return {"status": "ok", "message": "Invitation revoked"}

    # ------------------------------------------------------------------
    # Member roles
    # ------------------------------------------------------------------
    @staticmethod
    async def update_member_role(
        db: AsyncSession,
        business_id: uuid.UUID,
        member_id: uuid.UUID,
        role: str,
        changed_by: uuid.UUID,
    ) -> dict:
        """Update a team member's role (owner cannot demote themselves)."""
        stmt = select(BusinessMember).where(
            BusinessMember.id == member_id,
            BusinessMember.business_id == business_id,
            BusinessMember.is_active.is_(True),
        )
        member = (await db.execute(stmt)).scalars().first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found",
            )

        if member.user_id == changed_by and role != "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner cannot demote themselves",
            )

        if member.role == "owner" and role != "owner":
            owner_count = (
                await db.execute(
                    select(func.count()).select_from(BusinessMember).where(
                        BusinessMember.business_id == business_id,
                        BusinessMember.role == "owner",
                        BusinessMember.is_active.is_(True),
                    )
                )
            ).scalar()
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one owner must remain",
                )

        member.role = role
        await db.commit()
        await db.refresh(member)

        return {
            "status": "ok",
            "message": f"Member role updated to {role}",
            "member_id": str(member.id),
            "role": member.role,
        }

    # ------------------------------------------------------------------
    # Activity log
    # ------------------------------------------------------------------
    @staticmethod
    async def log_activity(
        db: AsyncSession,
        business_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Append an immutable activity-log entry."""
        entry = AgentActivityLog(
            id=uuid.uuid4(),
            business_id=business_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        db.add(entry)
        await db.flush()

    @staticmethod
    async def list_activity_logs(
        db: AsyncSession,
        business_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedActivityLogResponse:
        """List paginated agent activity logs for a business."""
        query = select(AgentActivityLog).where(
            AgentActivityLog.business_id == business_id
        )
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            query.order_by(AgentActivityLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        items = [
            AgentActivityLogResponse(
                id=log.id,
                business_id=log.business_id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                created_at=log.created_at,
            )
            for log in logs
        ]
        return PaginatedActivityLogResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
        )

    # ------------------------------------------------------------------
    # Typing indicators
    # ------------------------------------------------------------------
    @staticmethod
    async def set_typing(
        db: AsyncSession,
        tenant: TenantContext,
        conversation_id: uuid.UUID,
        is_typing: bool,
    ) -> ConversationTypingResponse:
        """Set or clear typing state for the current user in a conversation."""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.business_id == tenant.business_id,
        )
        conversation = (await db.execute(stmt)).scalars().first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        stmt_row = select(ConversationTyping).where(
            ConversationTyping.business_id == tenant.business_id,
            ConversationTyping.conversation_id == conversation_id,
            ConversationTyping.user_id == tenant.user_id,
        )
        row = (await db.execute(stmt_row)).scalars().first()
        now = datetime.now(timezone.utc)
        if not row:
            row = ConversationTyping(
                id=uuid.uuid4(),
                business_id=tenant.business_id,
                conversation_id=conversation_id,
                user_id=tenant.user_id,
                is_typing=is_typing,
                updated_at=now,
            )
            db.add(row)
        else:
            row.is_typing = is_typing
            row.updated_at = now
        await db.commit()
        await db.refresh(row)

        action = "typing_start" if is_typing else "typing_stop"
        await TeamService.log_activity(
            db,
            tenant.business_id,
            tenant.user_id,
            action,
            resource_type="conversation",
            resource_id=conversation_id,
        )

        return ConversationTypingResponse(
            conversation_id=row.conversation_id,
            user_id=row.user_id,
            user_email=None,
            user_full_name=None,
            is_typing=row.is_typing,
            updated_at=row.updated_at,
        )

    @staticmethod
    async def get_typing(
        db: AsyncSession,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> List[ConversationTypingResponse]:
        """Return users currently typing in a conversation (within last 30s)."""
        window = datetime.now(timezone.utc) - timedelta(seconds=30)
        stmt = (
            select(ConversationTyping, Profile.email, Profile.full_name)
            .join(Profile, ConversationTyping.user_id == Profile.id)
            .where(
                ConversationTyping.business_id == business_id,
                ConversationTyping.conversation_id == conversation_id,
                ConversationTyping.is_typing.is_(True),
                ConversationTyping.updated_at >= window,
            )
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [
            ConversationTypingResponse(
                conversation_id=t.conversation_id,
                user_id=t.user_id,
                user_email=email,
                user_full_name=full_name,
                is_typing=t.is_typing,
                updated_at=t.updated_at,
            )
            for t, email, full_name in rows
        ]




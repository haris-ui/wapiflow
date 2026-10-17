import re
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.business import Business, BusinessMember, BusinessSettings, Subscription
from app.models.profile import Profile
from app.schemas.business import (
    BusinessCreate,
    BusinessListItem,
    BusinessMemberInvite,
    BusinessMemberResponse,
    BusinessResponse,
    BusinessSettingsResponse,
    BusinessSettingsUpdate,
    BusinessUpdate,
    SubscriptionResponse,
)


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from business name."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = s.strip("-")
    return s or "business"


class BusinessService:
    """Business tenant management service."""

    @staticmethod
    async def create_business(
        db: AsyncSession,
        user_id: uuid.UUID,
        business_in: BusinessCreate,
    ) -> BusinessResponse:
        """
        Creates a new business tenant and initializes:
        1. Business record
        2. Creator as 'owner' BusinessMember
        3. Default BusinessSettings
        4. Default Free Subscription
        """
        # Ensure user profile exists in database
        stmt_prof = select(Profile).where(Profile.id == user_id)
        prof_res = await db.execute(stmt_prof)
        user_profile = prof_res.scalars().first()
        if not user_profile:
            user_profile = Profile(
                id=user_id,
                email=f"user_{user_id.hex[:8]}@wapiflow.internal",
                is_active=True,
            )
            db.add(user_profile)
            await db.flush()

        # Generate unique slug
        base_slug = business_in.slug or generate_slug(business_in.name)
        slug = base_slug
        counter = 1
        while True:
            stmt = select(Business).where(Business.slug == slug)
            res = await db.execute(stmt)
            if not res.scalars().first():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        business = Business(
            id=uuid.uuid4(),
            name=business_in.name,
            slug=slug,
            phone_number=business_in.phone_number,
            currency=business_in.currency.upper(),
            timezone=business_in.timezone,
            is_active=True,
        )
        db.add(business)
        await db.flush()

        # 2. Add creator as 'owner'
        membership = BusinessMember(
            id=uuid.uuid4(),
            business_id=business.id,
            user_id=user_id,
            role="owner",
            is_active=True,
        )
        db.add(membership)

        # 3. Create default business settings
        settings = BusinessSettings(
            id=uuid.uuid4(),
            business_id=business.id,
            auto_decrement_stock=True,
            order_prefix="WF-",
        )
        db.add(settings)

        # 4. Create default subscription
        subscription = Subscription(
            id=uuid.uuid4(),
            business_id=business.id,
            plan_tier="free",
            status="active",
        )
        db.add(subscription)

        await db.commit()
        await db.refresh(business)

        return BusinessResponse(
            id=business.id,
            name=business.name,
            slug=business.slug,
            phone_number=business.phone_number,
            currency=business.currency,
            timezone=business.timezone,
            logo_url=business.logo_url,
            is_active=business.is_active,
            role="owner",
            settings=BusinessSettingsResponse.model_validate(settings),
            subscription=SubscriptionResponse.model_validate(subscription),
            created_at=business.created_at,
            updated_at=business.updated_at,
        )

    @staticmethod
    async def list_user_businesses(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[BusinessListItem]:
        """List all active businesses that the user belongs to."""
        stmt = (
            select(Business, BusinessMember.role)
            .join(BusinessMember, Business.id == BusinessMember.business_id)
            .where(
                BusinessMember.user_id == user_id,
                BusinessMember.is_active.is_(True),
                Business.is_active.is_(True),
            )
            .order_by(Business.created_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [
            BusinessListItem(
                id=b.id,
                name=b.name,
                slug=b.slug,
                currency=b.currency,
                role=role,
                is_active=b.is_active,
                created_at=b.created_at,
            )
            for b, role in rows
        ]

    @staticmethod
    async def get_business_detail(
        db: AsyncSession,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> BusinessResponse:
        """Get full business details including settings and subscription."""
        stmt = (
            select(Business, BusinessMember.role)
            .join(BusinessMember, Business.id == BusinessMember.business_id)
            .options(
                selectinload(Business.settings),
                selectinload(Business.subscription),
            )
            .where(
                Business.id == business_id,
                BusinessMember.user_id == user_id,
                BusinessMember.is_active.is_(True),
            )
        )
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied",
            )

        business, role = row
        return BusinessResponse(
            id=business.id,
            name=business.name,
            slug=business.slug,
            phone_number=business.phone_number,
            currency=business.currency,
            timezone=business.timezone,
            logo_url=business.logo_url,
            is_active=business.is_active,
            role=role,
            settings=BusinessSettingsResponse.model_validate(business.settings) if business.settings else None,
            subscription=SubscriptionResponse.model_validate(business.subscription) if business.subscription else None,
            created_at=business.created_at,
            updated_at=business.updated_at,
        )

    @staticmethod
    async def update_business(
        db: AsyncSession,
        business_id: uuid.UUID,
        business_in: BusinessUpdate,
    ) -> BusinessResponse:
        """Update business profile details (Owner/Manager only)."""
        stmt = (
            select(Business)
            .options(
                selectinload(Business.settings),
                selectinload(Business.subscription),
            )
            .where(Business.id == business_id)
        )
        result = await db.execute(stmt)
        business = result.scalars().first()

        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found",
            )

        if business_in.name is not None:
            business.name = business_in.name
        if business_in.phone_number is not None:
            business.phone_number = business_in.phone_number
        if business_in.currency is not None:
            business.currency = business_in.currency.upper()
        if business_in.timezone is not None:
            business.timezone = business_in.timezone
        if business_in.logo_url is not None:
            business.logo_url = business_in.logo_url

        await db.commit()
        await db.refresh(business)

        return BusinessResponse(
            id=business.id,
            name=business.name,
            slug=business.slug,
            phone_number=business.phone_number,
            currency=business.currency,
            timezone=business.timezone,
            logo_url=business.logo_url,
            is_active=business.is_active,
            settings=BusinessSettingsResponse.model_validate(business.settings) if business.settings else None,
            subscription=SubscriptionResponse.model_validate(business.subscription) if business.subscription else None,
            created_at=business.created_at,
            updated_at=business.updated_at,
        )

    @staticmethod
    async def list_members(
        db: AsyncSession,
        business_id: uuid.UUID,
    ) -> List[BusinessMemberResponse]:
        """List all team members of the business."""
        stmt = (
            select(BusinessMember, Profile.email, Profile.full_name)
            .join(Profile, BusinessMember.user_id == Profile.id)
            .where(
                BusinessMember.business_id == business_id,
                BusinessMember.is_active.is_(True),
            )
            .order_by(BusinessMember.created_at.asc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [
            BusinessMemberResponse(
                id=m.id,
                business_id=m.business_id,
                user_id=m.user_id,
                email=email,
                full_name=full_name,
                role=m.role,
                is_active=m.is_active,
                created_at=m.created_at,
            )
            for m, email, full_name in rows
        ]

    @staticmethod
    async def invite_member(
        db: AsyncSession,
        business_id: uuid.UUID,
        invite_in: BusinessMemberInvite,
    ) -> BusinessMemberResponse:
        """Invite an existing user or newly registered email as business team member."""
        email_clean = invite_in.email.lower().strip()

        # Find or create invited profile
        stmt = select(Profile).where(Profile.email == email_clean)
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if not profile:
            profile = Profile(
                id=uuid.uuid4(),
                email=email_clean,
                is_active=True,
            )
            db.add(profile)
            await db.flush()

        # Check existing membership
        stmt_mem = select(BusinessMember).where(
            BusinessMember.business_id == business_id,
            BusinessMember.user_id == profile.id,
        )
        res_mem = await db.execute(stmt_mem)
        existing_mem = res_mem.scalars().first()

        if existing_mem:
            if existing_mem.is_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This user is already an active member of this business",
                )
            existing_mem.is_active = True
            existing_mem.role = invite_in.role
            membership = existing_mem
        else:
            membership = BusinessMember(
                id=uuid.uuid4(),
                business_id=business_id,
                user_id=profile.id,
                role=invite_in.role,
                is_active=True,
            )
            db.add(membership)

        await db.commit()
        await db.refresh(membership)

        return BusinessMemberResponse(
            id=membership.id,
            business_id=membership.business_id,
            user_id=membership.user_id,
            email=profile.email,
            full_name=profile.full_name,
            role=membership.role,
            is_active=membership.is_active,
            created_at=membership.created_at,
        )

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.profile import Profile
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
    UserUpdateRequest,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def create_jwt_token(user_id: uuid.UUID, email: str) -> str:
    """Create a signed JWT token for the user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


class AuthService:
    """Authentication and profile management service."""

    @staticmethod
    async def get_or_create_profile(
        db: AsyncSession,
        user_id: uuid.UUID,
        email: str,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Profile:
        """Find an existing profile or create a new profile for the authenticated user."""
        stmt = select(Profile).where(Profile.id == user_id)
        result = await db.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            profile = Profile(
                id=user_id,
                email=email.lower().strip(),
                full_name=full_name,
                phone_number=phone_number,
                is_active=True,
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        return profile

    @staticmethod
    async def register(db: AsyncSession, register_data: RegisterRequest) -> TokenResponse:
        """Register a new user and return an authentication token."""
        email_clean = register_data.email.lower().strip()

        # Check existing profile
        stmt = select(Profile).where(Profile.email == email_clean)
        result = await db.execute(stmt)
        existing_profile = result.scalars().first()

        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists",
            )

        new_user_id = uuid.uuid4()
        profile = Profile(
            id=new_user_id,
            email=email_clean,
            full_name=register_data.full_name,
            phone_number=register_data.phone_number,
            is_active=True,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        access_token = create_jwt_token(user_id=profile.id, email=profile.email)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=profile.id,
            email=profile.email,
        )

    @staticmethod
    async def login(db: AsyncSession, login_data: LoginRequest) -> TokenResponse:
        """Authenticate user and issue JWT."""
        email_clean = login_data.email.lower().strip()

        stmt = select(Profile).where(Profile.email == email_clean)
        result = await db.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            # Create user on first login if delegated to external auth
            new_id = uuid.uuid4()
            profile = Profile(
                id=new_id,
                email=email_clean,
                is_active=True,
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        if not profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )

        access_token = create_jwt_token(user_id=profile.id, email=profile.email)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=profile.id,
            email=profile.email,
        )

    @staticmethod
    async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfileResponse:
        """Fetch profile for the current user."""
        stmt = select(Profile).where(Profile.id == user_id)
        result = await db.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        return UserProfileResponse.model_validate(profile)

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        user_id: uuid.UUID,
        update_data: UserUpdateRequest,
    ) -> UserProfileResponse:
        """Update current user profile information."""
        stmt = select(Profile).where(Profile.id == user_id)
        result = await db.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        if update_data.full_name is not None:
            profile.full_name = update_data.full_name
        if update_data.phone_number is not None:
            profile.phone_number = update_data.phone_number
        if update_data.avatar_url is not None:
            profile.avatar_url = update_data.avatar_url

        await db.commit()
        await db.refresh(profile)
        return UserProfileResponse.model_validate(profile)

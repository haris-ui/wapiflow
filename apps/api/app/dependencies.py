import uuid
from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, Path, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.tenant import decode_jwt_token
from app.models.business import BusinessMember
from app.models.profile import Profile

# HTTP Bearer scheme
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Authenticated user representation extracted from validated JWT."""

    def __init__(self, user_id: uuid.UUID, email: str, raw_payload: Optional[dict] = None):
        self.id = user_id
        self.email = email
        self.raw_payload = raw_payload or {}

    def __repr__(self) -> str:
        return f"<CurrentUser id={self.id} email={self.email}>"


class TenantContext:
    """
    Resolved multi-tenant context verified against the database.
    Ensures that the current user is an active member of the business specified in the path.
    """

    def __init__(self, user_id: uuid.UUID, business_id: uuid.UUID, role: str):
        self.user_id = user_id
        self.business_id = business_id
        self.role = role

    def is_owner(self) -> bool:
        return self.role == "owner"

    def is_manager_or_higher(self) -> bool:
        return self.role in ("owner", "manager")

    def __repr__(self) -> str:
        return f"<TenantContext user={self.user_id} business={self.business_id} role={self.role}>"


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Verifies Supabase / application JWT token from Authorization header.
    Returns CurrentUser instance if valid, otherwise raises 401 Unauthorized.
    """
    token = credentials.credentials if credentials else None

    # Check request.state.user if populated by tenant middleware
    if getattr(request.state, "user", None):
        u = request.state.user
        return CurrentUser(user_id=u["id"], email=u["email"], raw_payload=u.get("raw_payload"))

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = decode_jwt_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=user_info["id"],
        email=user_info["email"],
        raw_payload=user_info.get("raw_payload"),
    )


async def get_tenant_context(
    business_id: uuid.UUID = Path(..., description="Business tenant UUID identifier"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """
    Verifies that the authenticated user is an active member of the specified business.
    Guarantees strict tenant isolation across all multi-tenant endpoints.
    Never trust business_id from request body; always use path parameter verified here.
    """
    stmt = (
        select(BusinessMember)
        .where(
            BusinessMember.business_id == business_id,
            BusinessMember.user_id == current_user.id,
            BusinessMember.is_active.is_(True),
        )
    )
    result = await db.execute(stmt)
    membership = result.scalars().first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Not an active member of this business",
        )

    return TenantContext(
        user_id=current_user.id,
        business_id=business_id,
        role=membership.role,
    )


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Dependency factory to enforce role-based access control inside a tenant.
    """
    async def role_checker(
        tenant: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if tenant.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}",
            )
        return tenant

    return role_checker

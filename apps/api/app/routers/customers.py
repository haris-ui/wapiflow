import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import TenantContext, get_tenant_context
from app.schemas.common import PaginatedResponse
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetailResponse,
    CustomerListItem,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/businesses/{business_id}/customers", tags=["Customers"])


@router.get(
    "",
    response_model=PaginatedResponse[CustomerListItem],
    status_code=status.HTTP_200_OK,
    summary="List customers with pagination and search",
)
async def list_customers(
    business_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CustomerListItem]:
    """Retrieve paginated customer list for the business tenant."""
    return await CustomerService.get_customers(
        db=db,
        tenant=tenant,
        page=page,
        page_size=page_size,
        search=search,
    )


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
)
async def create_customer(
    customer_in: CustomerCreate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Create a new customer record isolated within the tenant workspace."""
    return await CustomerService.create_customer(db, tenant, customer_in)


@router.get(
    "/{customer_id}",
    response_model=CustomerDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer detail with recent orders",
)
async def get_customer(
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> CustomerDetailResponse:
    """Retrieve customer details along with summary of recent orders."""
    return await CustomerService.get_customer_detail(db, tenant, customer_id)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update customer details",
)
async def update_customer(
    customer_in: CustomerUpdate,
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Update contact information and delivery address for a customer."""
    return await CustomerService.update_customer(db, tenant, customer_id, customer_in)

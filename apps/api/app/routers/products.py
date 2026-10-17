import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import TenantContext, get_tenant_context, require_role
from app.schemas.common import PaginatedResponse
from app.schemas.product import (
    ProductCreate,
    ProductListItem,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/businesses/{business_id}/products", tags=["Products"])


@router.get(
    "",
    response_model=PaginatedResponse[ProductListItem],
    status_code=status.HTTP_200_OK,
    summary="List products with pagination and filters",
)
async def list_products(
    business_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_archived: Optional[bool] = Query(default=False),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProductListItem]:
    """Retrieve paginated catalog products filtered by state and search criteria."""
    return await ProductService.get_products(
        db=db,
        tenant=tenant,
        page=page,
        page_size=page_size,
        is_archived=is_archived,
        is_active=is_active,
        search=search,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new catalog product",
)
async def create_product(
    product_in: ProductCreate,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Create a new product scoped to the business tenant."""
    return await ProductService.create_product(db, tenant, product_in)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product detail",
)
async def get_product(
    product_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Retrieve single product detail."""
    return await ProductService.get_product(db, tenant, product_id)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update product details",
)
async def update_product(
    product_in: ProductUpdate,
    product_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update product fields ensuring SKU uniqueness and tenant boundary."""
    return await ProductService.update_product(db, tenant, product_id, product_in)


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive product",
)
async def archive_product(
    product_id: uuid.UUID,
    business_id: uuid.UUID,
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Safely archive a product, preserving integrity of existing orders."""
    return await ProductService.archive_product(db, tenant, product_id)

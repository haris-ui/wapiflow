import math
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import TenantContext
from app.models.order import OrderItem
from app.models.product import Product
from app.schemas.common import PaginatedResponse
from app.schemas.product import (
    ProductCreate,
    ProductListItem,
    ProductResponse,
    ProductUpdate,
)


class ProductService:
    """Product catalog and inventory service enforcing tenant boundaries."""

    @staticmethod
    async def get_products(
        db: AsyncSession,
        tenant: TenantContext,
        page: int = 1,
        page_size: int = 20,
        is_archived: Optional[bool] = False,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[ProductListItem]:
        """List products with pagination, search, and status filters."""
        query = select(Product).where(Product.business_id == tenant.business_id)

        if is_archived is not None:
            query = query.where(Product.is_archived == is_archived)

        if is_active is not None:
            query = query.where(Product.is_active == is_active)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.sku.ilike(search_pattern),
                )
            )

        # Count total items
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginate results
        offset = (page - 1) * page_size
        stmt = query.order_by(Product.created_at.desc()).offset(offset).limit(page_size)
        result = await db.execute(stmt)
        products = result.scalars().all()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        has_next = page < total_pages

        items = [
            ProductListItem(
                id=p.id,
                name=p.name,
                sku=p.sku,
                price=p.price,
                stock_quantity=p.stock_quantity,
                track_inventory=p.track_inventory,
                is_active=p.is_active,
                is_archived=p.is_archived,
                image_url=p.image_url,
            )
            for p in products
        ]

        return PaginatedResponse[ProductListItem](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
        )

    @staticmethod
    async def create_product(
        db: AsyncSession,
        tenant: TenantContext,
        product_in: ProductCreate,
    ) -> ProductResponse:
        """Create a new product scoped to the business."""
        sku_clean = product_in.sku.strip()

        # Check SKU uniqueness per business
        stmt = select(Product).where(
            Product.business_id == tenant.business_id,
            Product.sku == sku_clean,
        )
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with SKU '{sku_clean}' already exists in this business",
            )

        product = Product(
            id=uuid.uuid4(),
            business_id=tenant.business_id,
            name=product_in.name.strip(),
            sku=sku_clean,
            description=product_in.description,
            price=product_in.price,
            compare_at_price=product_in.compare_at_price,
            cost_price=product_in.cost_price,
            stock_quantity=product_in.stock_quantity,
            track_inventory=product_in.track_inventory,
            image_url=product_in.image_url,
            is_active=product_in.is_active,
            is_archived=False,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)

        return ProductResponse.model_validate(product)

    @staticmethod
    async def get_product(
        db: AsyncSession,
        tenant: TenantContext,
        product_id: uuid.UUID,
    ) -> ProductResponse:
        """Retrieve single product by ID ensuring tenant boundaries."""
        stmt = select(Product).where(
            Product.id == product_id,
            Product.business_id == tenant.business_id,
        )
        product = (await db.execute(stmt)).scalars().first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        return ProductResponse.model_validate(product)

    @staticmethod
    async def update_product(
        db: AsyncSession,
        tenant: TenantContext,
        product_id: uuid.UUID,
        product_in: ProductUpdate,
    ) -> ProductResponse:
        """Update product attributes with tenant verification."""
        stmt = select(Product).where(
            Product.id == product_id,
            Product.business_id == tenant.business_id,
        )
        product = (await db.execute(stmt)).scalars().first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        if product_in.sku is not None:
            sku_clean = product_in.sku.strip()
            if sku_clean != product.sku:
                # Check SKU uniqueness
                stmt_sku = select(Product).where(
                    Product.business_id == tenant.business_id,
                    Product.sku == sku_clean,
                    Product.id != product_id,
                )
                if (await db.execute(stmt_sku)).scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"A product with SKU '{sku_clean}' already exists in this business",
                    )
                product.sku = sku_clean

        if product_in.name is not None:
            product.name = product_in.name.strip()
        if product_in.description is not None:
            product.description = product_in.description
        if product_in.price is not None:
            product.price = product_in.price
        if product_in.compare_at_price is not None:
            product.compare_at_price = product_in.compare_at_price
        if product_in.cost_price is not None:
            product.cost_price = product_in.cost_price
        if product_in.stock_quantity is not None:
            product.stock_quantity = product_in.stock_quantity
        if product_in.track_inventory is not None:
            product.track_inventory = product_in.track_inventory
        if product_in.image_url is not None:
            product.image_url = product_in.image_url
        if product_in.is_active is not None:
            product.is_active = product_in.is_active

        await db.commit()
        await db.refresh(product)
        return ProductResponse.model_validate(product)

    @staticmethod
    async def archive_product(
        db: AsyncSession,
        tenant: TenantContext,
        product_id: uuid.UUID,
    ) -> ProductResponse:
        """
        Archive a product. Never hard-deletes if order items exist referencing it;
        sets is_archived=True and is_active=False.
        """
        stmt = select(Product).where(
            Product.id == product_id,
            Product.business_id == tenant.business_id,
        )
        product = (await db.execute(stmt)).scalars().first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        # Check if product is referenced in any order_items
        order_stmt = select(func.count()).select_from(OrderItem).where(OrderItem.product_id == product_id)
        order_count = (await db.execute(order_stmt)).scalar() or 0

        # Always soft archive to protect transactional history
        product.is_archived = True
        product.is_active = False

        await db.commit()
        await db.refresh(product)
        return ProductResponse.model_validate(product)

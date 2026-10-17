import math
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import TenantContext
from app.models.customer import Customer
from app.models.order import Order
from app.schemas.common import PaginatedResponse
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetailResponse,
    CustomerListItem,
    CustomerResponse,
    CustomerUpdate,
)


class CustomerService:
    """Customer management service with strict tenant isolation."""

    @staticmethod
    async def get_customers(
        db: AsyncSession,
        tenant: TenantContext,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> PaginatedResponse[CustomerListItem]:
        """List customers scoped to the business."""
        query = select(Customer).where(Customer.business_id == tenant.business_id)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Customer.name.ilike(search_pattern),
                    Customer.phone_number.ilike(search_pattern),
                    Customer.email.ilike(search_pattern),
                )
            )

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        offset = (page - 1) * page_size
        stmt = query.order_by(Customer.created_at.desc()).offset(offset).limit(page_size)
        result = await db.execute(stmt)
        customers = result.scalars().all()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        has_next = page < total_pages

        items = [
            CustomerListItem(
                id=c.id,
                name=c.name,
                phone_number=c.phone_number,
                email=c.email,
                total_orders=c.total_orders,
                total_spend=c.total_spend,
                created_at=c.created_at,
            )
            for c in customers
        ]

        return PaginatedResponse[CustomerListItem](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
        )

    @staticmethod
    async def create_customer(
        db: AsyncSession,
        tenant: TenantContext,
        customer_in: CustomerCreate,
    ) -> CustomerResponse:
        """Create a new customer for the business."""
        phone_clean = customer_in.phone_number.strip()

        # Check unique phone number per business
        stmt = select(Customer).where(
            Customer.business_id == tenant.business_id,
            Customer.phone_number == phone_clean,
        )
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Customer with phone number '{phone_clean}' already exists in this business",
            )

        customer = Customer(
            id=uuid.uuid4(),
            business_id=tenant.business_id,
            name=customer_in.name.strip(),
            phone_number=phone_clean,
            email=customer_in.email,
            delivery_address=customer_in.delivery_address,
            notes=customer_in.notes,
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return CustomerResponse.model_validate(customer)

    @staticmethod
    async def get_customer_detail(
        db: AsyncSession,
        tenant: TenantContext,
        customer_id: uuid.UUID,
    ) -> CustomerDetailResponse:
        """Fetch single customer detail with recent order history summary."""
        stmt = (
            select(Customer)
            .options(selectinload(Customer.orders))
            .where(
                Customer.id == customer_id,
                Customer.business_id == tenant.business_id,
            )
        )
        customer = (await db.execute(stmt)).scalars().first()

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )

        # Get recent 5 orders
        orders_stmt = (
            select(Order)
            .where(
                Order.customer_id == customer_id,
                Order.business_id == tenant.business_id,
            )
            .order_by(Order.created_at.desc())
            .limit(5)
        )
        recent_orders = (await db.execute(orders_stmt)).scalars().all()

        recent_orders_data = [
            {
                "id": str(o.id),
                "order_number": o.order_number,
                "status": o.status,
                "total_amount": float(o.total_amount),
                "created_at": o.created_at.isoformat(),
            }
            for o in recent_orders
        ]

        return CustomerDetailResponse(
            id=customer.id,
            business_id=customer.business_id,
            name=customer.name,
            phone_number=customer.phone_number,
            email=customer.email,
            delivery_address=customer.delivery_address,
            notes=customer.notes,
            total_orders=customer.total_orders,
            total_spend=customer.total_spend,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            recent_orders=recent_orders_data,
        )

    @staticmethod
    async def update_customer(
        db: AsyncSession,
        tenant: TenantContext,
        customer_id: uuid.UUID,
        customer_in: CustomerUpdate,
    ) -> CustomerResponse:
        """Update customer details."""
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == tenant.business_id,
        )
        customer = (await db.execute(stmt)).scalars().first()

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )

        if customer_in.phone_number is not None:
            phone_clean = customer_in.phone_number.strip()
            if phone_clean != customer.phone_number:
                stmt_phone = select(Customer).where(
                    Customer.business_id == tenant.business_id,
                    Customer.phone_number == phone_clean,
                    Customer.id != customer_id,
                )
                if (await db.execute(stmt_phone)).scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Customer with phone number '{phone_clean}' already exists",
                    )
                customer.phone_number = phone_clean

        if customer_in.name is not None:
            customer.name = customer_in.name.strip()
        if customer_in.email is not None:
            customer.email = customer_in.email
        if customer_in.delivery_address is not None:
            customer.delivery_address = customer_in.delivery_address
        if customer_in.notes is not None:
            customer.notes = customer_in.notes

        await db.commit()
        await db.refresh(customer)
        return CustomerResponse.model_validate(customer)

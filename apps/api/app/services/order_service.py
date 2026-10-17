import math
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import TenantContext
from app.models.business import BusinessSettings
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.product import InventoryMovement, Product
from app.schemas.common import PaginatedResponse
from app.schemas.customer import CustomerResponse
from app.schemas.order import (
    VALID_STATUS_TRANSITIONS,
    OrderCreate,
    OrderItemResponse,
    OrderListItem,
    OrderResponse,
    OrderStatusHistoryResponse,
    OrderUpdate,
)


class OrderService:
    """Transactional order management service strictly isolated per business tenant."""

    @staticmethod
    async def create_order(
        db: AsyncSession,
        tenant: TenantContext,
        order_in: OrderCreate,
    ) -> OrderResponse:
        """
        Creates an order transactionally:
        1. Validates all products belong to business (tenant isolation)
        2. Snapshots product name + price
        3. Calculates totals on server (ignoring client calculations)
        4. Checks idempotency_key uniqueness per business
        5. Creates order + line items in transaction
        6. Decrements stock (if auto_decrement_stock configured)
        7. Records inventory movements
        8. Creates initial order_status_history entry
        9. Updates customer total_orders and total_spend
        10. Returns complete order with items and history
        """
        # 1. Idempotency Key check
        if order_in.idempotency_key:
            stmt_idem = select(Order).where(
                Order.business_id == tenant.business_id,
                Order.idempotency_key == order_in.idempotency_key,
            )
            existing_idem = (await db.execute(stmt_idem)).scalars().first()
            if existing_idem:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An order with this idempotency key already exists for this business",
                )

        # 2. Validate all products belong to the tenant's business
        product_ids = [item.product_id for item in order_in.items]
        stmt_products = select(Product).where(
            Product.id.in_(product_ids),
            Product.business_id == tenant.business_id,
        )
        products_res = await db.execute(stmt_products)
        products = products_res.scalars().all()
        product_map: Dict[uuid.UUID, Product] = {p.id: p for p in products}

        # Check if any product was not found or belongs to another tenant
        missing_or_foreign = [pid for pid in product_ids if pid not in product_map]
        if missing_or_foreign:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Products not found or belong to another business: {[str(pid) for pid in missing_or_foreign]}",
            )

        # 3. Resolve Customer (by ID or inline phone/name)
        customer: Optional[Customer] = None
        if order_in.customer_id:
            stmt_cust = select(Customer).where(
                Customer.id == order_in.customer_id,
                Customer.business_id == tenant.business_id,
            )
            customer = (await db.execute(stmt_cust)).scalars().first()
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found in this business",
                )
        elif order_in.customer_phone and order_in.customer_name:
            phone_clean = order_in.customer_phone.strip()
            stmt_cust = select(Customer).where(
                Customer.business_id == tenant.business_id,
                Customer.phone_number == phone_clean,
            )
            customer = (await db.execute(stmt_cust)).scalars().first()
            if not customer:
                customer = Customer(
                    id=uuid.uuid4(),
                    business_id=tenant.business_id,
                    name=order_in.customer_name.strip(),
                    phone_number=phone_clean,
                    delivery_address=order_in.fulfillment_address,
                )
                db.add(customer)
                await db.flush()

        # 4. Fetch business settings
        stmt_settings = select(BusinessSettings).where(
            BusinessSettings.business_id == tenant.business_id
        )
        settings_res = await db.execute(stmt_settings)
        b_settings = settings_res.scalars().first()
        order_prefix = b_settings.order_prefix if b_settings else "WF-"
        auto_decrement = b_settings.auto_decrement_stock if b_settings else True

        # Generate unique order number
        order_number = f"{order_prefix}{int(time.time())}-{uuid.uuid4().hex[:4].upper()}"

        # 5. Calculate totals on server and prepare order line items
        subtotal = Decimal("0.00")
        order_id = uuid.uuid4()
        created_items: List[OrderItem] = []

        for item_in in order_in.items:
            product = product_map[item_in.product_id]
            unit_price = Decimal(str(product.price))
            total_price = unit_price * item_in.quantity
            subtotal += total_price

            order_item = OrderItem(
                id=uuid.uuid4(),
                order_id=order_id,
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                unit_price=unit_price,
                quantity=item_in.quantity,
                total_price=total_price,
            )
            created_items.append(order_item)

            # 6 & 7. Stock decrement & Inventory Movement
            if auto_decrement and product.track_inventory:
                product.stock_quantity -= item_in.quantity
                movement = InventoryMovement(
                    id=uuid.uuid4(),
                    business_id=tenant.business_id,
                    product_id=product.id,
                    order_id=order_id,
                    change_quantity=-item_in.quantity,
                    movement_type="order_fulfillment",
                    notes=f"Auto-decremented for order {order_number}",
                )
                db.add(movement)

        discount_amount = max(Decimal("0.00"), Decimal(str(order_in.discount_amount)))
        shipping_fee = max(Decimal("0.00"), Decimal(str(order_in.shipping_fee)))
        total_amount = max(Decimal("0.00"), subtotal - discount_amount + shipping_fee)

        # 8. Create Order
        order = Order(
            id=order_id,
            business_id=tenant.business_id,
            order_number=order_number,
            customer_id=customer.id if customer else None,
            status="pending",
            payment_status="unpaid",
            source=order_in.source,
            subtotal=subtotal,
            tax_amount=Decimal("0.00"),
            discount_amount=discount_amount,
            shipping_fee=shipping_fee,
            total_amount=total_amount,
            currency="USD",
            notes=order_in.notes,
            fulfillment_address=order_in.fulfillment_address,
            idempotency_key=order_in.idempotency_key,
        )
        db.add(order)

        for item in created_items:
            db.add(item)

        # 9. Initial status history entry
        initial_history = OrderStatusHistory(
            id=uuid.uuid4(),
            order_id=order_id,
            previous_status=None,
            new_status="pending",
            notes="Order placed",
            changed_by_user_id=tenant.user_id,
        )
        db.add(initial_history)

        # 10. Update customer aggregate stats
        if customer:
            customer.total_orders += 1
            customer.total_spend += total_amount

        await db.commit()

        # Reload complete order with relations
        return await OrderService.get_order_detail(db, tenant, order_id)

    @staticmethod
    async def get_order_detail(
        db: AsyncSession,
        tenant: TenantContext,
        order_id: uuid.UUID,
    ) -> OrderResponse:
        """Fetch single order by ID with line items, customer, and status history."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.customer),
                selectinload(Order.status_history),
            )
            .where(
                Order.id == order_id,
                Order.business_id == tenant.business_id,
            )
        )
        result = await db.execute(stmt)
        order = result.scalars().first()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found in this business",
            )

        items_resp = [
            OrderItemResponse(
                id=item.id,
                order_id=item.order_id,
                product_id=item.product_id,
                product_name=item.product_name,
                product_sku=item.product_sku,
                unit_price=item.unit_price,
                quantity=item.quantity,
                total_price=item.total_price,
                created_at=item.created_at,
            )
            for item in order.items
        ]

        history_resp = [
            OrderStatusHistoryResponse(
                id=h.id,
                order_id=h.order_id,
                previous_status=h.previous_status,
                new_status=h.new_status,
                notes=h.notes,
                changed_by_user_id=h.changed_by_user_id,
                created_at=h.created_at,
            )
            for h in order.status_history
        ]

        customer_resp = (
            CustomerResponse.model_validate(order.customer) if order.customer else None
        )

        return OrderResponse(
            id=order.id,
            business_id=order.business_id,
            order_number=order.order_number,
            customer_id=order.customer_id,
            customer=customer_resp,
            status=order.status,
            payment_status=order.payment_status,
            source=order.source,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            discount_amount=order.discount_amount,
            shipping_fee=order.shipping_fee,
            total_amount=order.total_amount,
            currency=order.currency,
            notes=order.notes,
            fulfillment_address=order.fulfillment_address,
            idempotency_key=order.idempotency_key,
            items=items_resp,
            status_history=history_resp,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    @staticmethod
    async def transition_status(
        db: AsyncSession,
        tenant: TenantContext,
        order_id: uuid.UUID,
        new_status: str,
        notes: Optional[str] = None,
        changed_by: Optional[uuid.UUID] = None,
    ) -> OrderResponse:
        """
        Transition order status with state machine validation:
        pending → confirmed, cancelled
        confirmed → preparing, cancelled
        preparing → ready_for_dispatch, cancelled
        ready_for_dispatch → shipped, cancelled
        shipped → delivered, cancelled
        delivered → (terminal)
        cancelled → (terminal)
        """
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.id == order_id,
                Order.business_id == tenant.business_id,
            )
        )
        result = await db.execute(stmt)
        order = result.scalars().first()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found in this business",
            )

        current_status = order.status
        allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_transitions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Invalid status transition from '{current_status}' to '{new_status}'. "
                    f"Permitted transitions: {allowed_transitions}"
                ),
            )

        # Update order status
        order.status = new_status

        # If transitioning to cancelled, restore inventory
        if new_status == "cancelled":
            stmt_settings = select(BusinessSettings).where(
                BusinessSettings.business_id == tenant.business_id
            )
            b_settings = (await db.execute(stmt_settings)).scalars().first()
            if b_settings and b_settings.auto_decrement_stock:
                for item in order.items:
                    if item.product_id:
                        stmt_prod = select(Product).where(
                            Product.id == item.product_id,
                            Product.business_id == tenant.business_id,
                        )
                        prod = (await db.execute(stmt_prod)).scalars().first()
                        if prod and prod.track_inventory:
                            prod.stock_quantity += item.quantity
                            movement = InventoryMovement(
                                id=uuid.uuid4(),
                                business_id=tenant.business_id,
                                product_id=prod.id,
                                order_id=order.id,
                                change_quantity=item.quantity,
                                movement_type="order_cancellation",
                                notes=f"Stock restored on cancellation of {order.order_number}",
                            )
                            db.add(movement)

        # Append status history
        history_entry = OrderStatusHistory(
            id=uuid.uuid4(),
            order_id=order.id,
            previous_status=current_status,
            new_status=new_status,
            notes=notes,
            changed_by_user_id=changed_by or tenant.user_id,
        )
        db.add(history_entry)

        await db.commit()
        return await OrderService.get_order_detail(db, tenant, order_id)

    @staticmethod
    async def update_order(
        db: AsyncSession,
        tenant: TenantContext,
        order_id: uuid.UUID,
        order_in: OrderUpdate,
    ) -> OrderResponse:
        """Update permitted mutable fields on an order."""
        stmt = select(Order).where(
            Order.id == order_id,
            Order.business_id == tenant.business_id,
        )
        result = await db.execute(stmt)
        order = result.scalars().first()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found in this business",
            )

        if order_in.notes is not None:
            order.notes = order_in.notes
        if order_in.fulfillment_address is not None:
            order.fulfillment_address = order_in.fulfillment_address

        await db.commit()
        return await OrderService.get_order_detail(db, tenant, order_id)

    @staticmethod
    async def get_orders(
        db: AsyncSession,
        tenant: TenantContext,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        payment_status: Optional[str] = None,
        source: Optional[str] = None,
    ) -> PaginatedResponse[OrderListItem]:
        """Fetch paginated orders scoped to the tenant with flexible filtering."""
        query = (
            select(
                Order,
                Customer.name.label("customer_name"),
                func.count(OrderItem.id).label("items_count"),
            )
            .outerjoin(Customer, Order.customer_id == Customer.id)
            .outerjoin(OrderItem, Order.id == OrderItem.order_id)
            .where(Order.business_id == tenant.business_id)
            .group_by(Order.id, Customer.name)
        )

        if status_filter:
            query = query.where(Order.status == status_filter)
        if customer_id:
            query = query.where(Order.customer_id == customer_id)
        if payment_status:
            query = query.where(Order.payment_status == payment_status)
        if source:
            query = query.where(Order.source == source)
        if date_from:
            query = query.where(Order.created_at >= date_from)
        if date_to:
            query = query.where(Order.created_at <= date_to)

        # Count total
        count_stmt = select(func.count(Order.id)).where(Order.business_id == tenant.business_id)
        if status_filter:
            count_stmt = count_stmt.where(Order.status == status_filter)
        if customer_id:
            count_stmt = count_stmt.where(Order.customer_id == customer_id)
        if payment_status:
            count_stmt = count_stmt.where(Order.payment_status == payment_status)
        if source:
            count_stmt = count_stmt.where(Order.source == source)
        if date_from:
            count_stmt = count_stmt.where(Order.created_at >= date_from)
        if date_to:
            count_stmt = count_stmt.where(Order.created_at <= date_to)

        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size)
        rows = (await db.execute(stmt)).all()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        has_next = page < total_pages

        items = [
            OrderListItem(
                id=row[0].id,
                business_id=row[0].business_id,
                order_number=row[0].order_number,
                customer_id=row[0].customer_id,
                customer_name=row[1],
                status=row[0].status,
                payment_status=row[0].payment_status,
                source=row[0].source,
                total_amount=row[0].total_amount,
                currency=row[0].currency,
                items_count=row[2] or 0,
                created_at=row[0].created_at,
            )
            for row in rows
        ]

        return PaginatedResponse[OrderListItem](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
        )

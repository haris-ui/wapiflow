import logging
import math
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import TenantContext
from app.models.customer import Customer
from app.models.order import Order
from app.models.whatsapp import Conversation, Message, WhatsAppAccount
from app.schemas.common import PaginatedResponse
from app.schemas.conversation import (
    ConversationCustomerInfo,
    ConversationDetailResponse,
    ConversationQuickOrderCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.schemas.order import OrderCreate, OrderResponse
from app.services.meta_client import MetaWhatsAppClient
from app.services.order_service import OrderService

logger = logging.getLogger("wapiflow.conversations")


class ConversationService:
    """Live WhatsApp Conversation management service with strict tenant isolation."""

    @staticmethod
    async def get_conversations(
        db: AsyncSession,
        tenant: TenantContext,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ConversationResponse]:
        """List paginated conversations scoped to the business tenant."""
        query = (
            select(Conversation)
            .where(Conversation.business_id == tenant.business_id)
            .outerjoin(Customer, Conversation.customer_id == Customer.id)
            .options(selectinload(Conversation.customer))
        )

        if status_filter:
            query = query.where(Conversation.status == status_filter)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Conversation.last_message_preview.ilike(pattern),
                    Customer.name.ilike(pattern),
                    Customer.phone_number.ilike(pattern),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = (
            query.order_by(
                Conversation.last_message_at.desc().nullslast(),
                Conversation.created_at.desc(),
            )
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        convs = result.scalars().all()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        has_next = page < total_pages

        items = [
            ConversationResponse(
                id=c.id,
                business_id=c.business_id,
                customer_id=c.customer_id,
                customer=ConversationCustomerInfo(
                    id=c.customer.id,
                    name=c.customer.name,
                    phone_number=c.customer.phone_number,
                    email=c.customer.email,
                )
                if c.customer
                else None,
                status=c.status,
                assigned_to=c.assigned_to,
                unread_count=c.unread_count,
                last_message_at=c.last_message_at,
                last_message_preview=c.last_message_preview,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in convs
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
        )

    @staticmethod
    async def get_conversation_detail(
        db: AsyncSession,
        tenant: TenantContext,
        conversation_id: uuid.UUID,
    ) -> ConversationDetailResponse:
        """Retrieve conversation detail, mark as read, and attach customer order history."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.business_id == tenant.business_id,
            )
            .options(selectinload(Conversation.customer))
        )
        conv = (await db.execute(stmt)).scalars().first()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        # Mark conversation read
        if conv.unread_count > 0:
            conv.unread_count = 0
            await db.commit()

        # Fetch recent orders for customer
        recent_orders: List[OrderResponse] = []
        if conv.customer_id:
            stmt_orders = (
                select(Order)
                .where(
                    Order.business_id == tenant.business_id,
                    Order.customer_id == conv.customer_id,
                )
                .options(selectinload(Order.items), selectinload(Order.status_history))
                .order_by(Order.created_at.desc())
                .limit(5)
            )
            orders_res = (await db.execute(stmt_orders)).scalars().all()
            for o in orders_res:
                recent_orders.append(await OrderService.get_order_detail(db, tenant, o.id))

        return ConversationDetailResponse(
            id=conv.id,
            business_id=conv.business_id,
            customer_id=conv.customer_id,
            customer=ConversationCustomerInfo(
                id=conv.customer.id,
                name=conv.customer.name,
                phone_number=conv.customer.phone_number,
                email=conv.customer.email,
            )
            if conv.customer
            else None,
            status=conv.status,
            assigned_to=conv.assigned_to,
            unread_count=conv.unread_count,
            last_message_at=conv.last_message_at,
            last_message_preview=conv.last_message_preview,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            recent_orders=recent_orders,
        )

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        tenant: TenantContext,
        conversation_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[MessageResponse]:
        """Fetch chronological message history for a conversation thread."""
        # Verify conversation ownership
        stmt_conv = select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.business_id == tenant.business_id,
        )
        if not (await db.execute(stmt_conv)).scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        query = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.business_id == tenant.business_id,
        )

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        offset = (page - 1) * page_size
        stmt = query.order_by(Message.created_at.asc()).offset(offset).limit(page_size)
        result = await db.execute(stmt)
        msgs = result.scalars().all()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        has_next = page < total_pages

        items = [
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                business_id=m.business_id,
                wa_message_id=m.wa_message_id,
                direction=m.direction,
                message_type=m.message_type,
                content=m.content,
                media_url=m.media_url,
                status=m.status,
                error_message=m.error_message,
                is_internal_note=m.is_internal_note,
                created_at=m.created_at,
            )
            for m in msgs
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
        )

    @staticmethod
    async def send_message(
        db: AsyncSession,
        tenant: TenantContext,
        conversation_id: uuid.UUID,
        message_in: MessageCreate,
    ) -> MessageResponse:
        """Sends an outbound WhatsApp message to the customer or saves an internal note."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.business_id == tenant.business_id,
            )
            .options(selectinload(Conversation.customer))
        )
        conv = (await db.execute(stmt)).scalars().first()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        # 1. Handle Internal Note
        if message_in.is_internal_note:
            note = Message(
                conversation_id=conv.id,
                business_id=tenant.business_id,
                direction="outbound",
                message_type="text",
                content=message_in.content,
                status="sent",
                is_internal_note=True,
                sent_by=tenant.user_id,
            )
            db.add(note)
            await db.commit()
            await db.refresh(note)
            return MessageResponse(
                id=note.id,
                conversation_id=note.conversation_id,
                business_id=note.business_id,
                wa_message_id=None,
                direction=note.direction,
                message_type=note.message_type,
                content=note.content,
                media_url=None,
                status=note.status,
                is_internal_note=True,
                created_at=note.created_at,
            )

        # 2. Outbound WhatsApp Message
        if not conv.customer or not conv.customer.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send WhatsApp message: conversation has no valid customer phone number",
            )

        # Fetch active WhatsApp Account for the business
        stmt_acc = (
            select(WhatsAppAccount)
            .where(
                WhatsAppAccount.business_id == tenant.business_id,
                WhatsAppAccount.status == "connected",
            )
            .options(selectinload(WhatsAppAccount.phone_numbers))
        )
        account = (await db.execute(stmt_acc)).scalars().first()

        wa_message_id: Optional[str] = f"wamid.{uuid.uuid4().hex}"
        delivery_status = "sent"
        error_msg: Optional[str] = None

        if account and account.phone_numbers:
            phone_num_id = account.phone_numbers[0].phone_number
            meta_client = MetaWhatsAppClient()
            try:
                res = await meta_client.send_text_message(
                    phone_number_id=phone_num_id,
                    access_token=account.access_token,
                    to_phone=conv.customer.phone_number,
                    text=message_in.content,
                )
                if res.get("messages"):
                    wa_message_id = res["messages"][0].get("id", wa_message_id)
            except Exception as e:
                logger.warning(f"Meta Cloud API call failed: {e}. Storing message as pending.")
                delivery_status = "failed"
                error_msg = str(e)

        # Insert Message record
        msg_record = Message(
            conversation_id=conv.id,
            business_id=tenant.business_id,
            wa_message_id=wa_message_id,
            direction="outbound",
            message_type=message_in.message_type,
            content=message_in.content,
            status=delivery_status,
            error_message=error_msg,
            sent_by=tenant.user_id,
            is_internal_note=False,
        )
        db.add(msg_record)

        # Update Conversation timestamp and preview
        conv.last_message_at = datetime.utcnow()
        conv.last_message_preview = message_in.content[:150]
        await db.commit()
        await db.refresh(msg_record)

        return MessageResponse(
            id=msg_record.id,
            conversation_id=msg_record.conversation_id,
            business_id=msg_record.business_id,
            wa_message_id=msg_record.wa_message_id,
            direction=msg_record.direction,
            message_type=msg_record.message_type,
            content=msg_record.content,
            media_url=None,
            status=msg_record.status,
            error_message=msg_record.error_message,
            is_internal_note=False,
            created_at=msg_record.created_at,
        )

    @staticmethod
    async def update_conversation(
        db: AsyncSession,
        tenant: TenantContext,
        conversation_id: uuid.UUID,
        update_data: ConversationUpdate,
    ) -> ConversationResponse:
        """Update conversation status (open, resolved, snoozed) or assign staff."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.business_id == tenant.business_id,
            )
            .options(selectinload(Conversation.customer))
        )
        conv = (await db.execute(stmt)).scalars().first()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        if update_data.status is not None:
            if update_data.status not in ("open", "resolved", "snoozed"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Invalid status. Allowed values: 'open', 'resolved', 'snoozed'",
                )
            conv.status = update_data.status

        if update_data.assigned_to is not None:
            conv.assigned_to = update_data.assigned_to

        conv.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(conv)

        return ConversationResponse(
            id=conv.id,
            business_id=conv.business_id,
            customer_id=conv.customer_id,
            customer=ConversationCustomerInfo(
                id=conv.customer.id,
                name=conv.customer.name,
                phone_number=conv.customer.phone_number,
                email=conv.customer.email,
            )
            if conv.customer
            else None,
            status=conv.status,
            assigned_to=conv.assigned_to,
            unread_count=conv.unread_count,
            last_message_at=conv.last_message_at,
            last_message_preview=conv.last_message_preview,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    @staticmethod
    async def create_order_from_conversation(
        db: AsyncSession,
        tenant: TenantContext,
        conversation_id: uuid.UUID,
        order_in: ConversationQuickOrderCreate,
    ) -> OrderResponse:
        """Quickly creates an order linked to the customer and conversation context."""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.business_id == tenant.business_id,
        )
        conv = (await db.execute(stmt)).scalars().first()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        # Prepare OrderCreate payload
        create_payload = OrderCreate(
            items=order_in.items,
            customer_id=conv.customer_id,
            notes=order_in.notes or f"Generated via WhatsApp conversation #{conversation_id}",
            fulfillment_address=order_in.fulfillment_address,
            idempotency_key=order_in.idempotency_key,
        )

        order_resp = await OrderService.create_order(db, tenant, create_payload)

        # Automatically record confirmation internal note in conversation thread
        note_content = (
            f"🛒 Order {order_resp.order_number} created for "
            f"{order_resp.currency} {order_resp.total_amount:.2f}."
        )
        confirm_note = Message(
            conversation_id=conv.id,
            business_id=tenant.business_id,
            direction="outbound",
            message_type="text",
            content=note_content,
            status="sent",
            is_internal_note=True,
            sent_by=tenant.user_id,
        )
        db.add(confirm_note)
        conv.last_message_at = datetime.utcnow()
        conv.last_message_preview = note_content
        await db.commit()

        return order_resp

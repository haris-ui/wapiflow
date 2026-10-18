import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.customer import Customer
from app.models.whatsapp import (
    Conversation,
    Message,
    WebhookEvent,
    WhatsAppAccount,
    WhatsAppPhoneNumber,
)
from app.services.meta_client import MetaWhatsAppClient

logger = logging.getLogger("wapiflow.webhook")
settings = get_settings()


class WebhookService:
    """Processes Meta WhatsApp Cloud API webhooks with HMAC validation and deduplication."""

    @staticmethod
    def verify_handshake(mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> str:
        """
        Validates the Meta webhook subscription handshake (GET request).
        Returns the hub.challenge integer/string if token matches.
        """
        expected_token = settings.META_VERIFY_TOKEN
        if mode == "subscribe" and token == expected_token:
            logger.info("Meta webhook handshake successfully verified")
            return challenge or ""

        logger.warning(f"Webhook handshake failed: mode={mode}, token_match={token == expected_token}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification token mismatch",
        )

    @classmethod
    async def process_webhook(
        cls,
        db: AsyncSession,
        raw_body: bytes,
        signature_header: Optional[str],
    ) -> Dict[str, Any]:
        """
        Cryptographically validates and ingests incoming Meta WhatsApp webhook payload.
        Idempotently stores events and normalizes inbound messages & delivery receipts.
        """
        # 1. Cryptographic HMAC-SHA256 signature verification
        is_valid = MetaWhatsAppClient.verify_signature(raw_body, signature_header)
        if not is_valid:
            logger.warning("Rejected webhook: invalid HMAC-SHA256 signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid cryptographic signature",
            )

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Malformed JSON in webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed JSON body",
            )

        # 2. Extract entries and process
        entries = payload.get("entry", [])
        if not entries:
            return {"status": "ok", "message": "No entries in payload"}

        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") != "messages":
                    continue

                val = change.get("value", {})
                metadata = val.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id")

                # Resolve Business Tenant from phone_number_id
                tenant_business_id = await cls._resolve_tenant_business(db, phone_number_id)

                # Process delivery status receipts (sent, delivered, read, failed)
                statuses = val.get("statuses", [])
                for s in statuses:
                    await cls._process_status_update(db, tenant_business_id, s, payload)

                # Process inbound messages
                messages = val.get("messages", [])
                contacts = val.get("contacts", [])
                contacts_map = {c.get("wa_id"): c.get("profile", {}).get("name") for c in contacts if "wa_id" in c}

                for msg in messages:
                    await cls._process_inbound_message(
                        db=db,
                        business_id=tenant_business_id,
                        phone_number_id=phone_number_id,
                        msg=msg,
                        contacts_map=contacts_map,
                        raw_payload=payload,
                    )

        await db.commit()
        return {"status": "ok", "processed": True}

    @classmethod
    async def _resolve_tenant_business(
        cls,
        db: AsyncSession,
        phone_number_id: Optional[str],
    ) -> Optional[uuid.UUID]:
        """Resolves tenant business ID by Meta phone_number_id or falls back to first account."""
        if phone_number_id:
            stmt = select(WhatsAppPhoneNumber.business_id).where(
                WhatsAppPhoneNumber.phone_number == phone_number_id
            )
            res = (await db.execute(stmt)).scalars().first()
            if res:
                return res

            # Check by waba_id or account
            stmt_acc = select(WhatsAppAccount.business_id).where(
                WhatsAppAccount.waba_id == phone_number_id
            )
            res_acc = (await db.execute(stmt_acc)).scalars().first()
            if res_acc:
                return res_acc

        # Fallback: get first registered WhatsApp account
        stmt_any = select(WhatsAppAccount.business_id).limit(1)
        return (await db.execute(stmt_any)).scalars().first()

    @classmethod
    async def _process_inbound_message(
        cls,
        db: AsyncSession,
        business_id: Optional[uuid.UUID],
        phone_number_id: Optional[str],
        msg: Dict[str, Any],
        contacts_map: Dict[str, str],
        raw_payload: Dict[str, Any],
    ) -> None:
        """Handles an inbound customer message, customer upsert, and conversation thread update."""
        wa_message_id = msg.get("id")
        from_phone = msg.get("from")
        msg_type = msg.get("type", "text")

        if not wa_message_id or not from_phone:
            return

        # Record raw webhook event for audit & deduplication
        event_record = WebhookEvent(
            business_id=business_id,
            wa_message_id=wa_message_id,
            event_type=f"message.{msg_type}",
            payload=raw_payload,
            processing_status="pending",
        )
        db.add(event_record)

        # Idempotency check: verify if message ID already processed
        stmt_dup = select(Message.id).where(Message.wa_message_id == wa_message_id)
        existing = (await db.execute(stmt_dup)).scalars().first()
        if existing:
            logger.info(f"Duplicate WhatsApp message received: {wa_message_id}, skipping.")
            event_record.processing_status = "duplicate"
            return

        # Extract message body
        content: Optional[str] = None
        media_url: Optional[str] = None
        if msg_type == "text":
            content = msg.get("text", {}).get("body", "")
        elif msg_type == "interactive":
            interactive = msg.get("interactive", {})
            itype = interactive.get("type")
            if itype == "button_reply":
                content = interactive.get("button_reply", {}).get("title")
            elif itype == "list_reply":
                content = interactive.get("list_reply", {}).get("title")
            else:
                content = "[Interactive message response]"
        elif msg_type in ("image", "document", "audio", "video"):
            media_info = msg.get(msg_type, {})
            caption = media_info.get("caption", "")
            media_id = media_info.get("id", "")
            content = f"[{msg_type.capitalize()}] {caption}".strip()
            media_url = f"meta://media/{media_id}"
        elif msg_type == "location":
            loc = msg.get("location", {})
            name = loc.get("name") or "Location"
            content = f"📍 {name} ({loc.get('latitude')}, {loc.get('longitude')})"
        else:
            content = f"[{msg_type} message]"

        if not business_id:
            logger.warning(f"Inbound message from {from_phone} has no associated business tenant")
            event_record.processing_status = "failed"
            event_record.error_message = "No matching business tenant found"
            return

        # Upsert Customer by (business_id, phone_number)
        customer_name = contacts_map.get(from_phone) or f"Customer {from_phone[-4:]}"
        stmt_cust = select(Customer).where(
            Customer.business_id == business_id,
            or_(
                Customer.phone_number == from_phone,
                Customer.phone_number == f"+{from_phone}",
            ),
        )
        customer = (await db.execute(stmt_cust)).scalars().first()
        if not customer:
            customer = Customer(
                business_id=business_id,
                name=customer_name,
                phone_number=f"+{from_phone.lstrip('+')}",
            )
            db.add(customer)
            await db.flush()
        elif not customer.name and customer_name:
            customer.name = customer_name

        # Upsert Conversation thread
        stmt_conv = select(Conversation).where(
            Conversation.business_id == business_id,
            Conversation.customer_id == customer.id,
        )
        conv = (await db.execute(stmt_conv)).scalars().first()
        if not conv:
            conv = Conversation(
                business_id=business_id,
                customer_id=customer.id,
                status="open",
                unread_count=1,
                last_message_at=datetime.utcnow(),
                last_message_preview=content[:150] if content else "",
            )
            db.add(conv)
            await db.flush()
        else:
            conv.unread_count += 1
            conv.last_message_at = datetime.utcnow()
            conv.last_message_preview = content[:150] if content else ""
            if conv.status == "resolved":
                conv.status = "open"  # Reopen conversation on new inbound message

        # Insert Inbound Message
        message_record = Message(
            conversation_id=conv.id,
            business_id=business_id,
            wa_message_id=wa_message_id,
            direction="inbound",
            message_type=msg_type,
            content=content,
            media_url=media_url,
            status="received",
            is_internal_note=False,
            metadata_=msg,
        )
        db.add(message_record)
        event_record.processing_status = "processed"
        event_record.processed_at = datetime.utcnow()

    @classmethod
    async def _process_status_update(
        cls,
        db: AsyncSession,
        business_id: Optional[uuid.UUID],
        status_item: Dict[str, Any],
        raw_payload: Dict[str, Any],
    ) -> None:
        """Handles outbound message delivery receipts (sent -> delivered -> read -> failed)."""
        wa_message_id = status_item.get("id")
        delivery_status = status_item.get("status")  # sent, delivered, read, failed

        if not wa_message_id or not delivery_status:
            return

        # Record webhook event
        event_record = WebhookEvent(
            business_id=business_id,
            wa_message_id=wa_message_id,
            event_type=f"status.{delivery_status}",
            payload=raw_payload,
            processing_status="processed",
            processed_at=datetime.utcnow(),
        )
        db.add(event_record)

        # Update message status
        errors = status_item.get("errors", [])
        error_msg = errors[0].get("message") if errors else None
        error_code = str(errors[0].get("code")) if errors else None

        stmt = (
            update(Message)
            .where(Message.wa_message_id == wa_message_id)
            .values(
                status=delivery_status,
                error_message=error_msg,
                error_code=error_code,
                updated_at=datetime.utcnow(),
            )
        )
        await db.execute(stmt)

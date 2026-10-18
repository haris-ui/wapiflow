import logging
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.dependencies import TenantContext
from app.models.whatsapp import WhatsAppAccount, WhatsAppPhoneNumber
from app.schemas.whatsapp import (
    TestMessageRequest,
    WhatsAppAccountConnect,
    WhatsAppAccountResponse,
    WhatsAppConfigInfo,
    WhatsAppPhoneNumberResponse,
)
from app.services.meta_client import MetaWhatsAppClient

logger = logging.getLogger("wapiflow.whatsapp")
settings = get_settings()


class WhatsAppService:
    """Manages WhatsApp Business Account connection and configuration per tenant."""

    @staticmethod
    async def get_config_info(
        db: AsyncSession,
        tenant: TenantContext,
    ) -> WhatsAppConfigInfo:
        """Retrieve tenant WhatsApp connection state and webhook endpoints."""
        stmt = (
            select(WhatsAppAccount)
            .where(WhatsAppAccount.business_id == tenant.business_id)
            .options(selectinload(WhatsAppAccount.phone_numbers))
        )
        account = (await db.execute(stmt)).scalars().first()

        account_resp: Optional[WhatsAppAccountResponse] = None
        if account:
            phone_numbers = [
                WhatsAppPhoneNumberResponse(
                    id=pn.id,
                    phone_number=pn.phone_number,
                    display_name=pn.display_name,
                    quality_rating=pn.quality_rating,
                    status=pn.status,
                    is_primary=pn.is_primary,
                    created_at=pn.created_at,
                )
                for pn in account.phone_numbers
            ]
            account_resp = WhatsAppAccountResponse(
                id=account.id,
                business_id=account.business_id,
                waba_id=account.waba_id,
                app_id=account.app_id,
                status=account.status,
                webhook_verified_at=account.webhook_verified_at,
                phone_numbers=phone_numbers,
                created_at=account.created_at,
                updated_at=account.updated_at,
            )

        callback_url = f"{settings.SUPABASE_URL.split('.supabase')[0] if settings.SUPABASE_URL else 'https://api.wapiflow.com'}/api/v1/webhooks/whatsapp"

        return WhatsAppConfigInfo(
            webhook_callback_url=callback_url,
            verify_token=settings.META_VERIFY_TOKEN,
            is_connected=account is not None and account.status == "connected",
            account=account_resp,
        )

    @staticmethod
    async def connect_account(
        db: AsyncSession,
        tenant: TenantContext,
        data: WhatsAppAccountConnect,
    ) -> WhatsAppAccountResponse:
        """Connects or updates Meta WhatsApp Cloud API credentials for the tenant."""
        stmt = (
            select(WhatsAppAccount)
            .where(WhatsAppAccount.business_id == tenant.business_id)
            .options(selectinload(WhatsAppAccount.phone_numbers))
        )
        account = (await db.execute(stmt)).scalars().first()

        phone_num_id = data.phone_number_id or data.phone_number

        # Optionally test credentials with Meta Graph API
        meta_client = MetaWhatsAppClient()
        quality_rating = "UNKNOWN"
        try:
            info = await meta_client.fetch_phone_number_info(phone_num_id, data.access_token)
            if info:
                quality_rating = info.get("quality_rating", "GREEN")
        except Exception as e:
            logger.warning(f"Could not verify Meta token live: {e}")

        if not account:
            account = WhatsAppAccount(
                business_id=tenant.business_id,
                waba_id=data.waba_id,
                app_id="wapiflow",
                access_token=data.access_token,
                status="connected",
                webhook_verified_at=datetime.utcnow(),
            )
            db.add(account)
            await db.flush()

            phone_entry = WhatsAppPhoneNumber(
                business_id=tenant.business_id,
                whatsapp_account_id=account.id,
                phone_number=phone_num_id,
                display_name=data.display_name or data.phone_number,
                quality_rating=quality_rating,
                status="active",
                is_primary=True,
            )
            db.add(phone_entry)
        else:
            account.waba_id = data.waba_id
            account.access_token = data.access_token
            account.status = "connected"
            account.updated_at = datetime.utcnow()

            # Update or create phone number
            if account.phone_numbers:
                primary = account.phone_numbers[0]
                primary.phone_number = phone_num_id
                primary.display_name = data.display_name or primary.display_name
                primary.quality_rating = quality_rating
                primary.status = "active"
            else:
                phone_entry = WhatsAppPhoneNumber(
                    business_id=tenant.business_id,
                    whatsapp_account_id=account.id,
                    phone_number=phone_num_id,
                    display_name=data.display_name or data.phone_number,
                    quality_rating=quality_rating,
                    status="active",
                    is_primary=True,
                )
                db.add(phone_entry)

        await db.commit()
        await db.refresh(account)

        return await WhatsAppService.get_account_status(db, tenant)

    @staticmethod
    async def get_account_status(
        db: AsyncSession,
        tenant: TenantContext,
    ) -> WhatsAppAccountResponse:
        """Fetch current connected WhatsApp account for the tenant."""
        stmt = (
            select(WhatsAppAccount)
            .where(WhatsAppAccount.business_id == tenant.business_id)
            .options(selectinload(WhatsAppAccount.phone_numbers))
        )
        account = (await db.execute(stmt)).scalars().first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="WhatsApp account is not connected for this business",
            )

        phone_numbers = [
            WhatsAppPhoneNumberResponse(
                id=pn.id,
                phone_number=pn.phone_number,
                display_name=pn.display_name,
                quality_rating=pn.quality_rating,
                status=pn.status,
                is_primary=pn.is_primary,
                created_at=pn.created_at,
            )
            for pn in account.phone_numbers
        ]

        return WhatsAppAccountResponse(
            id=account.id,
            business_id=account.business_id,
            waba_id=account.waba_id,
            app_id=account.app_id,
            status=account.status,
            webhook_verified_at=account.webhook_verified_at,
            phone_numbers=phone_numbers,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    @staticmethod
    async def disconnect_account(
        db: AsyncSession,
        tenant: TenantContext,
    ) -> dict:
        """Disconnects WhatsApp integration from business."""
        stmt = select(WhatsAppAccount).where(WhatsAppAccount.business_id == tenant.business_id)
        account = (await db.execute(stmt)).scalars().first()
        if account:
            account.status = "disconnected"
            account.access_token = ""
            await db.commit()
        return {"status": "ok", "message": "WhatsApp integration disconnected"}

    @staticmethod
    async def send_test_message(
        db: AsyncSession,
        tenant: TenantContext,
        data: TestMessageRequest,
    ) -> dict:
        """Sends a verification test WhatsApp message using tenant credentials."""
        stmt = (
            select(WhatsAppAccount)
            .where(WhatsAppAccount.business_id == tenant.business_id)
            .options(selectinload(WhatsAppAccount.phone_numbers))
        )
        account = (await db.execute(stmt)).scalars().first()
        if not account or account.status != "connected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send test message: WhatsApp account is not connected",
            )

        if not account.phone_numbers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No registered phone number configured on WhatsApp account",
            )

        phone_number_id = account.phone_numbers[0].phone_number
        meta_client = MetaWhatsAppClient()

        try:
            res = await meta_client.send_text_message(
                phone_number_id=phone_number_id,
                access_token=account.access_token,
                to_phone=data.recipient_phone,
                text=data.message,
            )
            return {
                "status": "ok",
                "message": f"Test message dispatched to {data.recipient_phone}",
                "meta_response": res,
            }
        except Exception as e:
            logger.error(f"Failed to dispatch test message: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Meta Cloud API error: {str(e)}",
            )

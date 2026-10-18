import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.config import get_settings

logger = logging.getLogger("wapiflow.meta_client")
settings = get_settings()


class MetaWhatsAppClient:
    """Official Meta WhatsApp Cloud API client targeting Graph API."""

    def __init__(self, api_version: Optional[str] = None):
        self.api_version = api_version or settings.META_WHATSAPP_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    @staticmethod
    def verify_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
        """
        Cryptographically verifies the Meta X-Hub-Signature-256 header.
        Uses HMAC-SHA256 with META_APP_SECRET.
        """
        if not signature_header:
            logger.warning("Missing X-Hub-Signature-256 header on incoming webhook")
            return False

        app_secret = settings.META_APP_SECRET
        if not app_secret:
            # If no secret configured in development, warn and allow testing
            logger.warning("META_APP_SECRET is not configured; allowing webhook in development mode")
            return True

        if not signature_header.startswith("sha256="):
            return False

        expected_sig = signature_header.split("sha256=")[1].strip()
        computed_sig = hmac.new(
            app_secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed_sig, expected_sig)

    async def fetch_phone_number_info(
        self,
        phone_number_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """Fetch registered phone number attributes and quality rating from Meta Graph API."""
        url = f"{self.base_url}/{phone_number_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"fields": "verified_name,display_phone_number,quality_rating,code_verification_status"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                logger.error(f"Meta Graph API error fetching phone number {phone_number_id}: {resp.text}")
                return {}
            return resp.json()

    async def send_text_message(
        self,
        phone_number_id: str,
        access_token: str,
        to_phone: str,
        text: str,
    ) -> Dict[str, Any]:
        """
        Send an outbound plain text message via Meta Cloud API.
        Returns response dict containing 'messages': [{'id': 'wamid.HBg...'}]
        """
        url = f"{self.base_url}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        # Format phone to strip plus and non-digits if needed
        clean_phone = "".join(filter(str.isdigit, to_phone))
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text,
            },
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            data = resp.json()
            if resp.status_code not in (200, 201):
                logger.error(f"Failed to send WhatsApp message to {clean_phone}: {resp.text}")
                error_msg = data.get("error", {}).get("message", resp.text)
                raise RuntimeError(f"Meta Cloud API error: {error_msg}")
            return data

    async def send_template_message(
        self,
        phone_number_id: str,
        access_token: str,
        to_phone: str,
        template_name: str,
        language_code: str = "en_US",
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send an approved WhatsApp Business template message."""
        url = f"{self.base_url}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        clean_phone = "".join(filter(str.isdigit, to_phone))
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            data = resp.json()
            if resp.status_code not in (200, 201):
                logger.error(f"Failed to send template {template_name} to {clean_phone}: {resp.text}")
                error_msg = data.get("error", {}).get("message", resp.text)
                raise RuntimeError(f"Meta Cloud API template error: {error_msg}")
            return data

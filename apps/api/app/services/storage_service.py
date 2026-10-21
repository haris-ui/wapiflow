import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
import httpx

from app.config import get_settings

logger = logging.getLogger("wapiflow.services.storage")
settings = get_settings()

# Allowed MIME types for security
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
    "audio/ogg",
    "audio/mpeg",
    "video/mp4",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


class StorageService:
    """
    Multi-tenant storage manager supporting Cloudflare R2 (S3-compatible)
    with local disk fallback for zero-dependency development and testing.
    """

    @classmethod
    def is_r2_configured(cls) -> bool:
        """Checks if Cloudflare R2 credentials are fully configured."""
        return bool(
            settings.R2_ACCOUNT_ID
            and settings.R2_ACCESS_KEY_ID
            and settings.R2_SECRET_ACCESS_KEY
            and settings.R2_BUCKET_NAME
        )

    @classmethod
    def get_s3_client(cls):
        """Constructs an S3 client configured for Cloudflare R2."""
        endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitizes filename preventing directory traversal attacks."""
        clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
        return clean.strip("._") or "file"

    @classmethod
    def generate_storage_key(cls, business_id: uuid.UUID, folder: str, filename: str) -> str:
        """Generates tenant-isolated storage key: tenants/{business_id}/{folder}/{uuid}_{filename}."""
        safe_name = cls.sanitize_filename(filename)
        unique_prefix = uuid.uuid4().hex[:12]
        safe_folder = cls.sanitize_filename(folder)
        return f"tenants/{business_id}/{safe_folder}/{unique_prefix}_{safe_name}"

    @classmethod
    def generate_presigned_upload(
        cls,
        business_id: uuid.UUID,
        filename: str,
        content_type: str,
        folder: str = "products",
    ) -> Dict[str, str]:
        """
        Generates a presigned PUT URL allowing clients to upload directly to R2.
        If R2 is not configured, provides a direct backend upload fallback endpoint.
        """
        if content_type.lower() not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{content_type}'. Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
            )

        key = cls.generate_storage_key(business_id, folder, filename)

        if cls.is_r2_configured():
            try:
                s3 = cls.get_s3_client()
                upload_url = s3.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={
                        "Bucket": settings.R2_BUCKET_NAME,
                        "Key": key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=3600,
                )
                public_cdn = (
                    f"{settings.R2_PUBLIC_URL.rstrip('/')}/{key}"
                    if settings.R2_PUBLIC_URL
                    else f"https://{settings.R2_BUCKET_NAME}.r2.dev/{key}"
                )
                return {"upload_url": upload_url, "public_url": public_cdn, "key": key}
            except Exception as e:
                logger.error(f"Error generating R2 presigned URL: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate storage upload URL",
                )

        # Local fallback endpoint
        fallback_upload = f"/api/v1/businesses/{business_id}/media/upload"
        fallback_public = f"/api/v1/media/local/{key}"
        return {"upload_url": fallback_upload, "public_url": fallback_public, "key": key}

    @classmethod
    def upload_file_bytes(
        cls,
        business_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        folder: str = "products",
    ) -> Dict[str, Any]:
        """
        Uploads file bytes directly to Cloudflare R2 or local directory storage.
        """
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
            )

        if content_type.lower() not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{content_type}'",
            )

        key = cls.generate_storage_key(business_id, folder, filename)

        if cls.is_r2_configured():
            try:
                s3 = cls.get_s3_client()
                s3.put_object(
                    Bucket=settings.R2_BUCKET_NAME,
                    Key=key,
                    Body=file_bytes,
                    ContentType=content_type,
                )
                public_url = (
                    f"{settings.R2_PUBLIC_URL.rstrip('/')}/{key}"
                    if settings.R2_PUBLIC_URL
                    else f"https://{settings.R2_BUCKET_NAME}.r2.dev/{key}"
                )
                return {
                    "key": key,
                    "url": public_url,
                    "filename": filename,
                    "content_type": content_type,
                    "size_bytes": len(file_bytes),
                }
            except Exception as e:
                logger.error(f"R2 upload failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Cloud storage upload failed",
                )

        # Local storage mode (dev/test)
        base_dir = Path("uploads") / "tenants" / str(business_id) / folder
        base_dir.mkdir(parents=True, exist_ok=True)
        safe_name = cls.sanitize_filename(filename)
        unique_name = f"{uuid.uuid4().hex[:12]}_{safe_name}"
        file_path = base_dir / unique_name

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        local_key = f"tenants/{business_id}/{folder}/{unique_name}"
        local_url = f"/api/v1/media/local/{local_key}"

        return {
            "key": local_key,
            "url": local_url,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(file_bytes),
        }

    @classmethod
    async def download_and_store_meta_media(
        cls,
        business_id: uuid.UUID,
        media_id: str,
        access_token: str,
        expected_mime_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches an inbound media asset from Meta WhatsApp Cloud API and stores it in R2 / local store.
        """
        graph_url = f"https://graph.facebook.com/{settings.META_WHATSAPP_API_VERSION}/{media_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 1. Fetch media download URL from Graph API
                meta_res = await client.get(graph_url, headers=headers)
                if meta_res.status_code != 200:
                    logger.error(f"Meta Graph API media lookup failed for {media_id}: {meta_res.text}")
                    return None

                media_data = meta_res.json()
                download_url = media_data.get("url")
                mime_type = media_data.get("mime_type") or expected_mime_type or "image/jpeg"

                if not download_url:
                    return None

                # 2. Download binary media bytes
                binary_res = await client.get(download_url, headers=headers)
                if binary_res.status_code != 200:
                    logger.error(f"Failed downloading binary from Meta CDN: {binary_res.status_code}")
                    return None

                file_bytes = binary_res.content

                # Determine extension
                ext = "bin"
                if "jpeg" in mime_type or "jpg" in mime_type:
                    ext = "jpg"
                elif "png" in mime_type:
                    ext = "png"
                elif "webp" in mime_type:
                    ext = "webp"
                elif "pdf" in mime_type:
                    ext = "pdf"
                elif "ogg" in mime_type:
                    ext = "ogg"
                elif "mp4" in mime_type:
                    ext = "mp4"

                filename = f"whatsapp_{media_id}.{ext}"

                return cls.upload_file_bytes(
                    business_id=business_id,
                    file_bytes=file_bytes,
                    filename=filename,
                    content_type=mime_type,
                    folder="whatsapp",
                )
        except Exception as e:
            logger.error(f"Error ingesting WhatsApp media {media_id}: {e}", exc_info=True)
            return None

    @classmethod
    def delete_file(cls, key: str) -> bool:
        """Deletes file from R2 or local storage."""
        if cls.is_r2_configured():
            try:
                s3 = cls.get_s3_client()
                s3.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
                return True
            except ClientError as e:
                logger.error(f"R2 delete failed for {key}: {e}")
                return False

        # Local delete
        local_path = Path("uploads") / key
        if local_path.exists():
            try:
                os.remove(local_path)
                return True
            except OSError as e:
                logger.error(f"Local file delete failed for {key}: {e}")
                return False
        return False

import uuid
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseSchema


class PresignedUploadRequest(BaseSchema):
    """Request payload to obtain a direct-to-R2 presigned upload URL."""

    filename: str = Field(..., min_length=1, max_length=255, description="Original name of the file")
    content_type: str = Field(..., min_length=3, max_length=128, description="MIME type e.g. image/jpeg")
    folder: str = Field(default="products", description="Folder classification: products, whatsapp, or documents")


class PresignedUploadResponse(BaseSchema):
    """Presigned PUT URL allowing browser/client zero-egress uploads directly to R2."""

    upload_url: str = Field(..., description="Presigned HTTP PUT upload endpoint")
    public_url: str = Field(..., description="Target public CDN URL once uploaded")
    key: str = Field(..., description="Storage key / path in bucket")


class MediaUploadResponse(BaseSchema):
    """Metadata response for an uploaded file."""

    key: str = Field(..., description="Storage key inside bucket or local store")
    url: str = Field(..., description="Publicly accessible CDN or endpoint URL")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="Detected MIME content type")
    size_bytes: int = Field(..., description="File size in bytes")

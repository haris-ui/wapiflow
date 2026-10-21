import os
import uuid
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.dependencies import TenantContext, get_tenant_context, require_role
from app.schemas.media import MediaUploadResponse, PresignedUploadRequest, PresignedUploadResponse
from app.services.storage_service import StorageService

router = APIRouter(tags=["Media & Storage"])


@router.post(
    "/businesses/{business_id}/media/presigned",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate presigned upload URL for direct-to-R2 zero egress upload",
)
async def generate_presigned_url(
    business_id: uuid.UUID,
    payload: PresignedUploadRequest,
    tenant: TenantContext = Depends(require_role(["owner", "manager", "staff"])),
) -> PresignedUploadResponse:
    """Generate a presigned PUT URL allowing clients to upload directly to R2 bucket."""
    res = StorageService.generate_presigned_upload(
        business_id=tenant.business_id,
        filename=payload.filename,
        content_type=payload.content_type,
        folder=payload.folder,
    )
    return PresignedUploadResponse(**res)


@router.post(
    "/businesses/{business_id}/media/upload",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Direct multipart file upload to storage",
)
async def upload_media_file(
    business_id: uuid.UUID,
    file: UploadFile = File(..., description="Binary file (JPEG, PNG, WebP, PDF)"),
    folder: str = Form(default="products"),
    tenant: TenantContext = Depends(require_role(["owner", "manager", "staff"])),
) -> MediaUploadResponse:
    """Uploads file to Cloudflare R2 or local directory storage with strict tenant path isolation."""
    file_bytes = await file.read()
    filename = file.filename or "upload.bin"
    content_type = file.content_type or "application/octet-stream"

    res = StorageService.upload_file_bytes(
        business_id=tenant.business_id,
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        folder=folder,
    )
    return MediaUploadResponse(**res)


@router.delete(
    "/businesses/{business_id}/media",
    status_code=status.HTTP_200_OK,
    summary="Delete a stored media file",
)
async def delete_media_file(
    business_id: uuid.UUID,
    key: str = Query(..., description="Storage key to delete"),
    tenant: TenantContext = Depends(require_role(["owner", "manager"])),
) -> Dict[str, str]:
    """Delete file ensuring strict tenant isolation (cannot delete files belonging to other businesses)."""
    expected_prefix = f"tenants/{tenant.business_id}/"
    if not key.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete media assets outside your tenant boundary",
        )

    deleted = StorageService.delete_file(key)
    return {"status": "ok", "deleted": str(deleted)}


@router.get(
    "/media/local/{file_path:path}",
    summary="Serve locally stored development media files",
    include_in_schema=False,
)
async def serve_local_media(file_path: str):
    """Fallback handler to serve media files when running locally without R2 credentials."""
    safe_path = Path("uploads") / file_path
    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(safe_path)

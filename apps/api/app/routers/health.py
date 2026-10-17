from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", response_model=Dict[str, str])
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Service health check endpoint.
    Verifies database connectivity and reports application runtime status.
    """
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }

import logging
import sys
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import engine
from app.middleware.logging import LoggingAndRequestIdMiddleware
from app.middleware.tenant import TenantContextMiddleware
from app.routers.auth import router as auth_router
from app.routers.businesses import router as businesses_router
from app.routers.customers import router as customers_router
from app.routers.health import router as health_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router
from app.routers.webhooks import router as webhooks_router
from app.routers.whatsapp import router as whatsapp_router
from app.routers.conversations import router as conversations_router
from app.routers.media import router as media_router
from app.routers.team import router as team_router

settings = get_settings()

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("wapiflow.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and graceful shutdown."""
    logger.info("Initializing WapiFlow API v1.0.0...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")

    yield

    logger.info("Shutting down WapiFlow API. Disposing database engine...")
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="WapiFlow API",
    description="Turn WhatsApp conversations into business operations. Multi-tenant SaaS API.",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# 1. Logging and Correlation ID Middleware
app.add_middleware(LoggingAndRequestIdMiddleware)

# 2. Tenant Context Middleware (JWT parsing)
app.add_middleware(TenantContextMiddleware)

# 3. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# Global Exception Handlers — Never leak raw stack traces to clients
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.warning(
        f"[{request_id}] HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Request-ID": request_id, **(exc.headers or {})},
        content={
            "error": "HTTP_ERROR",
            "message": str(exc.detail),
            "request_id": request_id,
            "details": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.warning(
        f"[{request_id}] Validation error on {request.method} {request.url.path}: {exc.errors()}"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        headers={"X-Request-ID": request_id},
        content={
            "error": "VALIDATION_ERROR",
            "message": "Input validation failed. Please check your request parameters.",
            "request_id": request_id,
            "details": exc.errors(),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(
        f"[{request_id}] Database transaction error on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"X-Request-ID": request_id},
        content={
            "error": "DATABASE_ERROR",
            "message": "A database error occurred. The transaction was rolled back.",
            "request_id": request_id,
            "details": None,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(
        f"[{request_id}] Unhandled server exception on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"X-Request-ID": request_id},
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Our engineering team has been notified.",
            "request_id": request_id,
            "details": None,
        },
    )


# Root Health Check
app.include_router(health_router)

# Versioned API Routes under /api/v1
API_V1_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_V1_PREFIX)
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(businesses_router, prefix=API_V1_PREFIX)
app.include_router(products_router, prefix=API_V1_PREFIX)
app.include_router(orders_router, prefix=API_V1_PREFIX)
app.include_router(customers_router, prefix=API_V1_PREFIX)
app.include_router(webhooks_router, prefix=API_V1_PREFIX)
app.include_router(whatsapp_router, prefix=API_V1_PREFIX)
app.include_router(conversations_router, prefix=API_V1_PREFIX)
app.include_router(team_router, prefix=API_V1_PREFIX)
app.include_router(media_router, prefix=API_V1_PREFIX)

# WapiFlow — FastAPI Backend Service

Production-ready backend API service for **WapiFlow** ("Turn WhatsApp conversations into business operations").

## Tech Stack
- **Framework**: FastAPI (Python 3.13)
- **Database & ORM**: PostgreSQL via AsyncPG + SQLAlchemy 2.0 (Async) + Alembic
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Authentication**: Supabase Auth JWT verification & local RBAC
- **Queue/Worker**: ARQ (Redis)
- **Object Storage**: Cloudflare R2 (S3-compatible)
- **Messaging**: Meta WhatsApp Cloud API (v19.0)

---

## Core Architecture & Security Principles
1. **Strict Multi-Tenancy**: Every business operation is isolated by `business_id`. The `get_tenant_context` dependency verifies user membership in the specified business on every protected route.
2. **PII Masking**: Customer phone numbers are automatically redacted in structured access logs to comply with privacy regulations.
3. **Idempotency Guarantee**: Order creation supports `idempotency_key` per tenant to prevent duplicate charges or duplicate order records.
4. **Resilient Error Responses**: Stack traces are never leaked in client responses; all exceptions are logged internally with correlation IDs and returned as formatted `ErrorResponse` objects.

---

## Directory Structure
```
apps/api/
├── main.py                     # FastAPI application entrypoint with lifespan & middleware
├── pyproject.toml              # Project dependencies & pytest configuration
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development & testing dependencies
├── Dockerfile                  # Production container definition
├── alembic.ini                 # Database migrations configuration
├── alembic/
│   ├── env.py                  # Async Alembic execution environment
│   └── versions/
│       └── 001_initial_schema.py # Initial database migration
├── app/
│   ├── config.py               # Pydantic-settings environment configuration
│   ├── database.py             # Async SQLAlchemy engine & session factory
│   ├── dependencies.py         # Tenant isolation & security dependencies
│   ├── middleware/
│   │   ├── logging.py          # Structured logging & PII redaction
│   │   └── tenant.py           # JWT token parser
│   ├── models/                 # SQLAlchemy 2.0 ORM models
│   │   ├── base.py
│   │   ├── profile.py
│   │   ├── business.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── customer.py
│   │   └── whatsapp.py
│   ├── schemas/                # Pydantic v2 request/response models
│   │   ├── common.py
│   │   ├── auth.py
│   │   ├── business.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── customer.py
│   ├── routers/                # API route handlers
│   │   ├── health.py
│   │   ├── auth.py
│   │   ├── businesses.py
│   │   ├── products.py
│   │   ├── orders.py
│   │   └── customers.py
│   └── services/               # Transactional business logic
│       ├── auth_service.py
│       ├── business_service.py
│       ├── product_service.py
│       ├── order_service.py
│       └── customer_service.py
└── tests/                      # Automated test suite
    ├── conftest.py             # Async database & client fixtures
    ├── test_health.py
    ├── test_auth.py
    ├── test_products.py
    ├── test_orders.py
    └── test_tenant_isolation.py # Strict multi-tenant isolation tests
```

---

## Getting Started

### 1. Environment Setup
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

### 2. Database Migrations
```bash
alembic upgrade head
```

### 3. Run Development Server
```bash
uvicorn main:app --reload --port 8000
```
Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Running the Automated Test Suite
```bash
pytest -v
```
All tests run with in-memory SQLite (`aiosqlite`) and require zero external services.

---

## Manual Setup Steps

### 1. Supabase Configuration
1. Go to your Supabase Project Settings -> API.
2. Copy `Project URL`, `anon public` key, and `service_role` secret to your `.env`.
3. In Project Settings -> API -> JWT Settings, copy your `JWT Secret` and paste it into `SUPABASE_JWT_SECRET` in `.env`.

### 2. Meta WhatsApp Cloud API Setup
1. In Meta for Developers dashboard, create a WhatsApp App.
2. Obtain your `Phone Number ID` and `WhatsApp Business Account ID (WABA ID)`.
3. Generate a permanent System User Access Token with `whatsapp_business_messaging` permissions.
4. Set Webhook URL to: `https://<YOUR_DOMAIN>/api/v1/whatsapp/webhook`
5. Configure `META_VERIFY_TOKEN` and verify the webhook in Meta dashboard.

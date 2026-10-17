# WapiFlow

> **"Turn WhatsApp conversations into business operations"**

WapiFlow is a production-grade multi-tenant B2B SaaS platform that unifies WhatsApp Cloud API messaging with back-office operations: customer CRM, automated catalog ordering, conversational sales workflows, payment links, and fulfillment tracking.

---

## 🚀 Tech Stack

| Domain | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | React 18, Vite 5, TypeScript 5, Tailwind CSS 3, Shadcn/ui, TanStack Query | Responsive operator dashboard, real-time inbox, order workbench |
| **Backend** | FastAPI, Python 3.13, Pydantic v2, ARQ (Async Redis Queue), HTTPX | High-throughput asynchronous REST API and webhook ingestion engine |
| **Database & Auth** | Supabase (PostgreSQL 16), Supabase Auth | Multi-tenant relational schema enforced strictly by Row-Level Security (RLS) |
| **Cache & Queue** | Redis 7 | Distributed job queuing, rate limiting, and ephemeral idempotency tracking |
| **Object Storage** | Cloudflare R2 | S3-compatible, zero-egress storage for invoices, receipts, and media |
| **WhatsApp Engine** | Meta WhatsApp Cloud API (Graph API v20.0) | Official business messaging, interactive templates, media messaging |
| **Notifications** | Resend | Transactional email delivery for orders, invites, and system alerts |
| **Observability** | Sentry | Distributed tracing and error reporting across frontend and backend |

---

## 🏛 Architecture Highlights

- **Multi-Tenancy with Row-Level Security (RLS)**: Every single table includes a `tenant_id` column. Tenant boundaries are enforced at the PostgreSQL database level using session context and Supabase Auth JWT claims, guaranteeing zero data leakage across organizations.
- **FastAPI Tenant Context Middleware**: Inbound requests validate Bearer JWT tokens, extract the authenticated `tenant_id`, and inject an isolated tenant context into dependency injection scopes.
- **Strict Webhook Security**: All incoming Meta WhatsApp Cloud API payloads are validated against `X-Hub-Signature-256` using HMAC-SHA256 before ingestion into ARQ background queues.
- **Privacy & PII Protection**: Phone numbers and customer credentials are treated as sensitive PII. Backend logs strictly mask phone numbers (e.g. `+1 *** *** 4821`), and raw database error strings are never returned to public API callers.
- **Non-blocking Asynchronous Operations**: 100% async pipeline from HTTP handlers down to `asyncpg` queries and ARQ task dispatching.

---

## 📁 Repository Structure

```text
WSAAS/
├── .env.example              # Environment variables blueprint for all services
├── .gitignore                # Comprehensive ignore rules for Node, Python, caches
├── docker-compose.yml        # Local development infrastructure (Postgres, Redis, pgAdmin)
├── Makefile                  # Developer ergonomics (install, dev, test, lint, migrate, build)
├── README.md                 # Project documentation and getting started guide
├── apps/
│   ├── api/                  # FastAPI backend service (Python 3.13)
│   │   ├── app/              # Application source (routers, services, models, middleware)
│   │   ├── tests/            # Pytest test suite (unit and integration tests)
│   │   └── requirements.txt  # Python package dependencies
│   └── web/                  # React dashboard frontend (Vite + TypeScript)
│       ├── src/              # React components, hooks, stores, pages, lib
│       ├── package.json      # Node dependencies and scripts
│       └── vite.config.ts    # Vite bundler configuration
├── packages/
│   └── database/             # Supabase schema definitions and versioned migrations
│       └── migrations/       # Idempotent SQL migration files
└── docs/                     # Production architectural & operational documentation
    ├── ARCHITECTURE.md       # Detailed system design, data flow diagrams, isolation model
    ├── SECURITY.md           # Threat model, RLS rules, PII protection, secret rotation
    ├── COSTS_AND_LIMITS.md   # Cloud provider free tiers, quotas, and optimization
    ├── WHATSAPP_SETUP.md     # Step-by-step Meta Cloud API setup & webhook verification
    ├── DEPLOYMENT.md         # Deployment runbooks for staging and production
    ├── API.md                # REST API conventions, error envelopes, pagination
    ├── TESTING.md            # Testing strategy, pytest, vitest, and testcontainers
    ├── DATABASE.md           # Entity relationship model, indexing, and migration rules
    ├── OPERATIONS.md         # Monitoring, logging standards, alerting, incident response
    └── BACKUPS_AND_RECOVERY.md # Backup schedule, WAL-G, Point-In-Time recovery runbook
```

---

## ⚡ Prerequisites

Ensure you have the following installed locally:

- **Docker Desktop** (Engine 24+)
- **Python** (version 3.13 or higher)
- **Node.js** (version 20 LTS or higher) and `npm` (version 10+)
- **Git**

---

## 🛠 Local Development Setup

### 1. Environment Configuration

Clone the repository and copy the environment configuration template:

```bash
cp .env.example .env
```

Review `.env` and fill in necessary configuration options. For local development with Docker, the default values for Redis and Postgres can be used directly.

### 2. Launch Local Infrastructure

Start the local PostgreSQL, Redis, and pgAdmin containers:

```bash
docker compose up -d
```

Verify service status:
- **PostgreSQL**: `localhost:5432` (`user: postgres`, `password: postgres`, `db: wapiflow`)
- **Redis**: `localhost:6379`
- **pgAdmin 4**: [http://localhost:5050](http://localhost:5050) (`admin@wapiflow.local` / `admin1234`)

### 3. Backend Setup (FastAPI)

Navigate to the API directory, create and activate a Python virtual environment:

```bash
cd apps/api
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Install dependencies:
pip install -r requirements.txt
```

Run database migrations:

```bash
# Apply pending migrations
make migrate
```

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The interactive API documentation is accessible at [http://localhost:8000/docs](http://localhost:8000/docs).

### 4. Frontend Setup (React + Vite)

In a new terminal window, navigate to the web directory and install dependencies:

```bash
cd apps/web
npm install
npm run dev
```

The operator dashboard will be available at [http://localhost:5173](http://localhost:5173).

---

## 📋 Common Commands

The included `Makefile` provides standardized targets for all standard developer workflows:

| Command | Action |
| :--- | :--- |
| `make install` | Installs dependencies for both backend (Python) and frontend (Node). |
| `make dev` | Starts Docker services and prints commands for starting servers. |
| `make dev-backend` | Starts the FastAPI application with live code reloading on port `8000`. |
| `make dev-frontend`| Starts the Vite development server on port `5173`. |
| `make test` | Executes both backend `pytest` suite and frontend `vitest` tests. |
| `make lint` | Validates formatting and types via `ruff`, `black`, `mypy`, `eslint`, and `tsc`. |
| `make migrate` | Applies pending database migrations. |
| `make build` | Compiles frontend assets and verifies production distribution viability. |
| `make docker-up` | Starts local PostgreSQL, Redis, and pgAdmin containers in the background. |
| `make docker-down`| Stops and removes local Docker containers. |
| `make clean` | Cleans temporary cache directories, pycache, and build outputs. |

---

## 📚 Documentation Directory

Explore the complete system specification and operational runbooks:

- 🏗 [Architecture & System Design](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/ARCHITECTURE.md)
- 🔒 [Security & Threat Model](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/SECURITY.md)
- 💰 [Cloud Limits & Free-Tier Economics](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/COSTS_AND_LIMITS.md)
- 💬 [WhatsApp Cloud API Integration Guide](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/WHATSAPP_SETUP.md)
- 🚢 [Deployment Guide](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/DEPLOYMENT.md)
- 🔌 [API Design & Conventions](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/API.md)
- 🧪 [Testing Strategy & Execution](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/TESTING.md)
- 🗄 [Database Schema & RLS Policies](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/DATABASE.md)
- 📊 [Operations & Observability](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/OPERATIONS.md)
- 💾 [Backups & Disaster Recovery](file:///C:/Users/HaRIS/Desktop/University/Game/WSAAS/docs/BACKUPS_AND_RECOVERY.md)

---

## 📄 License

Proprietary — All rights reserved. Built for WapiFlow enterprise multi-tenant operations.

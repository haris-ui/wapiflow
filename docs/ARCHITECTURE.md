# System Architecture & Technical Design

## 1. System Overview

WapiFlow is designed as a high-concurrency, multi-tenant B2B platform that bridges conversational messaging over Meta's WhatsApp Cloud API with operational workflows: product catalog browsing, checkout sessions, order placement, conversational customer support, and automated status notifications.

The architecture prioritizes:
- **Strict Data Isolation**: Multi-tenancy enforced at the database layer using PostgreSQL Row-Level Security (RLS) coupled with application-level context boundaries.
- **Asynchronous Reliability**: Sub-100ms webhook ingestion decoupled from heavy business logic and external API calls via an asynchronous Redis worker queue (ARQ).
- **Stateless Application Layer**: FastAPI stateless backend containers that can scale horizontally behind a load balancer.
- **Zero-Egress Media Pipeline**: Media attachments (images, PDF invoices, audio notes) stream directly between the client, Cloudflare R2, and WhatsApp Cloud API.

---

## 2. Component Architecture

```text
+--------------------------------------------------------------------------------------------------+
|                                        CLIENT TIER                                               |
|                                                                                                  |
|   +------------------------------------+          +------------------------------------------+   |
|   |   Operator Dashboard (React 18)   |          |      WhatsApp Mobile App (Customers)     |   |
|   |   - Vite 5 + TypeScript            |          |      - End-user WhatsApp interface       |   |
|   |   - TanStack Query v5              |          |      - Interactive Messages, Buttons     |   |
|   |   - Tailwind CSS + Shadcn/ui       |          |      - Flow Forms, Catalogs, Media       |   |
|   +-----------------+------------------+          +--------------------+---------------------+   |
+---------------------|--------------------------------------------------|-------------------------+
                      | HTTPS / WSS                                      | HTTPS (Meta Webhooks)
                      v                                                  v
+--------------------------------------------------------------------------------------------------+
|                                    INGRESS & GATEWAY TIER                                        |
|                                                                                                  |
|   Cloudflare Edge (WAF, SSL/TLS Termination, DDoS Shield, Rate Limiting, DNS)                    |
+---------------------+--------------------------------------------------+-------------------------+
                      |                                                  |
                      v                                                  v
+--------------------------------------------------------------------------------------------------+
|                                    APPLICATION API TIER                                          |
|                                                                                                  |
|   FastAPI Stateless Engine (Python 3.13, ASGI / Uvicorn)                                         |
|   +------------------------------------+          +------------------------------------------+   |
|   |   Tenant Context Middleware        |          |   WhatsApp Webhook Controller            |   |
|   |   - Validates Supabase JWT         |          |   - Verifies HMAC-SHA256 signature       |   |
|   |   - Injects TenantContext into DI  |          |   - Returns 200 OK immediately (<50ms)  |   |
|   |   - Enforces scope & RBAC          |          |   - Enqueues job to ARQ / Redis          |   |
|   +-----------------+------------------+          +--------------------+---------------------+   |
|                     |                                                  |                         |
|   +-----------------v--------------------------------------------------v---------------------+   |
|   |   Service Layer (Business Logic)                                                          |   |
|   |   - Order Engine (State machines, inventory locking, pricing, tax calculations)          |   |
|   |   - Conversation Manager (Chat threads, SLA timers, routing to team members)             |   |
|   |   - Catalog Service (Products, variants, stock synchronization)                          |   |
|   |   - Notification Dispatcher (WhatsApp template rendering, Resend email notices)          |   |
|   +-----------------+--------------------------------------------------+---------------------+   |
+---------------------|--------------------------------------------------|-------------------------+
                      |                                                  |
                      v                                                  v
+-------------------------------------------------+  +---------------------------------------------+
|               DATA STORAGE TIER                 |  |             ASYNC WORKER TIER               |
|                                                 |  |                                             |
|  Supabase PostgreSQL 16                         |  |  ARQ Worker Pool (Python 3.13)              |
|  +-------------------------------------------+  |  |  +---------------------------------------+  |
|  | Multi-Tenant Relational Database          |  |  |  | - Webhook payload processor           |  |
|  | - Row-Level Security (RLS) on all tables  |  |  |  | - WhatsApp message dispatcher         |  |
|  | - Connection pooling (PgBouncer/Supavisor)|  |  |  | - Media downloader & R2 uploader     |  |
|  | - Realtime replication engine             |  |  |  | - SLA monitor & automated escalations |  |
|  +-------------------------------------------+  |  |  +-------------------+-------------------+  |
|                                                 |  |                      |                      |
|  Cloudflare R2 Object Storage                   |  |  Redis 7 (In-Memory Broker)                 |
|  +-------------------------------------------+  |  |  +---------------------------------------+  |
|  | - S3-compatible media store (Zero egress) |  |  |  | - Priority job queues                 |  |
|  | - Tenant path isolation:                  |  |  |  | - Rate-limiting sliding windows       |  |
|  |   /tenants/{tenant_id}/...                |  |  |  | - Webhook deduplication store (TTL)   |  |
|  +-------------------------------------------+  |  +--+---------------------------------------+  |
+-------------------------------------------------+
```

---

## 3. Data Flow Diagrams

### 3.1 Inbound WhatsApp Message to Order Flow

```text
[Customer WhatsApp]
       |
       | 1. Sends message / clicks catalog order
       v
[Meta WhatsApp Cloud API]
       |
       | 2. HTTP POST Webhook payload with X-Hub-Signature-256
       v
[FastAPI: /api/v1/webhooks/whatsapp]
       |
       | 3. Verify HMAC-SHA256 signature with META_APP_SECRET
       | 4. Extract WABA ID & Phone Number ID -> Lookup Tenant ID in cache
       | 5. Return HTTP 200 OK to Meta immediately
       v
[Redis Queue: arq:queue]
       |
       | 6. Dequeue task: process_incoming_whatsapp_message(payload, tenant_id)
       v
[ARQ Background Worker]
       |
       | 7. Deduplicate using message_id with 24h Redis TTL
       | 8. Mask PII for logger (e.g., +1 *** *** 4821)
       | 9. Set DB session context: set_config('app.current_tenant_id', tenant_id)
       |
       +---> [Supabase PostgreSQL (RLS Enforced)]
       |     - Upsert Customer record (phone_number, name)
       |     - Append to Conversation thread
       |     - Record Message entity
       |     - If Order payload: Create Order & OrderItems in PENDING state
       |
       +---> [Cloudflare R2]
       |     - If Media (voice, image, document): download from Meta URL, upload to R2
       |
       +---> [Meta WhatsApp Cloud API]
             - Dispatch automated confirmation / interactive reply button
```

### 3.2 Outbound Operator Message / Template Flow

```text
[Operator on React Dashboard]
       |
       | 1. Submit message / template trigger via HTTPS
       |    Authorization: Bearer <Supabase_JWT>
       v
[FastAPI: /api/v1/conversations/{id}/messages]
       |
       | 2. TenantContextMiddleware verifies JWT & extracts tenant_id
       | 3. Authorize operator permissions via RLS and DB policy
       | 4. Check 24-hour customer service window status
       |
       +--- If within 24h window: Freeform session text/media allowed
       +--- If outside 24h window: Must use approved WhatsApp Template
       |
       | 5. Persist message record to PostgreSQL (status: 'queued')
       | 6. Dispatch ARQ task: send_whatsapp_message(message_id, tenant_id)
       v
[ARQ Worker]
       |
       | 7. Call Meta Graph API: POST https://graph.facebook.com/v20.0/{phone_number_id}/messages
       | 8. On success: Update message status to 'sent' and record Meta WAMID
       | 9. Push Realtime update via Supabase to Operator Dashboard
```

---

## 4. Tenant Isolation Strategy

WapiFlow adopts a **Shared-Database, Shared-Schema Multi-Tenancy Architecture** with hardware-level cryptographic and relational enforcement. This delivers significant cost efficiency and streamlined operational maintenance while upholding enterprise data isolation.

### 4.1 Tenancy Enforcement Guarantees

1. **Mandatory `tenant_id` Primary Column**:
   Every domain table in the database schema (`customers`, `conversations`, `messages`, `products`, `orders`, `order_items`, `webhook_events`, `audit_logs`) includes a `tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE`.

2. **Database-Level Row-Level Security (RLS)**:
   PostgreSQL RLS is permanently active on all tables. Queries cannot execute across tenant boundaries, even if an application bug omits a `WHERE tenant_id = ...` clause.

   ```sql
   ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
   ALTER TABLE orders FORCE ROW LEVEL SECURITY;

   CREATE POLICY tenant_isolation_orders ON orders
       FOR ALL
       USING (
           tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
           OR
           tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
       );
   ```

3. **FastAPI Request Context Middleware**:
   Every API request passes through `TenantContextMiddleware`:
   - Validates the bearer token issued by Supabase Auth.
   - Extracts the verified `tenant_id` claim from `app_metadata`.
   - Injects a typed `TenantContext` object into the request state and FastAPI dependency container.
   - When a database session is acquired, the middleware sets the transaction-local configuration:
     ```python
     await db.execute("SET LOCAL app.current_tenant_id = :tenant_id", {"tenant_id": str(tenant_id)})
     ```

4. **Background Worker Tenant Encapsulation**:
   Every message enqueued into Redis includes the explicit `tenant_id`. When an ARQ worker picks up the job, it initializes a dedicated scoped database session with `SET LOCAL app.current_tenant_id` applied before executing domain logic.

5. **Storage Isolation**:
   Cloudflare R2 storage paths strictly adhere to tenant folder namespaces:
   ```text
   wapiflow-media-production/
   └── tenants/
       └── {tenant_id}/
           ├── orders/{order_id}/invoices/
           ├── media/{message_id}/
           └── catalog/{product_id}/
   ```
   Pre-signed URLs are generated with short-lived expirations (15 minutes) and scoped explicitly to the tenant's namespace.

---

## 5. High Availability & Scalability Tactics

| Concern | Strategy |
| :--- | :--- |
| **Meta Webhook Bursts** | Fast-path ingestion responds with HTTP 200 within 50ms and writes raw payloads to Redis queues. Background workers absorb traffic spikes without stalling Meta's webhook delivery. |
| **Rate Limit Protection** | Redis-backed sliding window rate limiters prevent exceeding Meta's Cloud API limits (80 MPS to 1,000 MPS depending on tier). |
| **Database Connection Pooling** | Supabase Supavisor connection pooler handles thousands of concurrent client connections over transaction mode, preventing PostgreSQL connection exhaustion. |
| **Idempotency** | Inbound webhook events are deduplicated in Redis via a `SETNX` key (`whatsapp:event:{wam_id}`) with a 24-hour TTL to prevent double-processing. |

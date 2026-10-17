# Database Schema & Entity Relationships

WapiFlow uses PostgreSQL 16 hosted on Supabase, designed from the ground up for strict multi-tenant isolation, high-throughput message ingestion, and relational consistency.

---

## 1. Entity-Relationship Diagram (ERD)

```text
+---------------------+
|       tenants       |
+---------------------+
| PK  id              |<-------+
|     name            |        |
|     slug            |        |
|     status          |        |
|     waba_id         |        |
|     phone_number_id |        |
|     created_at      |        |
+---------------------+        |
        |                      |
        | 1:N                  |
        v                      |
+---------------------+        |
|   tenant_members    |        |
+---------------------+        |
| PK  id              |        |
| FK  tenant_id       |--------+
| FK  user_id (auth)  |        |
|     role            |        |
|     created_at      |        |
+---------------------+        |
        |                      |
        | 1:N                  |
        v                      |
+---------------------+        |
|      customers      |        |
+---------------------+        |
| PK  id              |        |
| FK  tenant_id       |--------+
|     wa_id           |        |
|     phone_number    |        |
|     display_name    |        |
|     created_at      |        |
+---------------------+        |
        |                      |
        | 1:N                  |
        v                      |
+---------------------+        |        +---------------------+
|    conversations    |        |        |      products       |
+---------------------+        |        +---------------------+
| PK  id              |        |        | PK  id              |
| FK  tenant_id       |--------+        | FK  tenant_id       |---+
| FK  customer_id     |        |        |     sku             |   |
|     status          |        |        |     title           |   |
|     window_expires  |        |        |     price           |   |
|     assigned_to     |        |        |     stock_quantity  |   |
+---------------------+        |        +---------------------+   |
        |                      |                   |              |
        | 1:N                  |                   | 1:N          |
        v                      |                   v              |
+---------------------+        |        +---------------------+   |
|      messages       |        |        |     order_items     |   |
+---------------------+        |        +---------------------+   |
| PK  id              |        |        | PK  id              |   |
| FK  tenant_id       |--------+        | FK  tenant_id       |---+
| FK  conversation_id |        |        | FK  order_id        |   |
|     wamid           |        |   +--->| FK  product_id      |   |
|     direction       |        |   |    |     quantity        |   |
|     type            |        |   |    |     unit_price      |   |
|     status          |        |   |    +---------------------+   |
+---------------------+        |   |               ^              |
                               |   |               |              |
+---------------------+        |   |               | N:1          |
|       orders        |        |   |               |              |
+---------------------+        |   |               |              |
| PK  id              |        |   |               |              |
| FK  tenant_id       |--------+   |               |              |
| FK  customer_id     |            |               |              |
| FK  conversation_id |------------+---------------+              |
|     order_number    |                                           |
|     status          |                                           |
|     total_amount    |                                           |
+---------------------+                                           |
                                                                  |
+---------------------+        +---------------------+            |
|   webhook_events    |        |     audit_logs      |            |
+---------------------+        +---------------------+            |
| PK  id              |        | PK  id              |            |
| FK  tenant_id       |--------| FK  tenant_id       |------------+
|     event_type      |        | FK  user_id         |
|     status          |        |     action          |
|     payload         |        |     resource_type   |
|     created_at      |        |     resource_id     |
+---------------------+        +---------------------+
```

---

## 2. Table Specifications & Indexes

### 2.1 `tenants`
The central multi-tenant container for an organization using WapiFlow.
- `id` (UUID, PK, default `gen_random_uuid()`)
- `name` (TEXT NOT NULL)
- `slug` (VARCHAR(63) NOT NULL UNIQUE)
- `status` (VARCHAR(32) NOT NULL DEFAULT 'active') — `active`, `suspended`, `cancelled`
- `waba_id` (VARCHAR(64)) — Meta WhatsApp Business Account ID
- `phone_number_id` (VARCHAR(64)) — Meta WhatsApp Phone Number ID
- `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())
- `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())

**Indexes**:
- `CREATE UNIQUE INDEX idx_tenants_slug ON tenants(slug);`
- `CREATE INDEX idx_tenants_waba_id ON tenants(waba_id);`
- `CREATE INDEX idx_tenants_phone_number_id ON tenants(phone_number_id);`

---

### 2.2 `tenant_members`
Links Supabase authenticated users (`auth.users`) to specific tenants with RBAC roles.
- `id` (UUID, PK, default `gen_random_uuid()`)
- `tenant_id` (UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE)
- `user_id` (UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE)
- `role` (VARCHAR(32) NOT NULL DEFAULT 'agent') — `owner`, `admin`, `manager`, `agent`
- `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())

**Indexes**:
- `CREATE UNIQUE INDEX idx_tenant_members_tenant_user ON tenant_members(tenant_id, user_id);`
- `CREATE INDEX idx_tenant_members_user_id ON tenant_members(user_id);`

---

### 2.3 `customers`
End-user WhatsApp customers interacting with a tenant's business.
- `id` (UUID, PK, default `gen_random_uuid()`)
- `tenant_id` (UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE)
- `wa_id` (VARCHAR(32) NOT NULL) — WhatsApp User ID (E.164 phone number)
- `phone_number` (VARCHAR(32) NOT NULL)
- `display_name` (TEXT)
- `metadata` (JSONB NOT NULL DEFAULT '{}'::jsonb)
- `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())
- `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())

**Indexes**:
- `CREATE UNIQUE INDEX idx_customers_tenant_wa_id ON customers(tenant_id, wa_id);`
- `CREATE INDEX idx_customers_tenant_created ON customers(tenant_id, created_at DESC);`

---

### 2.4 `conversations`
Chat thread tracking session windows, SLAs, and assigned operators.
- `id` (UUID, PK, default `gen_random_uuid()`)
- `tenant_id` (UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE)
- `customer_id` (UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE)
- `status` (VARCHAR(32) NOT NULL DEFAULT 'open') — `open`, `pending`, `closed`
- `assigned_to` (UUID REFERENCES auth.users(id) ON DELETE SET NULL)
- `last_message_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())
- `window_expires_at` (TIMESTAMPTZ) — Meta 24-hour service conversation expiry
- `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())

**Indexes**:
- `CREATE INDEX idx_conversations_tenant_status ON conversations(tenant_id, status);`
- `CREATE INDEX idx_conversations_tenant_last_msg ON conversations(tenant_id, last_message_at DESC);`
- `CREATE INDEX idx_conversations_customer ON conversations(customer_id);`

---

### 2.5 `messages`
Individual message records (inbound customer messages and outbound operator responses).
- `id` (UUID, PK, default `gen_random_uuid()`)
- `tenant_id` (UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE)
- `conversation_id` (UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE)
- `wamid` (VARCHAR(128)) — Meta WhatsApp Message ID for tracking receipts
- `direction` (VARCHAR(8) NOT NULL) — `inbound` or `outbound`
- `type` (VARCHAR(32) NOT NULL) — `text`, `image`, `audio`, `document`, `interactive`, `order`
- `content` (TEXT)
- `media_url` (TEXT) — Stored Cloudflare R2 path
- `status` (VARCHAR(32) NOT NULL DEFAULT 'received') — `received`, `queued`, `sent`, `delivered`, `read`, `failed`
- `raw_payload` (JSONB)
- `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())

**Indexes**:
- `CREATE INDEX idx_messages_tenant_conversation ON messages(tenant_id, conversation_id, created_at ASC);`
- `CREATE UNIQUE INDEX idx_messages_wamid ON messages(tenant_id, wamid) WHERE wamid IS NOT NULL;`

---

### 2.6 `products`
Tenant catalog items for conversational commerce.
- `id` (UUID, PK, default `gen_random_uuid()`)
- `tenant_id` (UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE)
- `sku` (VARCHAR(64) NOT NULL)
- `title` (TEXT NOT NULL)
- `description` (TEXT)
- `price` (NUMERIC(12, 2) NOT NULL)
- `currency` (VARCHAR(3) NOT NULL DEFAULT 'USD')
- `stock_quantity` (INTEGER NOT NULL DEFAULT 0)
- `image_url` (TEXT)
- `is_active` (BOOLEAN NOT NULL DEFAULT true)
- `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())

**Indexes**:
- `CREATE UNIQUE INDEX idx_products_tenant_sku ON products(tenant_id, sku);`
- `CREATE INDEX idx_products_tenant_active ON products(tenant_id, is_active);`

---

### 2.7 `orders` & `order_items`
Orders created conversational or through WhatsApp catalog checkout.
- `orders`:
  - `id` (UUID, PK, default `gen_random_uuid()`)
  - `tenant_id` (UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE)
  - `customer_id` (UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT)
  - `conversation_id` (UUID REFERENCES conversations(id) ON DELETE SET NULL)
  - `order_number` (VARCHAR(32) NOT NULL)
  - `status` (VARCHAR(32) NOT NULL DEFAULT 'pending') — `pending`, `confirmed`, `paid`, `fulfilled`, `cancelled`
  - `total_amount` (NUMERIC(12, 2) NOT NULL)
  - `currency` (VARCHAR(3) NOT NULL DEFAULT 'USD')
  - `payment_status` (VARCHAR(32) NOT NULL DEFAULT 'unpaid')
  - `payment_url` (TEXT)
  - `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())
  - `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())
- `order_items`:
  - `id` (UUID, PK, default `gen_random_uuid()`)
  - `tenant_id` (UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE)
  - `order_id` (UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE)
  - `product_id` (UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT)
  - `quantity` (INTEGER NOT NULL)
  - `unit_price` (NUMERIC(12, 2) NOT NULL)
  - `subtotal` (NUMERIC(12, 2) NOT NULL)

**Indexes**:
- `CREATE UNIQUE INDEX idx_orders_tenant_number ON orders(tenant_id, order_number);`
- `CREATE INDEX idx_orders_tenant_status ON orders(tenant_id, status);`
- `CREATE INDEX idx_order_items_order ON order_items(order_id);`

---

## 3. Migration Idempotency & Standards

All SQL migration scripts adhere to strict architectural rules:
1. Every migration is versioned: `packages/database/migrations/YYYYMMDDHHMMSS_name.sql`.
2. Every table creation includes `IF NOT EXISTS`.
3. Every trigger or function creation uses `CREATE OR REPLACE FUNCTION` and guards in `DO $$` blocks.
4. Alterations use guarded syntax:
   ```sql
   DO $$
   BEGIN
       IF NOT EXISTS (
           SELECT 1 FROM information_schema.columns 
           WHERE table_name = 'orders' AND column_name = 'payment_url'
       ) THEN
           ALTER TABLE orders ADD COLUMN payment_url TEXT;
       END IF;
   END $$;
   ```
5. Every migration is self-contained and transactional.

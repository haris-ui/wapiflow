# Security Architecture & Threat Model

## 1. Authentication & Authorization Model

WapiFlow enforces a zero-trust, identity-centric access control architecture combining **Supabase Auth (OIDC / JWT)** with **PostgreSQL Row-Level Security (RLS)** and **FastAPI Dependency Injection guards**.

```text
+-------------------+       1. Authenticate with credentials / OAuth
|  Operator Browser | --------------------------------------------------> +--------------------+
+-------------------+                                                     |   Supabase Auth    |
        ^                                                                 +---------+----------+
        |                   2. Issues signed RS256 / HS256 JWT                      |
        +---------------------------------------------------------------------------+
        |
        | 3. API Request: Authorization: Bearer <JWT>
        v
+----------------------------------------------------------------------------------------------+
| FastAPI Application Gateway                                                                  |
|                                                                                              |
|   a. TenantContextMiddleware verifies JWT cryptographic signature                            |
|   b. Extracts claims: sub (user_id), app_metadata.tenant_id, user_metadata.role              |
|   c. Validates user status: Active, Invited, Suspended                                       |
|   d. Binds TenantContext to request.state and Python ContextVar                              |
+----------------------------------------------------------------------------------------------+
        |
        | 4. Acquires pooled DB connection & executes:
        |    SET LOCAL app.current_tenant_id = '<tenant_id>';
        |    SET LOCAL app.current_user_id = '<user_id>';
        v
+----------------------------------------------------------------------------------------------+
| Supabase PostgreSQL 16 (Row-Level Security Active)                                          |
|                                                                                              |
|   All queries transparently filtered by:                                                     |
|   WHERE tenant_id = current_setting('app.current_tenant_id')::uuid                           |
+----------------------------------------------------------------------------------------------+
```

### 1.1 Token Claims Specification

Each authenticated JWT issued to a WapiFlow user includes:

```json
{
  "sub": "b2f6b39c-5e40-4d89-b572-87a4146747df",
  "email": "operator@store.com",
  "aud": "authenticated",
  "role": "authenticated",
  "app_metadata": {
    "provider": "email",
    "providers": ["email"],
    "tenant_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  },
  "user_metadata": {
    "full_name": "Sarah Connor",
    "role": "manager"
  },
  "exp": 1735700000
}
```

### 1.2 Role-Based Access Control (RBAC) Matrix

| Action / Resource | Owner / Admin | Manager | Agent | System Worker |
| :--- | :---: | :---: | :---: | :---: |
| Manage Organization & Billing | ✅ | ❌ | ❌ | ❌ |
| Connect / Disconnect WhatsApp WABA | ✅ | ❌ | ❌ | ❌ |
| Manage Products & Prices | ✅ | ✅ | ❌ | ❌ |
| Create & Cancel Orders | ✅ | ✅ | ✅ | ✅ |
| View & Send Chat Messages | ✅ | ✅ | ✅ | ✅ |
| Export Customer PII & Audit Logs | ✅ | ❌ | ❌ | ❌ |
| Access Raw Webhook Payloads | ✅ | ❌ | ❌ | ✅ |

---

## 2. Row-Level Security (RLS) Policy Architecture

RLS guarantees that data cannot be accessed across tenants even in cases of application logic bugs, developer oversight, or injection attempts.

### 2.1 RLS Golden Rules

1. Every table must have `ROW LEVEL SECURITY` enabled and forced.
2. The `FORCE ROW LEVEL SECURITY` clause ensures table owners and superusers cannot accidentally bypass RLS during standard application connections.
3. Every SELECT, INSERT, UPDATE, DELETE policy validates against the authenticated tenant context.

```sql
-- Enforce RLS on domain table
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations FORCE ROW LEVEL SECURITY;

-- Dynamic Tenant Context Policy
CREATE POLICY conversations_tenant_isolation ON conversations
    FOR ALL
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        OR
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        OR
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );
```

---

## 3. Webhook Cryptographic Verification (HMAC-SHA256)

Meta WhatsApp Cloud API sends webhooks for incoming messages, delivery receipts, and status updates. An attacker could forge webhook requests to create fake orders or hijack accounts.

### 3.1 Verification Algorithm

Every incoming request to `/api/v1/webhooks/whatsapp` must contain an `X-Hub-Signature-256` header. The payload is verified before parsing any JSON:

```python
import hmac
import hashlib
from fastapi import Request, HTTPException, status

async def verify_meta_signature(request: Request, app_secret: str) -> bytes:
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature"
        )
    
    parts = signature_header.split("sha256=")
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed webhook signature header"
        )
    
    expected_hash = parts[1]
    raw_body = await request.body()
    
    computed_hash = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison prevents timing attacks
    if not hmac.compare_digest(computed_hash, expected_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature"
        )
    
    return raw_body
```

---

## 4. Personally Identifiable Information (PII) Protection

WhatsApp phone numbers are sensitive PII subject to GDPR, CCPA, and Meta Commercial Messaging policies.

### 4.1 Phone Number Masking Policy

**Strict Rule**: Phone numbers MUST NEVER be printed in plaintext to application logs, tracing systems (Sentry), console outputs, or unencrypted storage.

- Standard Masking Pattern: `+<country_code> *** *** <last_4_digits>`
- Example: `+1 (555) 234-5678` -> `+1 *** *** 5678`
- E.164: `+447911123456` -> `+44 *** *** 3456`

```python
import re

def mask_phone_number(phone: str) -> str:
    """Masks customer phone numbers for safe logging."""
    digits_only = re.sub(r"[^\d+]", "", phone)
    if len(digits_only) <= 4:
        return "****"
    prefix = digits_only[:3]
    suffix = digits_only[-4:]
    return f"{prefix} *** *** {suffix}"
```

### 4.2 Error Handling & Information Leakage Prevention

- **Never return raw database or stack trace errors**: PostgreSQL syntax errors, unique constraint violation names, or file paths must never escape to client responses.
- All unhandled exceptions are caught by global FastAPI exception handlers, logged internally with a correlation `request_id`, and returned to the client as an opaque error envelope:

```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred. Please quote the reference ID to support.",
    "request_id": "req_01HPX7K94Q8V12AB34CD"
  }
}
```

---

## 5. Threat Model (STRIDE Assessment)

| Threat Category | Potential Attack Vector | Mitigation in WapiFlow |
| :--- | :--- | :--- |
| **Spoofing** | Forged Meta WhatsApp webhooks injecting fraudulent orders. | Mandatory HMAC-SHA256 signature check (`X-Hub-Signature-256`) with constant-time comparison before any processing. |
| **Tampering** | Modifying order pricing or updating records belonging to another business. | Strict DB RLS; all mutations check `tenant_id`; order pricing is calculated on backend from product catalog, not user input. |
| **Repudiation** | Operator claims they never cancelled or altered an order. | Immutable append-only `audit_logs` table recording `user_id`, `tenant_id`, `action`, `resource_id`, and timestamp. |
| **Information Disclosure** | Cross-tenant data leakage via SQL injection or multi-tenant query bugs. | PostgreSQL RLS enabled and forced; parameterized queries exclusively via SQLModel/asyncpg; PII masking in logs. |
| **Denial of Service** | Webhook flooding or outbound messaging queue exhaustion. | Webhook returns HTTP 200 within 50ms and offloads payload to Redis; Redis token-bucket rate limiting per tenant. |
| **Elevation of Privilege** | Agent user attempts to access organization billing or API tokens. | FastAPI dependency `require_role(["owner", "admin"])` validates claims in verified JWT. |

---

## 6. Secrets Management & Key Rotation

1. **Environment Variables**: Secrets are injected as environment variables at runtime via container orchestrators (Render / Fly.io / Docker), never checked into git.
2. **Access Separation**:
   - `SUPABASE_ANON_KEY`: Public-safe, restricted by RLS, used only by frontend.
   - `SUPABASE_SERVICE_ROLE_KEY`: Superuser key, restricted to background maintenance jobs, NEVER bundled into frontend.
3. **Rotation Procedures**:
   - **Meta App Secret & Verify Token**: Update in Meta App Dashboard, then update environment variable and trigger zero-downtime rolling restart.
   - **Database Password**: Rotate via Supabase Dashboard; connection string pooler ensures seamless reconnects.
   - **R2 API Tokens**: Rotate every 90 days with dual-token overlap period.

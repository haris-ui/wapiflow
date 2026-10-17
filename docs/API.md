# REST API Conventions & Specification

WapiFlow provides an asynchronous, predictable RESTful API designed around multi-tenancy, strict validation, and idempotent operations.

---

## 1. Protocol & Versioning

- **Base URL (Local)**: `http://localhost:8000/api/v1`
- **Base URL (Production)**: `https://api.wapiflow.com/api/v1`
- **Content Type**: `application/json; charset=utf-8`
- **API Versioning**: URL path-based (`/api/v1/`). Breaking schema changes will increment the major version path (`/api/v2/`).

---

## 2. Authentication & Headers

Every request to the protected API tier must supply the client's verified Supabase Auth JWT token in the `Authorization` header:

```http
GET /api/v1/orders HTTP/1.1
Host: api.wapiflow.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
Accept: application/json
X-Request-ID: req_01HPX7K94Q8V12AB34CD
```

### Standard Headers

| Header Name | Type | Description |
| :--- | :--- | :--- |
| `Authorization` | Required | `Bearer <JWT>` issued by Supabase Auth. Contains authenticated `tenant_id` claim. |
| `X-Request-ID` | Optional | Client correlation ID for tracing. If omitted, the server generates a UUID v7. |
| `X-Hub-Signature-256` | Webhook Only | Cryptographic HMAC-SHA256 signature calculated by Meta using the App Secret. |

---

## 3. Standard Response Format

All successful responses return HTTP `200 OK` (or `201 Created` for resource creation) with a consistent JSON body.

### 3.1 Single Resource Response

```json
{
  "data": {
    "id": "ord_01HPX88M6A4VBD12345678",
    "tenant_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "customer_id": "cust_01HPX81J5K4VBD98765432",
    "status": "confirmed",
    "total_amount": 149.50,
    "currency": "USD",
    "created_at": "2026-10-17T07:30:00Z",
    "updated_at": "2026-10-17T07:31:00Z"
  }
}
```

### 3.2 Paginated List Response

List endpoints accept `limit` (default: `20`, max: `100`), `offset` (page-based), or `cursor` (keyset pagination for continuous feeds):

```http
GET /api/v1/conversations?limit=20&cursor=wamid_01HPX88M HTTP/1.1
```

```json
{
  "data": [
    {
      "id": "conv_01HPX88M6A4VBD0001",
      "customer_id": "cust_01HPX81J5K4VBD0001",
      "last_message": "Can I get an update on order #1042?",
      "unread_count": 1,
      "updated_at": "2026-10-17T07:28:00Z"
    }
  ],
  "meta": {
    "limit": 20,
    "has_more": true,
    "next_cursor": "conv_01HPX88M6A4VBD0020",
    "total": 348
  }
}
```

---

## 4. Error Handling & Standard Error Envelope

WapiFlow guarantees **safe, uniform error responses**. Under no circumstance will the backend expose raw database exceptions, SQL queries, or internal stack traces to the caller.

### 4.1 Error Envelope Schema

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested order does not exist or does not belong to your organization.",
    "request_id": "req_01HPX7K94Q8V12AB34CD",
    "details": []
  }
}
```

### 4.2 Validation Error Example (HTTP 422 Unprocessable Entity)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed on 2 fields.",
    "request_id": "req_01HPX7K94Q8V12AB34CD",
    "details": [
      {
        "field": "phone_number",
        "issue": "Invalid international E.164 phone number format"
      },
      {
        "field": "total_amount",
        "issue": "Amount must be greater than zero"
      }
    ]
  }
}
```

### 4.3 Standard Error Codes

| HTTP Status | Error Code | Description |
| :---: | :--- | :--- |
| `400` | `BAD_REQUEST` | Malformed request body or missing parameters. |
| `401` | `UNAUTHORIZED` | Missing, expired, or invalid Supabase JWT bearer token. |
| `403` | `FORBIDDEN` | Valid authentication but user lacks required role or tenant permission. |
| `404` | `RESOURCE_NOT_FOUND` | Resource was not found within the caller's tenant. |
| `409` | `RESOURCE_CONFLICT` | Unique key violation (e.g. duplicate SKU or idempotency key collision). |
| `422` | `VALIDATION_ERROR` | Request body fails Pydantic schema validation. |
| `429` | `RATE_LIMITED` | Tenant exceeded allocated requests per minute. |
| `500` | `INTERNAL_SERVER_ERROR` | Unhandled server error. Stack trace logged internally with `request_id`. |
| `503` | `SERVICE_UNAVAILABLE` | Database connection or external Meta API outage. |

---

## 5. Core Endpoints Reference

### 5.1 System Health
- `GET /health/live` — Returns `200 OK` (ASGI process liveness check).
- `GET /health/ready` — Returns `200 OK` if PostgreSQL and Redis connections are healthy, `503` if degraded.

### 5.2 WhatsApp Webhooks
- `GET /api/v1/webhooks/whatsapp` — Meta webhook verification handshake (`hub.challenge`).
- `POST /api/v1/webhooks/whatsapp` — Meta webhook inbound message and status ingestion. Validated via `X-Hub-Signature-256`.

### 5.3 Conversations & Messages
- `GET /api/v1/conversations` — List conversations for the tenant (supports status and unread filters).
- `GET /api/v1/conversations/{id}` — Get single conversation details.
- `GET /api/v1/conversations/{id}/messages` — List paginated message thread for a conversation.
- `POST /api/v1/conversations/{id}/messages` — Send an outbound freeform message or interactive template.

### 5.4 Orders & Fulfillment
- `GET /api/v1/orders` — List tenant orders (filterable by customer, status, date range).
- `POST /api/v1/orders` — Manually create or draft an order.
- `GET /api/v1/orders/{id}` — Retrieve full order detail including line items and payment link.
- `PATCH /api/v1/orders/{id}/status` — Update order state (e.g., `confirmed` -> `fulfilled` -> `delivered`).

### 5.5 Products & Catalog
- `GET /api/v1/products` — List catalog products and inventory counts.
- `POST /api/v1/products` — Create a new catalog item.
- `PATCH /api/v1/products/{id}` — Update item pricing, inventory, or description.
- `DELETE /api/v1/products/{id}` — Soft-delete a catalog product.

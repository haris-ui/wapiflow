# Testing Strategy & Execution Guide

WapiFlow employs a rigorous multi-tiered automated testing strategy spanning unit tests, integration tests with real databases and Redis instances, and webhook signature verification simulations.

---

## 1. Test Architecture & Pyramids

```text
                  / \
                 /   \
                / E2E \       - Critical user journeys & webhook pipelines
               /-------\
              / Integr. \     - FastAPI + real Postgres (RLS) + Redis ARQ
             /-----------\
            /  Unit Tests \   - Pydantic models, utilities, pricing logic, UI
           /---------------\
```

| Scope | Tooling | Focus | Target Coverage |
| :--- | :--- | :--- | :---: |
| **Backend Unit** | `pytest`, `pytest-asyncio`, `pytest-mock` | Pydantic validation, business rules, pricing calculation, PII masking | > 90% |
| **Backend Integration** | `pytest`, `httpx.AsyncClient`, Testcontainers / Local DB | Full HTTP request cycles, RLS isolation policies, ARQ job dispatching | > 80% |
| **Frontend Unit** | `vitest`, `@testing-library/react`, `msw` | Component rendering, state hooks, form validations, optimistic mutations | > 80% |
| **Type Integrity** | `mypy` (Python), `tsc --noEmit` (TypeScript) | Zero type errors, strict null checks, explicit models | 100% |

---

## 2. Running Tests

### 2.1 Unified Test Command
Run all unit and integration test suites across frontend and backend:

```bash
make test
```

### 2.2 Backend Tests (FastAPI / Pytest)
To run backend tests exclusively:

```bash
# Using Makefile
make test-backend

# Or directly in apps/api directory:
cd apps/api
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing --cov-report=html tests/

# Run a specific test module
pytest tests/test_webhooks.py -v -k "test_meta_signature"
```

### 2.3 Frontend Tests (React / Vitest)
To run frontend tests:

```bash
# Using Makefile
make test-frontend

# Or directly in apps/web directory:
cd apps/web
npm test -- --run

# Run with interactive UI
npm run test:ui

# Run with coverage
npm run test:coverage
```

### 2.4 Static Analysis & Linting

```bash
make lint
```
Executes:
- `ruff check .` (Python fast linter)
- `black --check .` (Python code formatter check)
- `mypy app` (Strict Python static type checking)
- `npm run lint` (ESLint on React codebase)
- `npm run type-check` (`tsc --noEmit` on TypeScript codebase)

---

## 3. Backend Test Implementation Guidelines

### 3.1 Async Client & Test DB Fixture
FastAPI endpoints are tested asynchronously using `httpx.AsyncClient` with transaction rollbacks to guarantee test isolation:

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health_live_endpoint(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

### 3.2 Testing Row-Level Security (Tenant Isolation)
Tests verify that Tenant A can never view, update, or delete records created by Tenant B:

```python
@pytest.mark.asyncio
async def test_tenant_rls_isolation(client: AsyncClient, token_tenant_a, token_tenant_b):
    # 1. Create order under Tenant A
    res_a = await client.post(
        "/api/v1/orders",
        json={"total_amount": 100.0, "currency": "USD"},
        headers={"Authorization": f"Bearer {token_tenant_a}"}
    )
    assert res_a.status_code == 201
    order_id = res_a.json()["data"]["id"]

    # 2. Attempt to read order using Tenant B credentials
    res_b = await client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {token_tenant_b}"}
    )
    assert res_b.status_code == 404
    assert res_b.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
```

### 3.3 Simulating Meta Webhook Deliveries
Use helper utilities to generate cryptographic signatures matching `META_APP_SECRET`:

```python
import hmac
import hashlib
import json

def generate_hub_signature(payload: dict, secret: str) -> str:
    raw_bytes = json.dumps(payload).encode("utf-8")
    hash_hex = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
    return f"sha256={hash_hex}"

@pytest.mark.asyncio
async def test_webhook_hmac_verification_success(client: AsyncClient, test_secret):
    payload = {"object": "whatsapp_business_account", "entry": []}
    sig = generate_hub_signature(payload, test_secret)

    response = await client.post(
        "/api/v1/webhooks/whatsapp",
        json=payload,
        headers={"X-Hub-Signature-256": sig}
    )
    assert response.status_code == 200
```

---

## 4. Continuous Integration Checks

Every pull request must pass the GitHub Actions CI pipeline:
1. **Lint Check**: Zero warnings or format errors.
2. **Type Check**: Zero TypeScript or Mypy type violations.
3. **Automated Test Run**: 100% pass rate.
4. **Coverage Threshold**: PRs causing overall code coverage to drop below 80% are blocked from merging.

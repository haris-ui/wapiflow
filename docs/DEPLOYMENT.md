# Deployment Guide: Local, Staging & Production

This guide covers deployment procedures across all lifecycle stages for the WapiFlow monorepo.

---

## 1. Environments Overview

| Environment | Frontend | Backend API & ARQ Workers | Database & Auth | Redis Broker | Media Storage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Local Dev** | Vite Dev Server (`localhost:5173`) | Uvicorn (`localhost:8000`) | Docker PostgreSQL 16 (`localhost:5432`) | Docker Redis 7 (`localhost:6379`) | Local filesystem / MinIO or R2 dev bucket |
| **Staging** | Vercel (`staging.wapiflow.com`) | Render / Fly.io (`api-staging.wapiflow.com`) | Supabase Staging Project | Upstash Redis (Staging) | Cloudflare R2 (`wapiflow-media-staging`) |
| **Production** | Vercel Edge (`app.wapiflow.com`) | Render / Container Cluster (`api.wapiflow.com`) | Supabase Production Project | Upstash Redis (Pro) / Managed Redis | Cloudflare R2 (`wapiflow-media-production`) |

---

## 2. Local Development Deployment

Local development utilizes Docker Compose to run backing services alongside hot-reloading application processes:

```bash
# 1. Clone repository & configure environment variables
git clone <repo_url>
cd WSAAS
cp .env.example .env

# 2. Boot background containers (Postgres, Redis, pgAdmin)
make docker-up

# 3. Apply database migrations
make migrate

# 4. In Terminal 1: Launch FastAPI backend with hot-reload
make dev-backend

# 5. In Terminal 2: Launch Vite frontend
make dev-frontend
```

Verify service endpoints:
- Frontend UI: `http://localhost:5173`
- Backend Swagger API Docs: `http://localhost:8000/docs`
- Health Liveness Probe: `http://localhost:8000/health/live`
- Health Readiness Probe: `http://localhost:8000/health/ready`
- pgAdmin Dashboard: `http://localhost:5050`

---

## 3. Production Deployment Step-by-Step

### 3.1 Step 1: Database & Auth Setup (Supabase)
1. Create a new organization and project on [Supabase Cloud](https://supabase.com).
2. Note the Project URL, Anon Key, Service Role Key, and PostgreSQL Transaction Pooler connection string (`pooler.supabase.com:6543`).
3. Under **Authentication** -> **Providers**, enable **Email** (and Google OAuth if required).
4. Run schema migrations against the production database:
   ```bash
   SUPABASE_DB_URL="postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require" make migrate
   ```

### 3.2 Step 2: Object Storage Setup (Cloudflare R2)
1. In Cloudflare Dashboard, navigate to **R2** -> **Create Bucket**:
   - Bucket name: `wapiflow-media-production`
   - Location: Automatic
2. Set Bucket CORS Policy to allow operator uploads from the frontend:
   ```json
   [
     {
       "AllowedOrigins": ["https://app.wapiflow.com"],
       "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
       "AllowedHeaders": ["*"],
       "ExposeHeaders": ["ETag"],
       "MaxAgeSeconds": 3600
     }
   ]
   ```
3. Generate R2 API Tokens with `Object Read & Write` permissions.
4. (Optional) Connect a custom domain: `media.wapiflow.com`.

### 3.3 Step 3: Redis Setup (Upstash or Managed Redis)
1. Create a Redis database with TLS on [Upstash](https://upstash.com) or your managed cloud provider.
2. Ensure persistence (AOF/RDB) is enabled.
3. Save the connection string: `rediss://default:[password]@[host]:[port]`.

### 3.4 Step 4: Backend API & Worker Deployment (Render / Docker)
The backend runs in two processes:
1. **API Web Service**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4`
2. **ARQ Worker Service**: `python -m arq app.workers.worker.WorkerSettings`

#### Render Blueprint (`render.yaml`):
```yaml
services:
  - type: web
    name: wapiflow-api
    env: python
    region: frankfurt
    plan: starter
    rootDir: apps/api
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
    healthCheckPath: /health/ready
    envVars:
      - key: PYTHON_VERSION
        value: 3.13.0
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: SUPABASE_DB_URL
        sync: false
      - key: BACKEND_SECRET_KEY
        sync: false
      - key: REDIS_URL
        sync: false
      - key: META_APP_SECRET
        sync: false
      - key: META_VERIFY_TOKEN
        sync: false

  - type: worker
    name: wapiflow-arq-worker
    env: python
    region: frankfurt
    plan: starter
    rootDir: apps/api
    buildCommand: pip install -r requirements.txt
    startCommand: python -m arq app.workers.worker.WorkerSettings
    envVars:
      - key: PYTHON_VERSION
        value: 3.13.0
      - key: REDIS_URL
        sync: false
      - key: SUPABASE_DB_URL
        sync: false
```

### 3.5 Step 5: Frontend Deployment (Vercel)
1. Import repository into [Vercel](https://vercel.com).
2. Configure Project Settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `apps/web`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add Environment Variables:
   - `VITE_SUPABASE_URL`: `https://[project-ref].supabase.co`
   - `VITE_SUPABASE_ANON_KEY`: `[anon_key]`
   - `VITE_API_URL`: `https://api.wapiflow.com`
   - `VITE_APP_NAME`: `WapiFlow`
   - `VITE_SENTRY_DSN`: `[dsn_url]`
4. Deploy and bind production custom domain: `app.wapiflow.com`.

---

## 4. CI/CD Pipeline (GitHub Actions)

Continuous integration and automated delivery pipeline:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, staging ]
  pull_request:
    branches: [ main ]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'

      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: 'apps/web/package-lock.json'

      - name: Install dependencies
        run: make install

      - name: Run Linters
        run: make lint

      - name: Run Backend Tests
        run: make test-backend

      - name: Run Frontend Tests
        run: make test-frontend

  deploy-staging:
    needs: lint-and-test
    if: github.ref == 'refs/heads/staging'
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Staging Deploy Webhook
        run: curl -X POST ${{ secrets.RENDER_STAGING_DEPLOY_HOOK }}
```

---

## 5. Health Checks & Zero-Downtime Migration Policy

### 5.1 Health Check Endpoints
- **Liveness Probe** (`GET /health/live`): Confirms ASGI worker is accepting requests. Always returns `200 OK`.
- **Readiness Probe** (`GET /health/ready`): Validates connection to PostgreSQL pool and Redis broker. Returns `200 OK` only when both systems respond; returns `503 Service Unavailable` if database or Redis are unreachable.

### 5.2 Zero-Downtime Migration Strategy
1. **Expand and Contract (Phased Migrations)**:
   - **Phase 1 (Add)**: Add nullable columns or new tables with safe defaults. Apply migration before deploying new code.
   - **Phase 2 (Code Deploy)**: Deploy new application version that reads and writes both old and new columns.
   - **Phase 3 (Backfill & Contract)**: Backfill data, then drop obsolete columns in a subsequent release.
2. **Never lock tables exclusively**: Always create indexes concurrently (`CREATE INDEX CONCURRENTLY IF NOT EXISTS`).

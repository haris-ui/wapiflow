# Operations, Observability & Incident Response

This document establishes operational procedures, telemetry instrumentation, alerting thresholds, and incident playbooks for WapiFlow production systems.

---

## 1. Observability Architecture

```text
[Incoming Requests / Webhooks]
              |
              v
     [FastAPI Middleware]
     - Injects X-Request-ID
     - Masks PII (Phone numbers)
     - Captures Latency & Status Codes
              |
              +----------------------------+
              |                            |
              v                            v
      [Structured Logs]            [Sentry APM]
     - JSON formatted outputs     - Error captures with context
     - Shipped to Cloud Logging   - Distributed transaction tracing
                                  - Webhook latency profiling
```

### 1.1 Structured Logging Standard

All application logs must be output to `stdout` in valid JSON format with standard fields:

```json
{
  "timestamp": "2026-10-17T07:45:12.304Z",
  "level": "INFO",
  "logger": "app.services.whatsapp",
  "message": "Outbound message dispatched successfully",
  "request_id": "req_01HPX7K94Q8V12AB34CD",
  "tenant_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "customer_phone_masked": "+1 *** *** 4821",
  "duration_ms": 42.1
}
```

> [!CAUTION]
> **Zero Plaintext PII Rule**: Logging raw customer phone numbers, customer credit card numbers, or Meta API access tokens is strictly forbidden. The automated linter and code reviews enforce the `mask_phone_number` utility.

---

## 2. Key Metrics & Alert Thresholds

| Metric | Target / SLA | Alert Threshold (Warning) | Critical Page Threshold | Action |
| :--- | :--- | :--- | :--- | :--- |
| **Webhook Response Latency** | < 100ms | p95 > 500ms for 3m | p95 > 2,000ms for 1m | Scale API pods; verify webhook fast-path |
| **ARQ Queue Backlog** | < 50 jobs | > 500 queued jobs | > 2,000 queued jobs | Scale ARQ worker replicas |
| **Meta API Rate Limit (429)** | 0% | > 10 errors in 5m | > 50 errors in 5m | Verify Redis rate limiter; apply backoff |
| **Database Pool Utilization**| < 70% | > 80% pool busy | > 95% pool busy | Check for long-running unindexed queries |
| **Daily Resend Email Quota** | < 100 / day | > 80 emails in 24h | > 95 emails in 24h | Notify administrator to upgrade plan |

---

## 3. Incident Response Playbooks

### Playbook A: Meta Webhook Ingestion Outage

**Symptoms**: Inbound customer WhatsApp messages are not appearing on the operator dashboard. Meta App Dashboard shows Webhook Error Rate > 5%.

**Procedure**:
1. **Check FastAPI Liveness**:
   ```bash
   curl -I https://api.wapiflow.com/health/live
   ```
2. **Inspect Webhook Endpoint Errors**:
   Query logs for `/api/v1/webhooks/whatsapp`:
   ```bash
   grep "webhooks/whatsapp" /var/log/wapiflow/api.log | grep -E "401|403|500"
   ```
3. **Verify App Secret**:
   If returns `403 Forbidden`, check whether `META_APP_SECRET` was recently regenerated in Meta Developer Dashboard without updating production `.env`.
4. **Inspect Redis Broker Connectivity**:
   ```bash
   redis-cli -u $REDIS_URL ping
   ```
   If Redis is down or full, webhooks cannot enqueue messages. Restart Redis or flush expired keys.
5. **Acknowledge Meta Outage**:
   Check Meta Business Status page (`https://metastatus.com/whatsapp-business-api`) for upstream Cloud API incidents.

---

### Playbook B: Database Connection Pool Exhaustion

**Symptoms**: API endpoints return `503 Service Unavailable` with `too many clients already` or `connection pool timeout`.

**Procedure**:
1. **Identify Long-Running Queries**:
   Connect via pgAdmin or Supabase SQL Editor and execute:
   ```sql
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE (now() - pg_stat_activity.query_start) > interval '10 seconds'
     AND state != 'idle';
   ```
2. **Terminate Blocked Queries**:
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <PID_TO_KILL>;
   ```
3. **Switch to Supavisor Pooler**:
   Ensure `SUPABASE_DB_URL` points to port `6543` (transaction mode pooler) rather than port `5432` (session mode).
4. **Restart API Worker Nodes**:
   Restart backend instances to clear abandoned pooled connections.

---

### Playbook C: WhatsApp Cloud API Rate Limit Exceeded (HTTP 429)

**Symptoms**: Outbound order confirmations and messages are failing with Meta error code `131048` or `130429`.

**Procedure**:
1. **Pause Batch Broadcast Campaigns**:
   Immediately suspend non-critical broadcast tasks in the ARQ queue:
   ```bash
   python -m app.scripts.pause_queue --queue "marketing"
   ```
2. **Review Tenant Quota**:
   Inspect whether a single tenant triggered high-volume marketing messages exceeding Meta tier throughput (80 MPS on Tier 1).
3. **Enable Exponential Jitter Backoff**:
   Ensure the ARQ worker retry mechanism applies exponential backoff:
   `wait_seconds = min(300, (2 ** attempt) + random.uniform(0.5, 1.5))`.
4. **Request Meta Tier Upgrade**:
   If business volume warrants, submit request via Meta Business Manager to increase phone number messaging tier from 1,000 to 10,000 conversations/day.

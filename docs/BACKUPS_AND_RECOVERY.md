# Backups, Disaster Recovery & Business Continuity

This document outlines the backup topologies, recovery objectives, and disaster response procedures across all storage and database providers utilized by WapiFlow.

---

## 1. Recovery Objectives (SLA Targets)

| Environment | Recovery Point Objective (RPO) | Recovery Time Objective (RTO) | Description |
| :--- | :---: | :---: | :--- |
| **Production Primary** | **< 5 minutes** | **< 30 minutes** | Continuous WAL archiving enables restoration to any second within the past 7 days. |
| **Object Media (R2)** | **< 1 minute** | **< 15 minutes** | Versioned buckets allow immediate rollback of deleted or overwritten objects. |
| **Queue / Cache (Redis)**| **< 15 minutes** | **< 10 minutes** | Ephemeral queues; in-flight tasks replayable from idempotent webhook logs. |

---

## 2. Backup Strategy per Infrastructure Component

```text
+-------------------------------------------------------------------------------------------------+
|                                    WAPIFLOW BACKUP ECOSYSTEM                                    |
|                                                                                                 |
|   +-----------------------+   WAL Streaming     +-------------------------------------------+   |
|   | Supabase PostgreSQL   | ------------------> | Cloud Storage WAL-G (Continuous Archive)  |   |
|   | Primary DB            |   Daily Snapshot    | - Enables Point-In-Time Recovery (PITR)   |   |
|   +-----------------------+ ------------------> | - Retained 7 days (Pro) / 30 days (Ent.)   |   |
|                                                 +-------------------------------------------+   |
|   +-----------------------+   RDB / AOF         +-------------------------------------------+   |
|   | Redis 7 Broker        | ------------------> | Persistent Block Storage Volume           |   |
|   | Task & Rate Limit     |                     | - Hourly snapshot + Append-Only File      |   |
|   +-----------------------+                     +-------------------------------------------+   |
|                                                                                                 |
|   +-----------------------+   Object Versioning +-------------------------------------------+   |
|   | Cloudflare R2 Bucket  | ------------------> | Cloudflare Distributed Storage Pool       |   |
|   | Invoices & Media      |                     | - Non-current versions kept 90 days       |   |
|   +-----------------------+                     +-------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

### 2.1 Supabase PostgreSQL Database
- **Continuous Write-Ahead Logging (WAL)**: WAL records are streamed to secure cloud storage.
- **Point-In-Time Recovery (PITR)**: Enables rolling back the database to any millisecond within the retention window (e.g. 5 minutes before a bad migration or data corruption event).
- **Logical pg_dump Backups**: An automated GitHub Actions cron runs weekly logical dumps of schema and row data to an encrypted, cold-storage R2 bucket.

### 2.2 Redis (Job Queues & State)
- **AOF (Append-Only File)**: Redis is configured with `appendonly yes` and `appendfsync everysec`, guaranteeing at most 1 second of task loss in catastrophic hardware failure.
- **RDB Snapshots**: Snapshots are taken every 60 seconds if at least 1 key changed.

### 2.3 Cloudflare R2 (Object Storage)
- **Bucket Versioning**: Enabled on `wapiflow-media-production`. Overwritten or deleted customer invoices and media retain prior versions for 90 days.
- **Lifecycle Rules**: Incomplete multipart uploads are aborted and cleaned after 7 days.

---

## 3. Disaster Recovery Runbooks

### Runbook 1: Supabase Point-in-Time Recovery (PITR)

**Scenario**: A database migration error or accidental batch deletion corrupted order records at `2026-10-17 14:32:00 UTC`.

1. **Halt Application Traffic**:
   Temporarily put the frontend in maintenance mode or stop API containers to avoid writing further conflicting records.
2. **Access Supabase PITR Console**:
   - Go to **Supabase Dashboard** -> **Project Settings** -> **Database** -> **Backups**.
   - Select **Point in Time**.
3. **Select Restoration Timestamp**:
   Enter target time: `2026-10-17 14:30:00 UTC` (2 minutes prior to corruption event).
4. **Initiate Restore**:
   Confirm restoration. Supabase will spin up a fresh instance and replay WAL logs up to the exact minute.
5. **Verify Database Integrity**:
   Inspect row counts on `tenants`, `orders`, and `messages`.
6. **Re-route DNS / Connection Strings**:
   Update `SUPABASE_DB_URL` if a new project reference was spawned, then bring the application back online.

---

### Runbook 2: Accidental Tenant Record Recovery

**Scenario**: An operator accidentally deleted a critical customer or conversation thread, but other tenants remain unaffected.

1. **Extract Tenant Data from Standby Dump**:
   Spin up the latest logical backup in a temporary Docker instance:
   ```bash
   docker run --name temp-pg -e POSTGRES_PASSWORD=temp -d postgres:16
   pg_restore -h localhost -p 5432 -U postgres -d postgres backup_latest.dump
   ```
2. **Export Isolated Tenant Slice**:
   ```sql
   \copy (SELECT * FROM customers WHERE tenant_id = '7c9e6679-7425-40de-944b-e07fc1f90ae7') TO 'customers_recover.csv' CSV HEADER;
   \copy (SELECT * FROM conversations WHERE tenant_id = '7c9e6679-7425-40de-944b-e07fc1f90ae7') TO 'conversations_recover.csv' CSV HEADER;
   ```
3. **Re-import to Production**:
   Apply data back to production using an idempotent `ON CONFLICT DO NOTHING` SQL script.

---

### Runbook 3: Cloudflare R2 Media Rollback

**Scenario**: An invoice file was accidentally overwritten in the media bucket.

1. Install and authenticate AWS CLI with R2 credentials:
   ```bash
   aws configure set aws_access_key_id "$R2_ACCESS_KEY_ID"
   aws configure set aws_secret_access_key "$R2_SECRET_ACCESS_KEY"
   ```
2. List non-current object versions:
   ```bash
   aws s3api list-object-versions \
     --endpoint-url https://$R2_ACCOUNT_ID.r2.cloudflarestorage.com \
     --bucket wapiflow-media-production \
     --prefix "tenants/7c9e6679-7425-40de-944b-e07fc1f90ae7/orders/ord_1024/"
   ```
3. Restore previous version by copying the versioned object ID back to the canonical key.

---

## 4. Quarterly Backup Drill Schedule

To ensure backup readiness:
- **Every Quarter (Q1, Q2, Q3, Q4)**:
  1. Restore the production database backup into a staging environment.
  2. Execute automated integration test suite (`make test`) against the restored database.
  3. Validate that RLS policies remain functional on the restored dataset.
  4. Measure and document RTO to verify compliance with the 30-minute target.

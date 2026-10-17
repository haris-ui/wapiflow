# Cloud Provider Costs, Quotas & Limits

WapiFlow is engineered to operate efficiently within modern cloud provider free tiers during initial development and early-stage tenant onboarding, scaling predictably as production volume grows.

---

## 1. Free Tier Comparison & Limit Matrix

| Provider & Service | Free Tier Allocation | Key Quotas & Thresholds | Overage Cost / Upgrade Tier |
| :--- | :--- | :--- | :--- |
| **Supabase**<br>(PostgreSQL & Auth) | • 500 MB PostgreSQL database<br>• 50,000 Monthly Active Users (MAU)<br>• 5 GB file storage<br>• 2 GB bandwidth | • 2 active projects max<br>• Pauses after 7 days of inactivity (free)<br>• Direct connection pool limit: 60 | **$25/month (Pro Tier)**<br>• 8 GB DB disk included ($0.125/GB after)<br>• 100,000 MAU ($0.00325/MAU after)<br>• Never pauses |
| **Vercel**<br>(Frontend Hosting) | • 100 GB Bandwidth / month<br>• 6,000 Build Minutes / month<br>• Automatic global Edge CDN<br>• Unlimited preview deployments | • Non-commercial fair use on Hobby tier<br>• Max 100 deployments / day<br>• Edge Function execution 10s timeout | **$20/seat/month (Pro Tier)**<br>• 1 TB Bandwidth<br>• Commercial use licensed<br>• Concurrent builds |
| **Render**<br>(FastAPI Backend API) | • 750 free instance hours / month<br>• 512 MB RAM, 0.1 vCPU<br>• Free TLS/SSL certificates | • Spins down after 15 min of inactivity<br>• Cold start latency: ~30-50s<br>• 100 GB egress / month | **$7/month (Starter Instance)**<br>• Always on (no cold start)<br>• 512 MB RAM, 0.5 vCPU<br>• Health check automations |
| **Cloudflare R2**<br>(Object Storage) | • **10 GB storage / month free**<br>• **1,000,000 Class A operations** (write/list)<br>• **10,000,000 Class B operations** (read)<br>• **$0 egress fees permanently** | • Zero data egress bandwidth charges<br>• Max single upload size: 5 GB<br>• S3-compatible API | **Pay-as-you-go**:<br>• $0.015 / GB-month storage<br>• $4.50 / million Class A ops<br>• $0.36 / million Class B ops<br>• Zero egress fee |
| **Resend**<br>(Transactional Email) | • 3,000 emails / month free<br>• 100 emails / day limit<br>• 1 custom domain verified | • Daily rate limit: 100 sends<br>• Shared IP pool | **$20/month (Pro Tier)**<br>• 50,000 emails / month<br>• Unlimited domains<br>• Dedicated IP add-on |
| **Meta WhatsApp**<br>(Cloud API) | • **1,000 Service (User-Initiated) conversations free per month per WABA**<br>• Unlimited inbound messages | • 24-hour service window per session<br>• Marketing/Utility templates not covered by 1k free grant<br>• Tier 1 throughput: 80 MPS | **Per-Conversation Pricing** (varies by region/category):<br>• Utility: ~$0.005 - $0.035 / convo<br>• Marketing: ~$0.025 - $0.085 / convo<br>• Service: Free for first 1,000, then ~$0.015 - $0.035 |

---

## 2. WhatsApp Cloud API Conversation Pricing Rules

Meta charges on a **24-hour conversation session model**, not per individual message:

1. **Service Conversations (User-Initiated)**:
   - Triggered when a customer messages the business.
   - A 24-hour customer service window opens.
   - The first **1,000 Service conversations each month per WhatsApp Business Account (WABA) are 100% free**.
   - Within the open 24h window, the business can send unlimited freeform messages, images, order receipts, and interactive lists at no extra charge.

2. **Business-Initiated Conversations (Template Messages)**:
   - Must use pre-approved WhatsApp message templates.
   - Categorized into three tiers:
     - **Authentication**: One-time passcodes, account verification.
     - **Utility**: Order updates, shipping alerts, invoice receipts, payment links.
     - **Marketing**: Promotions, discount offers, product drops.
   - Charged per opened 24-hour window according to the recipient country's rate card.

---

## 3. Cost Optimization Strategies for Early Stage

### 3.1 Eliminating Render Backend Cold Starts
On the free Render tier, services spin down after 15 minutes of silence. A cold start of 40 seconds will cause Meta webhooks to time out and retry repeatedly.
- **Remediation Option A**: Deploy backend on **Railway** ($5 free credit/month covers a 24/7 512MB container) or **Fly.io** ($0 tier with 3 shared-cpu-1x VMs).
- **Remediation Option B**: Upgrade Render instance to Starter tier ($7/month) prior to production customer launch.

### 3.2 Optimizing Media Egress with Cloudflare R2
- Storing customer receipts, catalog images, and audio notes on AWS S3 incurs severe egress bandwidth penalties ($0.09/GB).
- Cloudflare R2 provides **0 egress fees**. Combined with Cloudflare CDN caching, all catalog image loads from WhatsApp or the dashboard are served at zero marginal bandwidth cost.

### 3.3 Supabase Database Quota Preservation
- Purge raw webhook payload records from `webhook_events` older than 30 days via a scheduled pg_cron / ARQ job.
- Store large documents and PDFs in Cloudflare R2, storing only the metadata reference URL in PostgreSQL.
- Utilize Supavisor connection pooler (port `6543`) to prevent reaching the 60 direct connection threshold.

---

## 4. Scaling Cost Projections

| Scale Milestone | Monthly Active Tenants | Monthly WhatsApp Convos | Projected Infrastructure Cost |
| :--- | :--- | :--- | :--- |
| **Stage 0 (MVP / Dev)** | 1 - 3 tenants | < 1,000 (Testing) | **$0.00 / month** (All Free Tiers) |
| **Stage 1 (Launch)** | 10 - 25 tenants | ~5,000 - 15,000 | **~$32.00 / month**<br>• Supabase Pro: $25<br>• Render Starter: $7<br>• R2 / Vercel / Resend: Free tier |
| **Stage 2 (Growth)** | 100 tenants | ~50,000 - 100,000 | **~$110.00 / month**<br>• Supabase Pro + compute add-on: $50<br>• Render Standard (2GB): $25<br>• Managed Redis (Upstash): $15<br>• Resend Pro: $20<br>• Cloudflare R2: ~$2 |

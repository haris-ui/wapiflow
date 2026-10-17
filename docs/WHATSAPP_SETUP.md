# Meta WhatsApp Cloud API Setup & Integration Guide

This guide walks through configuring the official Meta WhatsApp Cloud API (Graph API v20.0) for WapiFlow, from creating a Meta Developer App to registering webhooks and generating production System User access tokens.

---

## 1. Prerequisites

Before starting, ensure you have:
1. A **Facebook Personal Account** with two-factor authentication (2FA) enabled.
2. A verified **Meta Business Portfolio** (formerly Meta Business Manager).
3. A clean phone number capable of receiving SMS or voice calls (must not currently be registered on standard WhatsApp or WhatsApp Business mobile apps).

---

## 2. Meta Developer Account & App Creation

### Step 2.1: Register as a Meta Developer
1. Go to [developers.facebook.com](https://developers.facebook.com/) and log in.
2. Click **Get Started** or **My Apps** -> **Create App**.

### Step 2.2: Select App Type & Use Case
1. Choose **Other** as the app use case, click **Next**.
2. Select **Business** as the app type, click **Next**.
3. Fill in details:
   - **App Display Name**: `WapiFlow Production` (or your staging name)
   - **App Contact Email**: Your technical notification email
   - **Business Account**: Select your verified Meta Business Portfolio
4. Click **Create App** and complete the security prompt.

### Step 2.3: Add WhatsApp Product
1. In the App Dashboard left sidebar, find **Add Products to Your App**.
2. Locate the **WhatsApp** card and click **Set Up**.
3. Under the WhatsApp sidebar menu, select **API Setup** (or Quickstart).

---

## 3. WhatsApp Business Account (WABA) & Phone Number

### Step 3.1: Understanding Test vs Production Numbers
- **Meta Test Phone Number**: Meta provides a pre-configured test phone number with 5 test recipient slots. Useful for development before your company phone number is verified.
- **Production Phone Number**:
  1. Go to WhatsApp -> **API Setup** -> **Step 5: Add a phone number**.
  2. Enter your business phone number.
  3. Verify via 6-digit SMS code or voice call.
  4. Create a 6-digit registration PIN (save this securely).

> [!WARNING]
> If a phone number is currently active on the WhatsApp consumer app or WhatsApp Business mobile app, you **must delete the WhatsApp account from the mobile app** before registering it with the Cloud API. Once registered with Cloud API, the number operates exclusively via API/SaaS.

---

## 4. System User & Permanent Access Token

By default, the Graph API Explorer provides temporary access tokens that expire after 24 hours. For WapiFlow SaaS production, you must generate a permanent System User token.

### Step 4.1: Create System User
1. Open [Meta Business Settings](https://business.facebook.com/settings).
2. In the left navigation, go to **Users** -> **System Users**.
3. Click **Add**.
4. Enter System User Name (e.g., `wapiflow-api-integration`).
5. Role: **Admin System User**. Click **Create System User**.

### Step 4.2: Assign Assets & Permissions
1. Select the newly created system user and click **Assign Assets**.
2. Choose **Apps** -> Select `WapiFlow Production` -> Enable **Full Control (Manage App)**.
3. Choose **WhatsApp Business Accounts** -> Select your WABA -> Enable **Full Control (Manage WhatsApp Business Account)**.
4. Click **Save Changes**.

### Step 4.3: Generate Permanent Token
1. Click **Generate New Token**.
2. Select your App: `WapiFlow Production`.
3. Set Token Expiration: **Never** (or maximum allowable).
4. Select the required permission scopes:
   - `whatsapp_business_messaging` (Required: send & receive messages, templates, media)
   - `whatsapp_business_management` (Required: manage templates, numbers, profile)
5. Click **Generate Token**.
6. Copy the token immediately and save it in your secure vault. This will be stored per-tenant in WapiFlow.

---

## 5. Webhook Configuration

Meta Cloud API sends HTTP POST requests to WapiFlow for incoming customer messages, interactive button replies, and delivery receipts (sent, delivered, read).

### Step 5.1: Webhook Endpoint URL & Verify Token
In your WapiFlow deployment (or ngrok / cloudflare tunnel for local testing):
- **Callback URL**: `https://api.yourdomain.com/api/v1/webhooks/whatsapp`
- **Verify Token**: A strong random string matching your `.env` `META_VERIFY_TOKEN` (e.g., `wpf_vfy_9a87d6e5c4b3a2`).

### Step 5.2: Verification Handshake (GET Request)
When you submit the webhook URL in Meta Dashboard, Meta immediately fires an HTTP GET request to verify ownership:

```http
GET /api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=1158201444&hub.verify_token=wpf_vfy_9a87d6e5c4b3a2
```

FastAPI validates that `hub.verify_token` matches `META_VERIFY_TOKEN` and responds with the raw `hub.challenge` integer in plaintext with HTTP 200.

### Step 5.3: Webhook Field Subscriptions
In the WhatsApp Webhook settings page:
1. Click **Subscribe** on the **`messages`** webhook field. This captures:
   - Inbound text, image, audio, document, and video messages
   - Interactive reply button taps and list choices
   - Message status updates: `sent`, `delivered`, `read`, `failed`
2. Optional: Subscribe to `message_template_status_update` to monitor template approval events automatically.

---

## 6. Message Templates Setup

Outside the 24-hour service conversation window, outbound messages can only be sent using approved Meta Message Templates.

### Step 6.1: Create Templates in Meta WhatsApp Manager
1. Navigate to **WhatsApp Manager** -> **Account Tools** -> **Message Templates**.
2. Click **Create Template**.
3. Choose Category:
   - **Utility**: Order confirmation, delivery status, appointment reminders.
   - **Marketing**: Special discounts, seasonal promotions.
   - **Authentication**: Verification codes.

### Step 6.2: Example Order Confirmation Template (Utility)
- **Template Name**: `order_confirmation_v1`
- **Language**: `en_US`
- **Body**:
  ```text
  Hello {{1}}, your order #{{2}} for {{3}} has been confirmed!
  Total: {{4}}
  We will notify you once your order is dispatched.
  ```
- **Buttons (Quick Reply)**:
  - `Track Order`
  - `Contact Support`

Templates are reviewed automatically by Meta's AI; utility templates are typically approved within 1-5 minutes.

---

## 7. Verifying Webhook Ingestion Locally

Use the following `curl` command to simulate a valid Meta webhook notification against your local backend:

```bash
# Generate HMAC signature for test payload
SECRET="your_meta_app_secret_hash"
PAYLOAD='{"object":"whatsapp_business_account","entry":[{"id":"100000000000","changes":[{"value":{"messaging_product":"whatsapp","metadata":{"display_phone_number":"15550001111","phone_number_id":"200000000000"},"contacts":[{"profile":{"name":"Alex Customer"},"wa_id":"15551234567"}],"messages":[{"from":"15551234567","id":"wamid.HBgLMTU1NTEyMzQ1NjcVAgASGBgyMjhB","timestamp":"1735700000","text":{"body":"Hi, I would like to place an order"},"type":"text"}]},"field":"messages"}]}]}'

SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

curl -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

Expected response: `HTTP 200 OK` with JSON `{"status": "queued"}`.

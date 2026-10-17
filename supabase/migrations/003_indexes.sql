-- =============================================================================
-- Migration: 003_indexes.sql
-- Description: Performance and uniqueness indexes for WapiFlow.
-- Optimizes multi-tenant lookups, filtering, ordering, and background worker queues.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Orders Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_orders_business_status 
    ON public.orders (business_id, status);

CREATE INDEX IF NOT EXISTS idx_orders_business_created_at 
    ON public.orders (business_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_business_customer 
    ON public.orders (business_id, customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_idempotency_key 
    ON public.orders (idempotency_key) 
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_orders_business_order_number 
    ON public.orders (business_id, order_number);

CREATE INDEX IF NOT EXISTS idx_orders_conversation 
    ON public.orders (conversation_id) 
    WHERE conversation_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- 2. Order Items Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_order_items_order_id 
    ON public.order_items (order_id);

CREATE INDEX IF NOT EXISTS idx_order_items_business_product 
    ON public.order_items (business_id, product_id);

-- -----------------------------------------------------------------------------
-- 3. Products Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_products_business_active_archived 
    ON public.products (business_id, is_active, is_archived);

CREATE INDEX IF NOT EXISTS idx_products_business_sku 
    ON public.products (business_id, sku);

CREATE INDEX IF NOT EXISTS idx_products_business_category 
    ON public.products (business_id, category_id);

-- -----------------------------------------------------------------------------
-- 4. Customers Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_customers_business_phone 
    ON public.customers (business_id, phone);

CREATE INDEX IF NOT EXISTS idx_customers_business_whatsapp 
    ON public.customers (business_id, whatsapp_id) 
    WHERE whatsapp_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- 5. Messages Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created_at 
    ON public.messages (conversation_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_messages_wa_message_id 
    ON public.messages (wa_message_id) 
    WHERE wa_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_messages_business_created_at 
    ON public.messages (business_id, created_at DESC);

-- -----------------------------------------------------------------------------
-- 6. Conversations Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_conversations_business_status_last_msg 
    ON public.conversations (business_id, status, last_message_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_conversations_business_customer 
    ON public.conversations (business_id, customer_id);

CREATE INDEX IF NOT EXISTS idx_conversations_wa_convo_id 
    ON public.conversations (wa_conversation_id) 
    WHERE wa_conversation_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- 7. Webhook Events Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_webhook_events_wa_message_id 
    ON public.webhook_events (wa_message_id) 
    WHERE wa_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_webhook_events_processing_status_received 
    ON public.webhook_events (processing_status, received_at ASC);

-- -----------------------------------------------------------------------------
-- 8. Inventory Movements Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_inventory_movements_business_product_created 
    ON public.inventory_movements (business_id, product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_inventory_movements_order 
    ON public.inventory_movements (order_id) 
    WHERE order_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- 9. Audit Logs Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_audit_logs_business_created_at 
    ON public.audit_logs (business_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_resource 
    ON public.audit_logs (resource_type, resource_id);

-- -----------------------------------------------------------------------------
-- 10. Daily Business Metrics Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_daily_business_metrics_business_date 
    ON public.daily_business_metrics (business_id, date DESC);

-- -----------------------------------------------------------------------------
-- 11. Business Members Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_business_members_user_business 
    ON public.business_members (user_id, business_id);

CREATE INDEX IF NOT EXISTS idx_business_members_business_user 
    ON public.business_members (business_id, user_id);

-- -----------------------------------------------------------------------------
-- 12. Supporting Operational Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_invitations_token 
    ON public.invitations (token);

CREATE INDEX IF NOT EXISTS idx_invitations_business 
    ON public.invitations (business_id);

CREATE INDEX IF NOT EXISTS idx_product_images_product_sort 
    ON public.product_images (product_id, sort_order ASC);

CREATE INDEX IF NOT EXISTS idx_payments_order 
    ON public.payments (order_id);

CREATE INDEX IF NOT EXISTS idx_payments_business 
    ON public.payments (business_id);

CREATE INDEX IF NOT EXISTS idx_notification_jobs_status_scheduled 
    ON public.notification_jobs (business_id, status, scheduled_at ASC);

CREATE INDEX IF NOT EXISTS idx_whatsapp_phones_account 
    ON public.whatsapp_phone_numbers (whatsapp_account_id);

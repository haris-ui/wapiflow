-- =============================================================================
-- Migration: 005_reconcile_schema.sql
-- Description: Reconciles live Postgres schema with application models.
-- Ensures all columns queried by the backend ORM exist seamlessly.
-- =============================================================================

-- Profiles
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS phone_number TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- Businesses
ALTER TABLE public.businesses ADD COLUMN IF NOT EXISTS phone_number TEXT;

-- Business Settings
ALTER TABLE public.business_settings ADD COLUMN IF NOT EXISTS auto_decrement_stock BOOLEAN DEFAULT true;
ALTER TABLE public.business_settings ADD COLUMN IF NOT EXISTS notification_phone TEXT;
ALTER TABLE public.business_settings ADD COLUMN IF NOT EXISTS order_prefix TEXT DEFAULT 'ORD';
ALTER TABLE public.business_settings ADD COLUMN IF NOT EXISTS whatsapp_catalog_id TEXT;

-- Subscriptions
ALTER TABLE public.subscriptions ADD COLUMN IF NOT EXISTS plan_tier TEXT DEFAULT 'free';

-- Products
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS cost_price NUMERIC(12, 2);
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS track_inventory BOOLEAN DEFAULT true;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS compare_at_price NUMERIC(12, 2);

-- Inventory Movements
ALTER TABLE public.inventory_movements ADD COLUMN IF NOT EXISTS change_quantity INT DEFAULT 0;
ALTER TABLE public.inventory_movements ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Customers
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS phone_number TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS delivery_address TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS total_orders INT DEFAULT 0;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS total_spend NUMERIC(12, 2) DEFAULT 0;
UPDATE public.customers SET name = full_name WHERE name IS NULL AND full_name IS NOT NULL;
UPDATE public.customers SET phone_number = phone WHERE phone_number IS NULL AND phone IS NOT NULL;

-- Orders
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS total_amount NUMERIC(12, 2) DEFAULT 0;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS shipping_fee NUMERIC(12, 2) DEFAULT 0;
UPDATE public.orders SET total_amount = total WHERE total_amount = 0 AND total > 0;
UPDATE public.orders SET shipping_fee = shipping_amount WHERE shipping_fee = 0 AND shipping_amount > 0;
UPDATE public.orders SET source = source_channel WHERE source IS NULL AND source_channel IS NOT NULL;

-- Order Items
ALTER TABLE public.order_items ADD COLUMN IF NOT EXISTS total_price NUMERIC(12, 2) DEFAULT 0;
ALTER TABLE public.order_items ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
UPDATE public.order_items SET total_price = line_total WHERE total_price = 0 AND line_total > 0;

-- Order Status History
ALTER TABLE public.order_status_history ADD COLUMN IF NOT EXISTS previous_status TEXT;
ALTER TABLE public.order_status_history ADD COLUMN IF NOT EXISTS new_status TEXT;
ALTER TABLE public.order_status_history ADD COLUMN IF NOT EXISTS changed_by_user_id UUID;
ALTER TABLE public.order_status_history ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

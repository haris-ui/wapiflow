-- =============================================================================
-- WapiFlow Seed Data: supabase/seed.sql
-- Description: Deterministic mock data for local development and testing.
-- All UUIDs are fixed and structured for predictable test fixtures.
-- =============================================================================

-- Ensure cryptographic extension is present
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. Dev Auth Users (if running with Supabase Auth schema)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) THEN
        INSERT INTO auth.users (
            id,
            instance_id,
            aud,
            role,
            email,
            encrypted_password,
            email_confirmed_at,
            raw_app_meta_data,
            raw_user_meta_data,
            created_at,
            updated_at
        ) VALUES 
        (
            'a0000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            'owner@wapiflow.dev',
            crypt('Password123!', gen_salt('bf')),
            NOW(),
            '{"provider":"email","providers":["email"]}'::jsonb,
            '{"full_name":"Alex Mercer", "avatar_url":"https://images.unsplash.com/photo-1534528741775-53994a69daeb"}'::jsonb,
            NOW(),
            NOW()
        ),
        (
            'a0000000-0000-0000-0000-000000000002',
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            'manager@wapiflow.dev',
            crypt('Password123!', gen_salt('bf')),
            NOW(),
            '{"provider":"email","providers":["email"]}'::jsonb,
            '{"full_name":"Sarah Chen", "avatar_url":"https://images.unsplash.com/photo-1517841905240-472988babdf9"}'::jsonb,
            NOW(),
            NOW()
        ),
        (
            'a0000000-0000-0000-0000-000000000003',
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            'staff@wapiflow.dev',
            crypt('Password123!', gen_salt('bf')),
            NOW(),
            '{"provider":"email","providers":["email"]}'::jsonb,
            '{"full_name":"Marcus Brody", "avatar_url":"https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d"}'::jsonb,
            NOW(),
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 2. Profiles
-- -----------------------------------------------------------------------------
INSERT INTO public.profiles (
    id, full_name, avatar_url, email, phone, created_at, updated_at
) VALUES 
(
    'a0000000-0000-0000-0000-000000000001',
    'Alex Mercer',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb',
    'owner@wapiflow.dev',
    '+15551000001',
    NOW(),
    NOW()
),
(
    'a0000000-0000-0000-0000-000000000002',
    'Sarah Chen',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9',
    'manager@wapiflow.dev',
    '+15551000002',
    NOW(),
    NOW()
),
(
    'a0000000-0000-0000-0000-000000000003',
    'Marcus Brody',
    'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d',
    'staff@wapiflow.dev',
    '+15551000003',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    full_name = EXCLUDED.full_name,
    avatar_url = EXCLUDED.avatar_url,
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    updated_at = NOW();

-- -----------------------------------------------------------------------------
-- 3. Business (Tenant)
-- -----------------------------------------------------------------------------
INSERT INTO public.businesses (
    id,
    name,
    slug,
    logo_url,
    description,
    email,
    phone,
    website,
    currency,
    timezone,
    address,
    order_number_prefix,
    order_number_counter,
    is_active,
    created_at,
    updated_at
) VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'Artisan Coffee Roasters',
    'artisan-coffee',
    'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd',
    'Specialty coffee and fresh pastries delivered straight via WhatsApp.',
    'hello@artisancoffee.dev',
    '+15550001234',
    'https://artisancoffee.dev',
    'USD',
    'America/New_York',
    '{"street": "123 Bean St", "city": "Brooklyn", "state": "NY", "postal_code": "11201", "country": "US"}'::jsonb,
    'ORD',
    1,
    true,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    slug = EXCLUDED.slug,
    updated_at = NOW();

-- -----------------------------------------------------------------------------
-- 4. Business Members
-- -----------------------------------------------------------------------------
INSERT INTO public.business_members (
    id, business_id, user_id, role, is_active, joined_at, created_at, updated_at
) VALUES 
(
    'b0000000-0000-0000-0000-000000000011',
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'owner',
    true,
    NOW(),
    NOW(),
    NOW()
),
(
    'b0000000-0000-0000-0000-000000000012',
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000002',
    'manager',
    true,
    NOW(),
    NOW(),
    NOW()
),
(
    'b0000000-0000-0000-0000-000000000013',
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000003',
    'staff',
    true,
    NOW(),
    NOW(),
    NOW()
)
ON CONFLICT (business_id, user_id) DO UPDATE SET
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- -----------------------------------------------------------------------------
-- 5. Business Settings & Subscriptions
-- -----------------------------------------------------------------------------
INSERT INTO public.business_settings (
    id, business_id, notifications_email, notifications_whatsapp, low_stock_threshold, auto_reply_enabled, created_at, updated_at
) VALUES (
    'b1000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    true,
    true,
    5,
    true,
    NOW(),
    NOW()
)
ON CONFLICT (business_id) DO NOTHING;

INSERT INTO public.subscriptions (
    id, business_id, plan, status, current_period_start, current_period_end, created_at, updated_at
) VALUES (
    'b2000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'pro',
    'active',
    NOW(),
    NOW() + INTERVAL '1 year',
    NOW(),
    NOW()
)
ON CONFLICT (business_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 6. WhatsApp Account & Phone Number
-- -----------------------------------------------------------------------------
INSERT INTO public.whatsapp_accounts (
    id, business_id, waba_id, app_id, access_token, token_expires_at, status, webhook_verified_at, created_at, updated_at
) VALUES (
    'w0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'waba_demo_1092837465',
    'app_demo_99887766',
    'EAAGmocktoken_production_grade_encrypted_placeholder_dev_only',
    NOW() + INTERVAL '60 days',
    'connected',
    NOW(),
    NOW(),
    NOW()
)
ON CONFLICT (business_id) DO NOTHING;

INSERT INTO public.whatsapp_phone_numbers (
    id, business_id, whatsapp_account_id, phone_number, display_name, quality_rating, status, is_primary, created_at, updated_at
) VALUES (
    'w1000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'w0000000-0000-0000-0000-000000000001',
    '+15557788990',
    'Artisan Coffee Order Desk',
    'GREEN',
    'verified',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 7. Product Categories
-- -----------------------------------------------------------------------------
INSERT INTO public.product_categories (
    id, business_id, name, slug, description, is_active, created_at, updated_at
) VALUES 
(
    'c0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'Cold Brews & Iced',
    'cold-brews',
    'Slow steeped cold brew and iced beverages',
    true,
    NOW(),
    NOW()
),
(
    'c0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000001',
    'Whole Bean Coffee',
    'whole-bean',
    'Freshly roasted single origin and signature blend beans',
    true,
    NOW(),
    NOW()
),
(
    'c0000000-0000-0000-0000-000000000003',
    'b0000000-0000-0000-0000-000000000001',
    'Fresh Bakery',
    'fresh-bakery',
    'Daily baked butter pastries and treats',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 8. Products
-- -----------------------------------------------------------------------------
INSERT INTO public.products (
    id, business_id, category_id, name, description, sku, price, currency, stock_quantity, low_stock_threshold, is_active, is_archived, image_url, metadata, created_at, updated_at
) VALUES 
(
    'd0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'c0000000-0000-0000-0000-000000000001',
    'Signature Nitro Cold Brew (16oz)',
    '18-hour steeped Ethiopian Yirgacheffe served velvety smooth.',
    'BEV-NITRO-16',
    4.50,
    'USD',
    45,
    5,
    true,
    false,
    'https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5',
    '{"serving_temp": "chilled", "volume_ml": 473}'::jsonb,
    NOW(),
    NOW()
),
(
    'd0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000002',
    'c0000000-0000-0000-0000-000000000002',
    'Guatemala Antigua Whole Bean (12oz)',
    'Notes of milk chocolate, candied pecan, and crisp red apple.',
    'BEAN-GUAT-12',
    16.00,
    'USD',
    25,
    5,
    true,
    false,
    'https://images.unsplash.com/photo-1587734195503-904fca47e0e9',
    '{"roast_level": "medium", "weight_oz": 12}'::jsonb,
    NOW(),
    NOW()
),
(
    'd0000000-0000-0000-0000-000000000003',
    'b0000000-0000-0000-0000-000000000003',
    'c0000000-0000-0000-0000-000000000003',
    'Artisan Butter Croissant',
    'Flaky, golden French butter croissant baked fresh each morning.',
    'BAK-CROIS-01',
    3.75,
    'USD',
    30,
    5,
    true,
    false,
    'https://images.unsplash.com/photo-1555507036-ab1f4038808a',
    '{"allergens": ["gluten", "dairy"]}'::jsonb,
    NOW(),
    NOW()
),
(
    'd0000000-0000-0000-0000-000000000004',
    'b0000000-0000-0000-0000-000000000003',
    'c0000000-0000-0000-0000-000000000003',
    'Almond Frangipane Croissant',
    'Double-baked pastry filled with rich almond frangipane cream.',
    'BAK-ALM-02',
    4.25,
    'USD',
    3, -- Below threshold: triggers low stock alert state
    5,
    true,
    false,
    'https://images.unsplash.com/photo-1509440159596-0249088772ff',
    '{"allergens": ["gluten", "dairy", "tree nuts"]}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    price = EXCLUDED.price,
    stock_quantity = EXCLUDED.stock_quantity,
    updated_at = NOW();

-- -----------------------------------------------------------------------------
-- 9. Product Images
-- -----------------------------------------------------------------------------
INSERT INTO public.product_images (
    id, product_id, business_id, url, r2_key, is_primary, sort_order, created_at
) VALUES 
(
    'd1000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5',
    'businesses/b000/products/coldbrew_primary.jpg',
    true,
    0,
    NOW()
),
(
    'd1000000-0000-0000-0000-000000000002',
    'd0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000001',
    'https://images.unsplash.com/photo-1587734195503-904fca47e0e9',
    'businesses/b000/products/guat_beans.jpg',
    true,
    0,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 10. Initial Stock Movements
-- -----------------------------------------------------------------------------
INSERT INTO public.inventory_movements (
    id, business_id, product_id, order_id, movement_type, quantity_delta, quantity_before, quantity_after, notes, performed_by, created_at
) VALUES 
(
    'i0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    NULL,
    'initial',
    47,
    0,
    47,
    'Initial inventory intake for dev demo',
    'a0000000-0000-0000-0000-000000000001',
    NOW() - INTERVAL '2 days'
),
(
    'i0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000003',
    NULL,
    'initial',
    31,
    0,
    31,
    'Morning bakery production batch',
    'a0000000-0000-0000-0000-000000000001',
    NOW() - INTERVAL '2 days'
)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 11. Customers
-- -----------------------------------------------------------------------------
INSERT INTO public.customers (
    id, business_id, full_name, phone, email, whatsapp_id, notes, tags, is_blocked, created_at, updated_at
) VALUES 
(
    'e0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'Alice Johnson',
    '+12025550143',
    'alice.j@example.com',
    '12025550143',
    'Loyal customer, prefers oat milk in espresso drinks.',
    ARRAY['vip', 'coffee-lover'],
    false,
    NOW() - INTERVAL '5 days',
    NOW()
),
(
    'e0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000001',
    'Bob Miller',
    '+12025550188',
    'bob.miller@example.com',
    '12025550188',
    'Office bulk order inquiry contact.',
    ARRAY['corporate'],
    false,
    NOW() - INTERVAL '3 days',
    NOW()
)
ON CONFLICT (business_id, phone) DO UPDATE SET
    full_name = EXCLUDED.full_name,
    email = EXCLUDED.email,
    updated_at = NOW();

-- -----------------------------------------------------------------------------
-- 12. Conversations & Messages
-- -----------------------------------------------------------------------------
INSERT INTO public.conversations (
    id, business_id, customer_id, whatsapp_phone_number_id, wa_conversation_id, status, assigned_to, unread_count, last_message_at, last_message_preview, created_at, updated_at
) VALUES (
    'f0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'e0000000-0000-0000-0000-000000000001',
    'w1000000-0000-0000-0000-000000000001',
    'wamid.HBgLMTIwMjU1NTAxNDM',
    'open',
    'a0000000-0000-0000-0000-000000000002',
    0,
    NOW(),
    'Your order ORD-00001 is confirmed and preparing!',
    NOW() - INTERVAL '1 hour',
    NOW()
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.messages (
    id, conversation_id, business_id, wa_message_id, direction, message_type, content, status, sent_by, is_internal_note, metadata, created_at, updated_at
) VALUES 
(
    'm0000000-0000-0000-0000-000000000001',
    'f0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'wamid.ABGG0123456789inbound',
    'inbound',
    'text',
    'Hi! I would like to order 2 nitro cold brews and 1 butter croissant for pickup please.',
    'read',
    NULL,
    false,
    '{}'::jsonb,
    NOW() - INTERVAL '45 minutes',
    NOW() - INTERVAL '45 minutes'
),
(
    'm0000000-0000-0000-0000-000000000002',
    'f0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'wamid.ABGG0123456789outbound',
    'outbound',
    'text',
    'Hello Alice! Your order ORD-00001 is confirmed and preparing. Total is $12.75. We will text you when it is ready!',
    'delivered',
    'a0000000-0000-0000-0000-000000000002',
    false,
    '{}'::jsonb,
    NOW() - INTERVAL '30 minutes',
    NOW() - INTERVAL '30 minutes'
)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 13. Orders, Line Items, and Status History
-- -----------------------------------------------------------------------------
INSERT INTO public.orders (
    id,
    business_id,
    customer_id,
    order_number,
    status,
    payment_status,
    currency,
    subtotal,
    discount_amount,
    tax_amount,
    shipping_amount,
    total,
    notes,
    source_channel,
    conversation_id,
    fulfillment_address,
    assigned_to,
    created_by,
    created_at,
    updated_at
) VALUES (
    'o0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'e0000000-0000-0000-0000-000000000001',
    'ORD-00001',
    'preparing',
    'paid',
    'USD',
    12.75,
    0.00,
    0.00,
    0.00,
    12.75,
    'Customer requested eco-friendly packaging if possible.',
    'whatsapp',
    'f0000000-0000-0000-0000-000000000001',
    '{"type": "pickup", "location": "Main Store Brooklyn"}'::jsonb,
    'a0000000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000002',
    NOW() - INTERVAL '40 minutes',
    NOW()
)
ON CONFLICT (business_id, order_number) DO UPDATE SET
    status = EXCLUDED.status,
    payment_status = EXCLUDED.payment_status,
    total = EXCLUDED.total,
    updated_at = NOW();

INSERT INTO public.order_items (
    id, order_id, business_id, product_id, product_name, product_sku, unit_price, quantity, discount_amount, tax_amount, line_total, metadata, created_at
) VALUES 
(
    'oi000000-0000-0000-0000-000000000001',
    'o0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    'Signature Nitro Cold Brew (16oz)',
    'BEV-NITRO-16',
    4.50,
    2,
    0.00,
    0.00,
    9.00,
    '{}'::jsonb,
    NOW() - INTERVAL '40 minutes'
),
(
    'oi000000-0000-0000-0000-000000000002',
    'o0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000003',
    'Artisan Butter Croissant',
    'BAK-CROIS-01',
    3.75,
    1,
    0.00,
    0.00,
    3.75,
    '{}'::jsonb,
    NOW() - INTERVAL '40 minutes'
)
ON CONFLICT (id) DO NOTHING;

-- Order status lifecycle records
INSERT INTO public.order_status_history (
    id, order_id, business_id, from_status, to_status, changed_by, notes, created_at
) VALUES 
(
    'h0000000-0000-0000-0000-000000000001',
    'o0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    NULL,
    'pending',
    'a0000000-0000-0000-0000-000000000002',
    'Created from incoming WhatsApp conversation message',
    NOW() - INTERVAL '40 minutes'
),
(
    'h0000000-0000-0000-0000-000000000002',
    'o0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'pending',
    'confirmed',
    'a0000000-0000-0000-0000-000000000002',
    'Order accepted and payment verified',
    NOW() - INTERVAL '35 minutes'
),
(
    'h0000000-0000-0000-0000-000000000003',
    'o0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    'confirmed',
    'preparing',
    'a0000000-0000-0000-0000-000000000003',
    'Barista began beverage preparation',
    NOW() - INTERVAL '25 minutes'
)
ON CONFLICT (id) DO NOTHING;

-- Record payment for order ORD-00001
INSERT INTO public.payments (
    id, order_id, business_id, amount, currency, payment_method, reference, status, recorded_by, created_at
) VALUES (
    'p0000000-0000-0000-0000-000000000001',
    'o0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    12.75,
    'USD',
    'stripe_payment_link',
    'pi_mock_1234567890abcdef',
    'completed',
    'a0000000-0000-0000-0000-000000000002',
    NOW() - INTERVAL '35 minutes'
)
ON CONFLICT (id) DO NOTHING;

-- Sales inventory decrement deduction
INSERT INTO public.inventory_movements (
    id, business_id, product_id, order_id, movement_type, quantity_delta, quantity_before, quantity_after, notes, performed_by, created_at
) VALUES 
(
    'i0000000-0000-0000-0000-000000000011',
    'b0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000001',
    'o0000000-0000-0000-0000-000000000001',
    'sale',
    -2,
    47,
    45,
    'Deduction for order ORD-00001',
    'a0000000-0000-0000-0000-000000000002',
    NOW() - INTERVAL '35 minutes'
),
(
    'i0000000-0000-0000-0000-000000000012',
    'b0000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000003',
    'o0000000-0000-0000-0000-000000000001',
    'sale',
    -1,
    31,
    30,
    'Deduction for order ORD-00001',
    'a0000000-0000-0000-0000-000000000002',
    NOW() - INTERVAL '35 minutes'
)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 14. Daily Business Metrics
-- -----------------------------------------------------------------------------
INSERT INTO public.daily_business_metrics (
    id,
    business_id,
    date,
    orders_total,
    orders_pending,
    orders_completed,
    orders_cancelled,
    revenue_gross,
    revenue_paid,
    messages_inbound,
    messages_outbound,
    new_customers,
    created_at,
    updated_at
) VALUES (
    'k0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001',
    CURRENT_DATE,
    1,
    1,
    0,
    0,
    12.75,
    12.75,
    1,
    1,
    1,
    NOW(),
    NOW()
)
ON CONFLICT (business_id, date) DO UPDATE SET
    orders_total = EXCLUDED.orders_total,
    revenue_gross = EXCLUDED.revenue_gross,
    revenue_paid = EXCLUDED.revenue_paid,
    updated_at = NOW();

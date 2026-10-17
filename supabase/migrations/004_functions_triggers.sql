-- =============================================================================
-- Migration: 004_functions_triggers.sql
-- Description: Core business logic functions, triggers, and automated workflows.
-- Includes:
-- 1. update_updated_at() trigger on all tables with updated_at
-- 2. generate_order_number(business_id UUID) atomic counter generator
-- 3. calculate_order_total(order_id UUID) subtotal & total recalculator
-- 4. handle_new_user() trigger on auth.users for profile creation
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Timestamp Auto-Update Function & Triggers
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Apply to profiles
DROP TRIGGER IF EXISTS trg_profiles_updated_at ON public.profiles;
CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to businesses
DROP TRIGGER IF EXISTS trg_businesses_updated_at ON public.businesses;
CREATE TRIGGER trg_businesses_updated_at
    BEFORE UPDATE ON public.businesses
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to business_members
DROP TRIGGER IF EXISTS trg_business_members_updated_at ON public.business_members;
CREATE TRIGGER trg_business_members_updated_at
    BEFORE UPDATE ON public.business_members
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to business_settings
DROP TRIGGER IF EXISTS trg_business_settings_updated_at ON public.business_settings;
CREATE TRIGGER trg_business_settings_updated_at
    BEFORE UPDATE ON public.business_settings
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to subscriptions
DROP TRIGGER IF EXISTS trg_subscriptions_updated_at ON public.subscriptions;
CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to product_categories
DROP TRIGGER IF EXISTS trg_product_categories_updated_at ON public.product_categories;
CREATE TRIGGER trg_product_categories_updated_at
    BEFORE UPDATE ON public.product_categories
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to products
DROP TRIGGER IF EXISTS trg_products_updated_at ON public.products;
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON public.products
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to customers
DROP TRIGGER IF EXISTS trg_customers_updated_at ON public.customers;
CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON public.customers
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to whatsapp_accounts
DROP TRIGGER IF EXISTS trg_whatsapp_accounts_updated_at ON public.whatsapp_accounts;
CREATE TRIGGER trg_whatsapp_accounts_updated_at
    BEFORE UPDATE ON public.whatsapp_accounts
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to whatsapp_phone_numbers
DROP TRIGGER IF EXISTS trg_whatsapp_phone_numbers_updated_at ON public.whatsapp_phone_numbers;
CREATE TRIGGER trg_whatsapp_phone_numbers_updated_at
    BEFORE UPDATE ON public.whatsapp_phone_numbers
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to conversations
DROP TRIGGER IF EXISTS trg_conversations_updated_at ON public.conversations;
CREATE TRIGGER trg_conversations_updated_at
    BEFORE UPDATE ON public.conversations
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to orders
DROP TRIGGER IF EXISTS trg_orders_updated_at ON public.orders;
CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON public.orders
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to messages
DROP TRIGGER IF EXISTS trg_messages_updated_at ON public.messages;
CREATE TRIGGER trg_messages_updated_at
    BEFORE UPDATE ON public.messages
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- Apply to daily_business_metrics
DROP TRIGGER IF EXISTS trg_daily_business_metrics_updated_at ON public.daily_business_metrics;
CREATE TRIGGER trg_daily_business_metrics_updated_at
    BEFORE UPDATE ON public.daily_business_metrics
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- -----------------------------------------------------------------------------
-- 2. Atomic Order Number Generator
-- Format: {order_number_prefix}-{zero_padded_counter} (e.g. ORD-00001)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.generate_order_number(p_business_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_prefix TEXT;
    v_counter INT;
    v_order_number TEXT;
BEGIN
    UPDATE public.businesses
    SET order_number_counter = order_number_counter + 1,
        updated_at = NOW()
    WHERE id = p_business_id
    RETURNING COALESCE(NULLIF(TRIM(order_number_prefix), ''), 'ORD'), order_number_counter
    INTO v_prefix, v_counter;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Business not found with id %', p_business_id;
    END IF;

    v_order_number := v_prefix || '-' || LPAD(v_counter::TEXT, 5, '0');
    RETURN v_order_number;
END;
$$;

-- Trigger to auto-assign order_number if not provided on order creation
CREATE OR REPLACE FUNCTION public.set_order_number_before_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.order_number IS NULL OR TRIM(NEW.order_number) = '' THEN
        NEW.order_number := public.generate_order_number(NEW.business_id);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_orders_auto_order_number ON public.orders;
CREATE TRIGGER trg_orders_auto_order_number
    BEFORE INSERT ON public.orders
    FOR EACH ROW
    EXECUTE FUNCTION public.set_order_number_before_insert();

-- -----------------------------------------------------------------------------
-- 3. Calculate Order Total from Order Items
-- Computes subtotal from line_total, accounts for discounts, taxes, and shipping
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calculate_order_total(p_order_id UUID)
RETURNS NUMERIC(12, 2)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_subtotal NUMERIC(12, 2);
    v_discount NUMERIC(12, 2);
    v_tax NUMERIC(12, 2);
    v_shipping NUMERIC(12, 2);
    v_final_total NUMERIC(12, 2);
BEGIN
    -- Sum line_total from items
    SELECT COALESCE(SUM(line_total), 0.00)
    INTO v_subtotal
    FROM public.order_items
    WHERE order_id = p_order_id;

    -- Retrieve order-level discount, tax, and shipping amounts
    SELECT 
        COALESCE(discount_amount, 0.00),
        COALESCE(tax_amount, 0.00),
        COALESCE(shipping_amount, 0.00)
    INTO v_discount, v_tax, v_shipping
    FROM public.orders
    WHERE id = p_order_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Order not found with id %', p_order_id;
    END IF;

    -- Calculate total: subtotal - discount + tax + shipping (cannot be negative)
    v_final_total := GREATEST(0.00, v_subtotal - v_discount + v_tax + v_shipping);

    UPDATE public.orders
    SET subtotal = v_subtotal,
        total = v_final_total,
        updated_at = NOW()
    WHERE id = p_order_id;

    RETURN v_final_total;
END;
$$;

-- Trigger to automatically recalculate order total when items change
CREATE OR REPLACE FUNCTION public.trg_fn_order_items_recalc()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_target_order_id UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_target_order_id := OLD.order_id;
    ELSE
        v_target_order_id := NEW.order_id;
    END IF;

    PERFORM public.calculate_order_total(v_target_order_id);
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_order_items_recalculate ON public.order_items;
CREATE TRIGGER trg_order_items_recalculate
    AFTER INSERT OR UPDATE OR DELETE ON public.order_items
    FOR EACH ROW
    EXECUTE FUNCTION public.trg_fn_order_items_recalc();

-- -----------------------------------------------------------------------------
-- 4. Auth New User Handler (Creates public.profiles on auth.users signup)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (
        id,
        full_name,
        avatar_url,
        email,
        phone,
        created_at,
        updated_at
    )
    VALUES (
        NEW.id,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            NEW.raw_user_meta_data->>'name',
            ''
        ),
        NEW.raw_user_meta_data->>'avatar_url',
        NEW.email,
        NEW.phone,
        NOW(),
        NOW()
    )
    ON CONFLICT (id) DO UPDATE
    SET
        full_name = CASE 
            WHEN EXCLUDED.full_name <> '' THEN EXCLUDED.full_name 
            ELSE public.profiles.full_name 
        END,
        avatar_url = COALESCE(EXCLUDED.avatar_url, public.profiles.avatar_url),
        email = COALESCE(EXCLUDED.email, public.profiles.email),
        phone = COALESCE(EXCLUDED.phone, public.profiles.phone),
        updated_at = NOW();

    RETURN NEW;
END;
$$;

-- Safely attach trigger to auth.users if the auth schema exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) THEN
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW
            EXECUTE FUNCTION public.handle_new_user();
    END IF;
END $$;

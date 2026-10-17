-- =============================================================================
-- Migration: 002_rls_policies.sql
-- Description: Row Level Security (RLS) policies for multi-tenant isolation.
-- Enforces tenant separation via business_members and auth.uid().
-- Includes service_role bypass policy on all tables.
-- =============================================================================

-- Helper functions for RLS checks (SECURITY DEFINER prevents recursion)
CREATE OR REPLACE FUNCTION public.current_user_business_ids()
RETURNS SETOF UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT business_id
    FROM public.business_members
    WHERE user_id = auth.uid()
      AND is_active = true;
$$;

CREATE OR REPLACE FUNCTION public.has_business_role(target_business_id UUID, allowed_roles TEXT[])
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.business_members
        WHERE business_id = target_business_id
          AND user_id = auth.uid()
          AND is_active = true
          AND role = ANY(allowed_roles)
    );
$$;

-- =============================================================================
-- 1. profiles
-- =============================================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.profiles;
CREATE POLICY "service_role_bypass" ON public.profiles
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "profiles_select" ON public.profiles;
CREATE POLICY "profiles_select" ON public.profiles
    FOR SELECT USING (id = auth.uid());

DROP POLICY IF EXISTS "profiles_insert" ON public.profiles;
CREATE POLICY "profiles_insert" ON public.profiles
    FOR INSERT WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "profiles_update" ON public.profiles;
CREATE POLICY "profiles_update" ON public.profiles
    FOR UPDATE USING (id = auth.uid()) WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "profiles_delete" ON public.profiles;
CREATE POLICY "profiles_delete" ON public.profiles
    FOR DELETE USING (id = auth.uid());

-- =============================================================================
-- 2. businesses
-- =============================================================================
ALTER TABLE public.businesses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.businesses;
CREATE POLICY "service_role_bypass" ON public.businesses
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.businesses;
CREATE POLICY "tenant_select" ON public.businesses
    FOR SELECT USING (
        id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.businesses;
CREATE POLICY "tenant_insert" ON public.businesses
    FOR INSERT WITH CHECK (
        auth.uid() IS NOT NULL
    );

DROP POLICY IF EXISTS "tenant_update" ON public.businesses;
CREATE POLICY "tenant_update" ON public.businesses
    FOR UPDATE USING (
        id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    ) WITH CHECK (
        id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.businesses;
CREATE POLICY "tenant_delete" ON public.businesses
    FOR DELETE USING (
        id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role = 'owner'
        )
    );

-- =============================================================================
-- 3. business_members
-- =============================================================================
ALTER TABLE public.business_members ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.business_members;
CREATE POLICY "service_role_bypass" ON public.business_members
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.business_members;
CREATE POLICY "tenant_select" ON public.business_members
    FOR SELECT USING (
        user_id = auth.uid() OR
        business_id IN (SELECT public.current_user_business_ids())
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.business_members;
CREATE POLICY "tenant_insert" ON public.business_members
    FOR INSERT WITH CHECK (
        user_id = auth.uid() OR
        public.has_business_role(business_id, ARRAY['owner', 'manager'])
    );

DROP POLICY IF EXISTS "tenant_update" ON public.business_members;
CREATE POLICY "tenant_update" ON public.business_members
    FOR UPDATE USING (
        public.has_business_role(business_id, ARRAY['owner', 'manager'])
    ) WITH CHECK (
        public.has_business_role(business_id, ARRAY['owner', 'manager'])
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.business_members;
CREATE POLICY "tenant_delete" ON public.business_members
    FOR DELETE USING (
        public.has_business_role(business_id, ARRAY['owner'])
    );

-- =============================================================================
-- 4. invitations
-- =============================================================================
ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.invitations;
CREATE POLICY "service_role_bypass" ON public.invitations
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.invitations;
CREATE POLICY "tenant_select" ON public.invitations
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.invitations;
CREATE POLICY "tenant_insert" ON public.invitations
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.invitations;
CREATE POLICY "tenant_update" ON public.invitations
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.invitations;
CREATE POLICY "tenant_delete" ON public.invitations
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

-- =============================================================================
-- 5. business_settings
-- =============================================================================
ALTER TABLE public.business_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.business_settings;
CREATE POLICY "service_role_bypass" ON public.business_settings
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.business_settings;
CREATE POLICY "tenant_select" ON public.business_settings
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.business_settings;
CREATE POLICY "tenant_insert" ON public.business_settings
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.business_settings;
CREATE POLICY "tenant_update" ON public.business_settings
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.business_settings;
CREATE POLICY "tenant_delete" ON public.business_settings
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role = 'owner'
        )
    );

-- =============================================================================
-- 6. subscriptions
-- =============================================================================
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.subscriptions;
CREATE POLICY "service_role_bypass" ON public.subscriptions
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.subscriptions;
CREATE POLICY "tenant_select" ON public.subscriptions
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.subscriptions;
CREATE POLICY "tenant_insert" ON public.subscriptions
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role = 'owner'
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.subscriptions;
CREATE POLICY "tenant_update" ON public.subscriptions
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role = 'owner'
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role = 'owner'
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.subscriptions;
CREATE POLICY "tenant_delete" ON public.subscriptions
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role = 'owner'
        )
    );

-- =============================================================================
-- 7. product_categories
-- =============================================================================
ALTER TABLE public.product_categories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.product_categories;
CREATE POLICY "service_role_bypass" ON public.product_categories
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.product_categories;
CREATE POLICY "tenant_select" ON public.product_categories
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.product_categories;
CREATE POLICY "tenant_insert" ON public.product_categories
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.product_categories;
CREATE POLICY "tenant_update" ON public.product_categories
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.product_categories;
CREATE POLICY "tenant_delete" ON public.product_categories
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 8. products
-- =============================================================================
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.products;
CREATE POLICY "service_role_bypass" ON public.products
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.products;
CREATE POLICY "tenant_select" ON public.products
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.products;
CREATE POLICY "tenant_insert" ON public.products
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.products;
CREATE POLICY "tenant_update" ON public.products
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.products;
CREATE POLICY "tenant_delete" ON public.products
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 9. product_images
-- =============================================================================
ALTER TABLE public.product_images ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.product_images;
CREATE POLICY "service_role_bypass" ON public.product_images
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.product_images;
CREATE POLICY "tenant_select" ON public.product_images
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.product_images;
CREATE POLICY "tenant_insert" ON public.product_images
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.product_images;
CREATE POLICY "tenant_update" ON public.product_images
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.product_images;
CREATE POLICY "tenant_delete" ON public.product_images
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 10. inventory_movements
-- =============================================================================
ALTER TABLE public.inventory_movements ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.inventory_movements;
CREATE POLICY "service_role_bypass" ON public.inventory_movements
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.inventory_movements;
CREATE POLICY "tenant_select" ON public.inventory_movements
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.inventory_movements;
CREATE POLICY "tenant_insert" ON public.inventory_movements
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.inventory_movements;
CREATE POLICY "tenant_update" ON public.inventory_movements
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.inventory_movements;
CREATE POLICY "tenant_delete" ON public.inventory_movements
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 11. customers
-- =============================================================================
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.customers;
CREATE POLICY "service_role_bypass" ON public.customers
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.customers;
CREATE POLICY "tenant_select" ON public.customers
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.customers;
CREATE POLICY "tenant_insert" ON public.customers
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.customers;
CREATE POLICY "tenant_update" ON public.customers
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.customers;
CREATE POLICY "tenant_delete" ON public.customers
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 12. orders
-- =============================================================================
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.orders;
CREATE POLICY "service_role_bypass" ON public.orders
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.orders;
CREATE POLICY "tenant_select" ON public.orders
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.orders;
CREATE POLICY "tenant_insert" ON public.orders
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.orders;
CREATE POLICY "tenant_update" ON public.orders
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.orders;
CREATE POLICY "tenant_delete" ON public.orders
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 13. order_items
-- =============================================================================
ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.order_items;
CREATE POLICY "service_role_bypass" ON public.order_items
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.order_items;
CREATE POLICY "tenant_select" ON public.order_items
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.order_items;
CREATE POLICY "tenant_insert" ON public.order_items
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.order_items;
CREATE POLICY "tenant_update" ON public.order_items
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.order_items;
CREATE POLICY "tenant_delete" ON public.order_items
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 14. order_status_history
-- =============================================================================
ALTER TABLE public.order_status_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.order_status_history;
CREATE POLICY "service_role_bypass" ON public.order_status_history
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.order_status_history;
CREATE POLICY "tenant_select" ON public.order_status_history
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.order_status_history;
CREATE POLICY "tenant_insert" ON public.order_status_history
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.order_status_history;
CREATE POLICY "tenant_update" ON public.order_status_history
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.order_status_history;
CREATE POLICY "tenant_delete" ON public.order_status_history
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 15. payments
-- =============================================================================
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.payments;
CREATE POLICY "service_role_bypass" ON public.payments
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.payments;
CREATE POLICY "tenant_select" ON public.payments
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.payments;
CREATE POLICY "tenant_insert" ON public.payments
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.payments;
CREATE POLICY "tenant_update" ON public.payments
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.payments;
CREATE POLICY "tenant_delete" ON public.payments
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 16. whatsapp_accounts
-- =============================================================================
ALTER TABLE public.whatsapp_accounts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.whatsapp_accounts;
CREATE POLICY "service_role_bypass" ON public.whatsapp_accounts
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.whatsapp_accounts;
CREATE POLICY "tenant_select" ON public.whatsapp_accounts
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.whatsapp_accounts;
CREATE POLICY "tenant_insert" ON public.whatsapp_accounts
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.whatsapp_accounts;
CREATE POLICY "tenant_update" ON public.whatsapp_accounts
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.whatsapp_accounts;
CREATE POLICY "tenant_delete" ON public.whatsapp_accounts
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role = 'owner'
        )
    );

-- =============================================================================
-- 17. whatsapp_phone_numbers
-- =============================================================================
ALTER TABLE public.whatsapp_phone_numbers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.whatsapp_phone_numbers;
CREATE POLICY "service_role_bypass" ON public.whatsapp_phone_numbers
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.whatsapp_phone_numbers;
CREATE POLICY "tenant_select" ON public.whatsapp_phone_numbers
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.whatsapp_phone_numbers;
CREATE POLICY "tenant_insert" ON public.whatsapp_phone_numbers
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.whatsapp_phone_numbers;
CREATE POLICY "tenant_update" ON public.whatsapp_phone_numbers
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role IN ('owner', 'manager')
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.whatsapp_phone_numbers;
CREATE POLICY "tenant_delete" ON public.whatsapp_phone_numbers
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true AND role = 'owner'
        )
    );

-- =============================================================================
-- 18. conversations
-- =============================================================================
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.conversations;
CREATE POLICY "service_role_bypass" ON public.conversations
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.conversations;
CREATE POLICY "tenant_select" ON public.conversations
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.conversations;
CREATE POLICY "tenant_insert" ON public.conversations
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.conversations;
CREATE POLICY "tenant_update" ON public.conversations
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.conversations;
CREATE POLICY "tenant_delete" ON public.conversations
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 19. messages
-- =============================================================================
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.messages;
CREATE POLICY "service_role_bypass" ON public.messages
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.messages;
CREATE POLICY "tenant_select" ON public.messages
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.messages;
CREATE POLICY "tenant_insert" ON public.messages
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.messages;
CREATE POLICY "tenant_update" ON public.messages
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.messages;
CREATE POLICY "tenant_delete" ON public.messages
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 20. webhook_events
-- =============================================================================
ALTER TABLE public.webhook_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.webhook_events;
CREATE POLICY "service_role_bypass" ON public.webhook_events
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.webhook_events;
CREATE POLICY "tenant_select" ON public.webhook_events
    FOR SELECT USING (
        business_id IS NOT NULL AND business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.webhook_events;
CREATE POLICY "tenant_insert" ON public.webhook_events
    FOR INSERT WITH CHECK (
        business_id IS NULL OR business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.webhook_events;
CREATE POLICY "tenant_update" ON public.webhook_events
    FOR UPDATE USING (
        business_id IS NOT NULL AND business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IS NOT NULL AND business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.webhook_events;
CREATE POLICY "tenant_delete" ON public.webhook_events
    FOR DELETE USING (
        business_id IS NOT NULL AND business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 21. audit_logs
-- =============================================================================
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.audit_logs;
CREATE POLICY "service_role_bypass" ON public.audit_logs
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.audit_logs;
CREATE POLICY "tenant_select" ON public.audit_logs
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.audit_logs;
CREATE POLICY "tenant_insert" ON public.audit_logs
    FOR INSERT WITH CHECK (
        business_id IS NULL OR business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.audit_logs;
CREATE POLICY "tenant_update" ON public.audit_logs
    FOR UPDATE USING (false); -- Audit logs are immutable

DROP POLICY IF EXISTS "tenant_delete" ON public.audit_logs;
CREATE POLICY "tenant_delete" ON public.audit_logs
    FOR DELETE USING (false); -- Audit logs cannot be deleted

-- =============================================================================
-- 22. notification_jobs
-- =============================================================================
ALTER TABLE public.notification_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.notification_jobs;
CREATE POLICY "service_role_bypass" ON public.notification_jobs
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.notification_jobs;
CREATE POLICY "tenant_select" ON public.notification_jobs
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.notification_jobs;
CREATE POLICY "tenant_insert" ON public.notification_jobs
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.notification_jobs;
CREATE POLICY "tenant_update" ON public.notification_jobs
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.notification_jobs;
CREATE POLICY "tenant_delete" ON public.notification_jobs
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- =============================================================================
-- 23. daily_business_metrics
-- =============================================================================
ALTER TABLE public.daily_business_metrics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.daily_business_metrics;
CREATE POLICY "service_role_bypass" ON public.daily_business_metrics
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.daily_business_metrics;
CREATE POLICY "tenant_select" ON public.daily_business_metrics
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.daily_business_metrics;
CREATE POLICY "tenant_insert" ON public.daily_business_metrics
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.daily_business_metrics;
CREATE POLICY "tenant_update" ON public.daily_business_metrics
    FOR UPDATE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    ) WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_delete" ON public.daily_business_metrics;
CREATE POLICY "tenant_delete" ON public.daily_business_metrics
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- ============================================================================
-- Migration: 006_phase4_team.sql
-- Description: Phase 4 Team & Multi-Agent schema additions.
-- Adds: business_invitations, agent_activity_logs, conversation_typing
-- Includes RLS policies for tenant isolation on all new tables.
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 1. business_invitations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.business_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff' CHECK (role IN ('manager', 'staff', 'agent', 'viewer')),
    token TEXT UNIQUE NOT NULL,
    invited_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_business_invitation_business_email UNIQUE (business_id, email)
);

-- -----------------------------------------------------------------------------
-- 2. agent_activity_logs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agent_activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 3. conversation_typing
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.conversation_typing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    is_typing BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_conversation_typing UNIQUE (business_id, conversation_id, user_id)
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_business_invitations_business_id
    ON public.business_invitations (business_id);
CREATE INDEX IF NOT EXISTS idx_business_invitations_email
    ON public.business_invitations (email);
CREATE INDEX IF NOT EXISTS idx_business_invitations_token
    ON public.business_invitations (token);

CREATE INDEX IF NOT EXISTS idx_agent_activity_logs_business_id
    ON public.agent_activity_logs (business_id);
CREATE INDEX IF NOT EXISTS idx_agent_activity_logs_user_id
    ON public.agent_activity_logs (user_id);

CREATE INDEX IF NOT EXISTS idx_conversation_typing_business_id
    ON public.conversation_typing (business_id);
CREATE INDEX IF NOT EXISTS idx_conversation_typing_conversation_id
    ON public.conversation_typing (conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_typing_user_id
    ON public.conversation_typing (user_id);

-- -----------------------------------------------------------------------------
-- RLS policies
-- -----------------------------------------------------------------------------
-- business_invitations
ALTER TABLE public.business_invitations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.business_invitations;
CREATE POLICY "service_role_bypass" ON public.business_invitations
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.business_invitations;
CREATE POLICY "tenant_select" ON public.business_invitations
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.business_invitations;
CREATE POLICY "tenant_insert" ON public.business_invitations
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.business_invitations;
CREATE POLICY "tenant_update" ON public.business_invitations
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

DROP POLICY IF EXISTS "tenant_delete" ON public.business_invitations;
CREATE POLICY "tenant_delete" ON public.business_invitations
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

-- agent_activity_logs
ALTER TABLE public.agent_activity_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.agent_activity_logs;
CREATE POLICY "service_role_bypass" ON public.agent_activity_logs
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.agent_activity_logs;
CREATE POLICY "tenant_select" ON public.agent_activity_logs
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.agent_activity_logs;
CREATE POLICY "tenant_insert" ON public.agent_activity_logs
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.agent_activity_logs;
CREATE POLICY "tenant_update" ON public.agent_activity_logs
    FOR UPDATE USING (false);

DROP POLICY IF EXISTS "tenant_delete" ON public.agent_activity_logs;
CREATE POLICY "tenant_delete" ON public.agent_activity_logs
    FOR DELETE USING (false);

-- conversation_typing
ALTER TABLE public.conversation_typing ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bypass" ON public.conversation_typing;
CREATE POLICY "service_role_bypass" ON public.conversation_typing
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "tenant_select" ON public.conversation_typing;
CREATE POLICY "tenant_select" ON public.conversation_typing
    FOR SELECT USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_insert" ON public.conversation_typing;
CREATE POLICY "tenant_insert" ON public.conversation_typing
    FOR INSERT WITH CHECK (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

DROP POLICY IF EXISTS "tenant_update" ON public.conversation_typing;
CREATE POLICY "tenant_update" ON public.conversation_typing
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

DROP POLICY IF EXISTS "tenant_delete" ON public.conversation_typing;
CREATE POLICY "tenant_delete" ON public.conversation_typing
    FOR DELETE USING (
        business_id IN (
            SELECT business_id FROM public.business_members
            WHERE user_id = auth.uid() AND is_active = true
        )
    );

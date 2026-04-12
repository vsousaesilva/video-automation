-- ============================================================
-- Migration 009 — Billing tables + Rename apps -> negocios
-- Sessao 2: Signup, Onboarding, Billing (Asaas)
-- ============================================================

-- ============================================================
-- 1. RENAME: apps -> negocios
-- ============================================================

-- Renomear tabela principal
ALTER TABLE apps RENAME TO negocios;

-- Renomear FKs em tabelas dependentes
ALTER TABLE conteudos RENAME COLUMN app_id TO negocio_id;
ALTER TABLE videos RENAME COLUMN app_id TO negocio_id;
ALTER TABLE media_assets RENAME COLUMN app_id TO negocio_id;
ALTER TABLE execution_logs RENAME COLUMN app_id TO negocio_id;

-- Renomear indice existente
ALTER INDEX idx_apps_workspace_status_horario RENAME TO idx_negocios_workspace_status_horario;

-- Renomear enum de status
ALTER TYPE status_app RENAME TO status_negocio;

-- Renomear funcao get_apps_for_hour -> get_negocios_for_hour
CREATE OR REPLACE FUNCTION get_negocios_for_hour(hora INTEGER)
RETURNS TABLE (
    negocio_id UUID,
    negocio_nome VARCHAR,
    workspace_id UUID,
    frequencia frequencia_publicacao,
    dias_semana JSONB,
    plataformas JSONB,
    formato_youtube VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        n.id AS negocio_id,
        n.nome AS negocio_nome,
        n.workspace_id,
        n.frequencia,
        n.dias_semana,
        n.plataformas,
        n.formato_youtube
    FROM negocios n
    WHERE n.status = 'ativo'
      AND n.horario_disparo = hora
      AND (
          n.frequencia = 'diaria'
          OR (
              n.dias_semana IS NOT NULL
              AND n.dias_semana @> to_jsonb(EXTRACT(DOW FROM now())::integer)
          )
      );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- Drop funcao antiga
DROP FUNCTION IF EXISTS get_apps_for_hour(INTEGER);

-- Renomear trigger
ALTER TRIGGER trigger_apps_atualizado_em ON negocios RENAME TO trigger_negocios_atualizado_em;

-- ============================================================
-- 2. ALTER workspaces — campos de billing e onboarding
-- ============================================================

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT false;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS asaas_customer_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS documento_titular VARCHAR(18);
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS email_cobranca VARCHAR(255);
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS telefone VARCHAR(20);

-- ============================================================
-- 3. TABELA: plans
-- ============================================================

CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(30) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    modulos JSONB NOT NULL DEFAULT '[]',
    max_negocios INTEGER NOT NULL DEFAULT 1,
    max_users INTEGER NOT NULL DEFAULT 1,
    max_videos_mes INTEGER DEFAULT 5,
    max_conteudos_mes INTEGER DEFAULT 20,
    max_campanhas INTEGER DEFAULT 0,
    max_contatos_crm INTEGER DEFAULT 0,
    max_benchmarks_mes INTEGER DEFAULT 0,
    storage_max_gb NUMERIC(5,2) DEFAULT 1.0,
    preco_centavos INTEGER NOT NULL DEFAULT 0,
    intervalo VARCHAR(10) DEFAULT 'mensal',
    ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 4. TABELA: subscriptions
-- ============================================================

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id),
    asaas_subscription_id TEXT,
    asaas_customer_id TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'trial',
    trial_ends_at TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 5. TABELA: invoices
-- ============================================================

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    asaas_payment_id TEXT,
    valor_centavos INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    url_boleto TEXT,
    url_pix TEXT,
    vencimento DATE,
    pago_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 6. TABELA: usage_metrics
-- ============================================================

CREATE TABLE usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    mes_referencia DATE NOT NULL,
    videos_gerados INTEGER DEFAULT 0,
    videos_publicados INTEGER DEFAULT 0,
    conteudos_gerados INTEGER DEFAULT 0,
    campanhas_criadas INTEGER DEFAULT 0,
    contatos_crm INTEGER DEFAULT 0,
    benchmarks_executados INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    UNIQUE(workspace_id, mes_referencia)
);

-- ============================================================
-- 7. TABELA: audit_log
-- ============================================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    user_id UUID,
    acao VARCHAR(50) NOT NULL,
    recurso VARCHAR(50),
    recurso_id UUID,
    detalhes JSONB,
    ip_address INET,
    user_agent TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 8. INDICES
-- ============================================================

CREATE INDEX idx_subscriptions_workspace ON subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_usage_metrics_workspace_mes ON usage_metrics(workspace_id, mes_referencia);
CREATE INDEX idx_audit_log_workspace_criado ON audit_log(workspace_id, criado_em);
CREATE INDEX idx_invoices_workspace ON invoices(workspace_id);

-- ============================================================
-- 9. RLS para novas tabelas
-- ============================================================

ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Plans: leitura publica (todos podem ver planos)
CREATE POLICY "Qualquer usuario ve planos"
    ON plans FOR SELECT
    USING (true);

-- Subscriptions: por workspace
CREATE POLICY "Usuarios veem subscriptions do proprio workspace"
    ON subscriptions FOR SELECT
    USING (workspace_id = auth_workspace_id());

-- Invoices: por workspace
CREATE POLICY "Usuarios veem invoices do proprio workspace"
    ON invoices FOR SELECT
    USING (workspace_id = auth_workspace_id());

-- Usage metrics: por workspace
CREATE POLICY "Usuarios veem metricas do proprio workspace"
    ON usage_metrics FOR SELECT
    USING (workspace_id = auth_workspace_id());

-- Audit log: por workspace
CREATE POLICY "Usuarios veem audit log do proprio workspace"
    ON audit_log FOR SELECT
    USING (workspace_id = auth_workspace_id());

-- ============================================================
-- 10. Atualizar RLS policies da tabela negocios (antes apps)
-- ============================================================

-- Drop policies antigas (referenciavam "apps")
DROP POLICY IF EXISTS "Usuários veem apps do próprio workspace" ON negocios;
DROP POLICY IF EXISTS "Editores criam apps no próprio workspace" ON negocios;
DROP POLICY IF EXISTS "Editores atualizam apps do próprio workspace" ON negocios;
DROP POLICY IF EXISTS "Editores removem apps do próprio workspace" ON negocios;

-- Recriar com novos nomes
CREATE POLICY "Usuarios veem negocios do proprio workspace"
    ON negocios FOR SELECT
    USING (workspace_id = auth_workspace_id());

CREATE POLICY "Editores criam negocios no proprio workspace"
    ON negocios FOR INSERT
    WITH CHECK (workspace_id = auth_workspace_id());

CREATE POLICY "Editores atualizam negocios do proprio workspace"
    ON negocios FOR UPDATE
    USING (workspace_id = auth_workspace_id())
    WITH CHECK (workspace_id = auth_workspace_id());

CREATE POLICY "Editores removem negocios do proprio workspace"
    ON negocios FOR DELETE
    USING (workspace_id = auth_workspace_id());

-- Atualizar policies de conteudos, videos, execution_logs (referenciam negocio_id agora)
DROP POLICY IF EXISTS "Usuários veem conteúdos dos apps do próprio workspace" ON conteudos;
DROP POLICY IF EXISTS "Sistema cria conteúdos" ON conteudos;
DROP POLICY IF EXISTS "Sistema atualiza conteúdos" ON conteudos;

CREATE POLICY "Usuarios veem conteudos do proprio workspace"
    ON conteudos FOR SELECT
    USING (negocio_id IN (SELECT id FROM negocios WHERE workspace_id = auth_workspace_id()));

CREATE POLICY "Sistema cria conteudos"
    ON conteudos FOR INSERT
    WITH CHECK (negocio_id IN (SELECT id FROM negocios WHERE workspace_id = auth_workspace_id()));

CREATE POLICY "Sistema atualiza conteudos"
    ON conteudos FOR UPDATE
    USING (negocio_id IN (SELECT id FROM negocios WHERE workspace_id = auth_workspace_id()));

DROP POLICY IF EXISTS "Usuários veem vídeos dos apps do próprio workspace" ON videos;
DROP POLICY IF EXISTS "Sistema cria vídeos" ON videos;
DROP POLICY IF EXISTS "Sistema atualiza vídeos" ON videos;

CREATE POLICY "Usuarios veem videos do proprio workspace"
    ON videos FOR SELECT
    USING (negocio_id IN (SELECT id FROM negocios WHERE workspace_id = auth_workspace_id()));

CREATE POLICY "Sistema cria videos"
    ON videos FOR INSERT
    WITH CHECK (negocio_id IN (SELECT id FROM negocios WHERE workspace_id = auth_workspace_id()));

CREATE POLICY "Sistema atualiza videos"
    ON videos FOR UPDATE
    USING (negocio_id IN (SELECT id FROM negocios WHERE workspace_id = auth_workspace_id()));

DROP POLICY IF EXISTS "Usuários veem logs dos apps do próprio workspace" ON execution_logs;
DROP POLICY IF EXISTS "Sistema cria logs" ON execution_logs;

CREATE POLICY "Usuarios veem logs do proprio workspace"
    ON execution_logs FOR SELECT
    USING (negocio_id IN (SELECT id FROM negocios WHERE workspace_id = auth_workspace_id()));

CREATE POLICY "Sistema cria logs"
    ON execution_logs FOR INSERT
    WITH CHECK (negocio_id IN (SELECT id FROM negocios WHERE workspace_id = auth_workspace_id()));

-- Tabela users: adicionar campo para reset de senha
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMPTZ;

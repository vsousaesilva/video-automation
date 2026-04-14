-- Migration 014: Ads Manager (Meta Ads, Google Ads, TikTok Ads)
-- Sessao 8 — Inicial com foco em Meta Ads

-- ============================================================
-- 1. Contas de anuncios vinculadas (ad_accounts)
-- ============================================================
CREATE TABLE IF NOT EXISTS ad_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    plataforma VARCHAR(20) NOT NULL,  -- meta, google, tiktok
    external_id VARCHAR(100) NOT NULL, -- id da conta na plataforma (ex: act_1234567890)
    nome VARCHAR(255),
    moeda VARCHAR(10) DEFAULT 'BRL',
    fuso VARCHAR(50),
    access_token_encrypted TEXT,       -- criptografado (Fernet)
    token_expira_em TIMESTAMPTZ,
    refresh_token_encrypted TEXT,
    status VARCHAR(30) DEFAULT 'ativo', -- ativo, expirado, removido
    ultimo_sync TIMESTAMPTZ,
    dados_extras JSONB DEFAULT '{}',
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ad_accounts_workspace ON ad_accounts(workspace_id, plataforma);
CREATE UNIQUE INDEX idx_ad_accounts_unique
    ON ad_accounts(workspace_id, plataforma, external_id);

ALTER TABLE ad_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY ad_accounts_workspace_isolation ON ad_accounts
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 2. Campanhas (campaigns)
-- ============================================================
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    ad_account_id UUID NOT NULL REFERENCES ad_accounts(id) ON DELETE CASCADE,
    external_id VARCHAR(100) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    objetivo VARCHAR(100),             -- conversions, traffic, awareness, etc.
    status VARCHAR(30),                -- active, paused, archived, deleted
    orcamento_diario_centavos BIGINT,
    orcamento_total_centavos BIGINT,
    data_inicio DATE,
    data_fim DATE,
    dados_extras JSONB DEFAULT '{}',
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_campaigns_workspace ON campaigns(workspace_id);
CREATE INDEX idx_campaigns_account ON campaigns(ad_account_id, status);
CREATE UNIQUE INDEX idx_campaigns_unique ON campaigns(ad_account_id, external_id);

ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
CREATE POLICY campaigns_workspace_isolation ON campaigns
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 3. Ad Sets (conjuntos de anuncios)
-- ============================================================
CREATE TABLE IF NOT EXISTS ad_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    external_id VARCHAR(100) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    status VARCHAR(30),
    orcamento_diario_centavos BIGINT,
    publico_alvo JSONB DEFAULT '{}',
    dados_extras JSONB DEFAULT '{}',
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ad_sets_campaign ON ad_sets(campaign_id);
CREATE UNIQUE INDEX idx_ad_sets_unique ON ad_sets(campaign_id, external_id);

ALTER TABLE ad_sets ENABLE ROW LEVEL SECURITY;
CREATE POLICY ad_sets_workspace_isolation ON ad_sets
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 4. Ads (criativos)
-- ============================================================
CREATE TABLE IF NOT EXISTS ads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    ad_set_id UUID NOT NULL REFERENCES ad_sets(id) ON DELETE CASCADE,
    external_id VARCHAR(100) NOT NULL,
    nome VARCHAR(255),
    status VARCHAR(30),
    criativo JSONB DEFAULT '{}',       -- texto, imagem_url, video_url, headline, cta
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ads_ad_set ON ads(ad_set_id);
CREATE UNIQUE INDEX idx_ads_unique ON ads(ad_set_id, external_id);

ALTER TABLE ads ENABLE ROW LEVEL SECURITY;
CREATE POLICY ads_workspace_isolation ON ads
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 5. Metricas diarias (ad_metrics_daily)
-- ============================================================
CREATE TABLE IF NOT EXISTS ad_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    ad_account_id UUID NOT NULL REFERENCES ad_accounts(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    ad_set_id UUID REFERENCES ad_sets(id) ON DELETE CASCADE,
    ad_id UUID REFERENCES ads(id) ON DELETE CASCADE,
    data DATE NOT NULL,
    impressoes BIGINT DEFAULT 0,
    cliques BIGINT DEFAULT 0,
    conversoes BIGINT DEFAULT 0,
    gasto_centavos BIGINT DEFAULT 0,
    receita_centavos BIGINT DEFAULT 0,  -- para ROAS
    ctr NUMERIC(8, 4),                  -- %
    cpc_centavos BIGINT,
    cpa_centavos BIGINT,
    roas NUMERIC(10, 4),
    dados_extras JSONB DEFAULT '{}',
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ad_metrics_workspace ON ad_metrics_daily(workspace_id, data DESC);
CREATE INDEX idx_ad_metrics_campaign ON ad_metrics_daily(campaign_id, data DESC);
CREATE UNIQUE INDEX idx_ad_metrics_unique
    ON ad_metrics_daily(COALESCE(ad_id::text, ad_set_id::text, campaign_id::text, ad_account_id::text), data);

ALTER TABLE ad_metrics_daily ENABLE ROW LEVEL SECURITY;
CREATE POLICY ad_metrics_daily_workspace_isolation ON ad_metrics_daily
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 6. Regras de automacao (ad_rules)
-- ============================================================
CREATE TABLE IF NOT EXISTS ad_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    ad_account_id UUID REFERENCES ad_accounts(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    escopo VARCHAR(30) NOT NULL,   -- campaign, ad_set, ad
    escopo_ids JSONB DEFAULT '[]',  -- lista de IDs (vazio = todos)
    condicao JSONB NOT NULL,        -- {metrica, operador, valor, periodo_dias}
    acao VARCHAR(50) NOT NULL,      -- pause, activate, adjust_budget, notify
    acao_params JSONB DEFAULT '{}', -- parametros da acao (ex: ajuste de %)
    ativa BOOLEAN DEFAULT TRUE,
    ultima_execucao TIMESTAMPTZ,
    ultima_acao JSONB,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ad_rules_workspace ON ad_rules(workspace_id, ativa);

ALTER TABLE ad_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY ad_rules_workspace_isolation ON ad_rules
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

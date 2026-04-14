-- Migration 015: Benchmark (Sessao 10)
-- Pesquisa e monitoramento de concorrentes.

-- ============================================================
-- 1. Concorrentes cadastrados (competitors)
-- ============================================================
CREATE TABLE IF NOT EXISTS competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    segmento VARCHAR(100),
    website VARCHAR(500),
    descricao TEXT,
    instagram_handle VARCHAR(100),
    youtube_handle VARCHAR(100),
    tiktok_handle VARCHAR(100),
    palavras_chave JSONB DEFAULT '[]',
    dados_extras JSONB DEFAULT '{}',
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_competitors_workspace ON competitors(workspace_id, ativo);

ALTER TABLE competitors ENABLE ROW LEVEL SECURITY;
CREATE POLICY competitors_workspace_isolation ON competitors
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 2. Relatorios de benchmark (benchmark_reports)
-- ============================================================
CREATE TABLE IF NOT EXISTS benchmark_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    competitor_ids JSONB DEFAULT '[]',    -- lista de ids de competitors analisados
    parametros JSONB DEFAULT '{}',        -- redes, periodo, tipos de analise
    status VARCHAR(30) DEFAULT 'pendente', -- pendente, processando, concluido, erro
    resumo TEXT,                          -- summary textual
    insights JSONB DEFAULT '[]',          -- lista de insights acionaveis
    erro_msg TEXT,
    iniciado_em TIMESTAMPTZ,
    concluido_em TIMESTAMPTZ,
    criado_por UUID REFERENCES users(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_benchmark_reports_workspace ON benchmark_reports(workspace_id, criado_em DESC);
CREATE INDEX idx_benchmark_reports_status ON benchmark_reports(status);

ALTER TABLE benchmark_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY benchmark_reports_workspace_isolation ON benchmark_reports
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 3. Metricas de benchmark por concorrente (benchmark_metrics)
-- ============================================================
CREATE TABLE IF NOT EXISTS benchmark_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES benchmark_reports(id) ON DELETE CASCADE,
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    rede VARCHAR(30) NOT NULL,             -- instagram, youtube, tiktok, website
    seguidores BIGINT,
    seguindo BIGINT,
    publicacoes BIGINT,
    engajamento_medio NUMERIC(10, 4),      -- taxa em %
    visualizacoes_medias BIGINT,
    curtidas_medias BIGINT,
    comentarios_medios BIGINT,
    frequencia_semanal NUMERIC(10, 2),     -- publicacoes por semana
    dados_extras JSONB DEFAULT '{}',
    coletado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_benchmark_metrics_report ON benchmark_metrics(report_id);
CREATE INDEX idx_benchmark_metrics_competitor ON benchmark_metrics(competitor_id, rede);

ALTER TABLE benchmark_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY benchmark_metrics_workspace_isolation ON benchmark_metrics
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 4. Analise de palavras-chave (benchmark_keywords)
-- ============================================================
CREATE TABLE IF NOT EXISTS benchmark_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES benchmark_reports(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    palavra VARCHAR(255) NOT NULL,
    frequencia INTEGER DEFAULT 1,
    relevancia NUMERIC(4, 2),               -- 0.00 a 1.00
    intencao VARCHAR(50),                   -- informacional, comercial, transacional, navegacional
    volume_estimado BIGINT,                 -- estimativa mensal (Gemini pode sugerir)
    dados_extras JSONB DEFAULT '{}',
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_benchmark_keywords_report ON benchmark_keywords(report_id);
CREATE INDEX idx_benchmark_keywords_palavra ON benchmark_keywords(workspace_id, palavra);

ALTER TABLE benchmark_keywords ENABLE ROW LEVEL SECURITY;
CREATE POLICY benchmark_keywords_workspace_isolation ON benchmark_keywords
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 5. Billing: coluna de limite e contador
-- ============================================================
ALTER TABLE plans
    ADD COLUMN IF NOT EXISTS max_benchmarks_mes INTEGER;

ALTER TABLE usage_metrics
    ADD COLUMN IF NOT EXISTS benchmarks_executados INTEGER DEFAULT 0;

-- Preencher limites por plano
UPDATE plans SET max_benchmarks_mes = 0  WHERE slug = 'free';
UPDATE plans SET max_benchmarks_mes = 2  WHERE slug = 'starter';
UPDATE plans SET max_benchmarks_mes = 20 WHERE slug = 'pro';
UPDATE plans SET max_benchmarks_mes = NULL WHERE slug = 'enterprise'; -- ilimitado

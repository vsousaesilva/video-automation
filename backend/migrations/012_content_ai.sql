-- ============================================================
-- Migration 012 — Content AI
-- Sessao 6: tabelas content_templates, content_requests, generated_contents
-- ============================================================

-- 1. Templates de conteudo (prompts reutilizaveis)
CREATE TABLE IF NOT EXISTS content_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,          -- copy_ads, legenda, roteiro, artigo, resposta_comentario, email_marketing
    tom_voz VARCHAR(100),
    idioma VARCHAR(10) DEFAULT 'pt-BR',
    prompt_sistema TEXT,                -- instrucoes do sistema (system prompt)
    prompt_template TEXT NOT NULL,      -- template com placeholders {{variavel}}
    variaveis JSONB DEFAULT '[]',       -- lista de variaveis esperadas: [{"nome": "produto", "descricao": "..."}]
    ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

-- 2. Requisicoes de geracao
CREATE TABLE IF NOT EXISTS content_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    template_id UUID REFERENCES content_templates(id) ON DELETE SET NULL,
    negocio_id UUID REFERENCES negocios(id) ON DELETE SET NULL,
    tipo VARCHAR(50) NOT NULL,          -- copy_ads, legenda, roteiro, artigo, resposta_comentario, email_marketing
    tom_voz VARCHAR(100) DEFAULT 'profissional',
    idioma VARCHAR(10) DEFAULT 'pt-BR',
    prompt_usuario TEXT,                -- instrucoes adicionais do usuario
    contexto JSONB DEFAULT '{}',        -- dados de contexto (nome negocio, publico, plataforma, etc.)
    quantidade INT DEFAULT 1,           -- quantas variacoes gerar
    status VARCHAR(30) DEFAULT 'pending', -- pending, processing, completed, failed
    erro_msg TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- 3. Conteudos gerados
CREATE TABLE IF NOT EXISTS generated_contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES content_requests(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    negocio_id UUID REFERENCES negocios(id) ON DELETE SET NULL,
    tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(500),
    conteudo TEXT NOT NULL,             -- texto gerado
    metadata JSONB DEFAULT '{}',        -- hashtags, emojis, variacoes, etc.
    tokens_usados INT DEFAULT 0,
    avaliacao SMALLINT,                 -- 1-5 estrelas (feedback do usuario)
    usado_em VARCHAR(100),              -- onde foi usado: video_engine, copiado, exportado
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_content_templates_workspace ON content_templates(workspace_id);
CREATE INDEX IF NOT EXISTS idx_content_templates_tipo ON content_templates(workspace_id, tipo);
CREATE INDEX IF NOT EXISTS idx_content_requests_workspace ON content_requests(workspace_id);
CREATE INDEX IF NOT EXISTS idx_content_requests_status ON content_requests(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_content_requests_criado ON content_requests(workspace_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_generated_contents_request ON generated_contents(request_id);
CREATE INDEX IF NOT EXISTS idx_generated_contents_workspace ON generated_contents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_generated_contents_tipo ON generated_contents(workspace_id, tipo);

-- RLS
ALTER TABLE content_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_contents ENABLE ROW LEVEL SECURITY;

CREATE POLICY content_templates_workspace_isolation ON content_templates
    USING (workspace_id = current_setting('app.current_workspace_id')::uuid);

CREATE POLICY content_requests_workspace_isolation ON content_requests
    USING (workspace_id = current_setting('app.current_workspace_id')::uuid);

CREATE POLICY generated_contents_workspace_isolation ON generated_contents
    USING (workspace_id = current_setting('app.current_workspace_id')::uuid);

-- Seed: templates padrao (globais, workspace_id sera preenchido na aplicacao)
-- Os templates padrao serao criados pela aplicacao no primeiro acesso

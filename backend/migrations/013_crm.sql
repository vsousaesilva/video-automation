-- Migration 013: CRM — Contatos, Deals, Funil, Atividades, Tags
-- Sessao 7

-- ============================================================
-- 1. Etapas do funil (deal_stages)
-- ============================================================
CREATE TABLE IF NOT EXISTS deal_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    posicao INTEGER NOT NULL DEFAULT 0,
    cor VARCHAR(7) DEFAULT '#6366f1',
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_deal_stages_workspace ON deal_stages(workspace_id, posicao);

ALTER TABLE deal_stages ENABLE ROW LEVEL SECURITY;
CREATE POLICY deal_stages_workspace_isolation ON deal_stages
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 2. Contatos (contacts)
-- ============================================================
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefone VARCHAR(30),
    empresa VARCHAR(255),
    cargo VARCHAR(255),
    origem VARCHAR(100),  -- site, indicacao, linkedin, importacao, manual
    notas TEXT,
    avatar_url TEXT,
    dados_extras JSONB DEFAULT '{}',
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_contacts_workspace ON contacts(workspace_id);
CREATE INDEX idx_contacts_email ON contacts(workspace_id, email);
CREATE INDEX idx_contacts_nome ON contacts(workspace_id, nome);
CREATE INDEX idx_contacts_criado ON contacts(workspace_id, criado_em DESC);

ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY contacts_workspace_isolation ON contacts
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 3. Tags de contato (contact_tags)
-- ============================================================
CREATE TABLE IF NOT EXISTS contact_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    cor VARCHAR(7) DEFAULT '#6366f1',
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX idx_contact_tags_unique ON contact_tags(workspace_id, nome);

ALTER TABLE contact_tags ENABLE ROW LEVEL SECURITY;
CREATE POLICY contact_tags_workspace_isolation ON contact_tags
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- Tabela de junção contato <-> tag
CREATE TABLE IF NOT EXISTS contacts_tags (
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES contact_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, tag_id)
);

-- ============================================================
-- 4. Deals / Oportunidades
-- ============================================================
CREATE TABLE IF NOT EXISTS deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    stage_id UUID NOT NULL REFERENCES deal_stages(id) ON DELETE RESTRICT,
    titulo VARCHAR(255) NOT NULL,
    valor_centavos BIGINT DEFAULT 0,
    moeda VARCHAR(3) DEFAULT 'BRL',
    status VARCHAR(50) DEFAULT 'aberto',  -- aberto, ganho, perdido
    motivo_perda VARCHAR(500),
    previsao_fechamento DATE,
    responsavel_id UUID REFERENCES users(id) ON DELETE SET NULL,
    notas TEXT,
    posicao_kanban INTEGER DEFAULT 0,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_deals_workspace ON deals(workspace_id);
CREATE INDEX idx_deals_stage ON deals(workspace_id, stage_id);
CREATE INDEX idx_deals_contact ON deals(contact_id);
CREATE INDEX idx_deals_status ON deals(workspace_id, status);

ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
CREATE POLICY deals_workspace_isolation ON deals
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 5. Atividades (activities)
-- ============================================================
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    deal_id UUID REFERENCES deals(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    tipo VARCHAR(50) NOT NULL,  -- nota, email, ligacao, reuniao, tarefa
    titulo VARCHAR(255),
    descricao TEXT,
    data_atividade TIMESTAMPTZ DEFAULT now(),
    concluida BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_activities_contact ON activities(contact_id, criado_em DESC);
CREATE INDEX idx_activities_deal ON activities(deal_id, criado_em DESC);
CREATE INDEX idx_activities_workspace ON activities(workspace_id, criado_em DESC);

ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
CREATE POLICY activities_workspace_isolation ON activities
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 6. Seed: Etapas padrão do funil para workspaces existentes
-- ============================================================
DO $$
DECLARE
    ws RECORD;
BEGIN
    FOR ws IN SELECT id FROM workspaces LOOP
        INSERT INTO deal_stages (workspace_id, nome, posicao, cor) VALUES
            (ws.id, 'Novo Lead', 0, '#94a3b8'),
            (ws.id, 'Qualificado', 1, '#60a5fa'),
            (ws.id, 'Proposta', 2, '#f59e0b'),
            (ws.id, 'Negociacao', 3, '#f97316'),
            (ws.id, 'Ganho', 4, '#22c55e'),
            (ws.id, 'Perdido', 5, '#ef4444')
        ON CONFLICT DO NOTHING;
    END LOOP;
END $$;

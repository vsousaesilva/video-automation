-- Migration 017: API Keys para API publica (Sessao 12)
-- Tabela api_keys — permite que clientes Enterprise usem a API programaticamente.

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    prefix VARCHAR(12) NOT NULL,          -- primeiros 12 chars para exibicao (ex.: uks_live_ab)
    key_hash VARCHAR(255) NOT NULL,       -- SHA-256 da chave completa
    scopes TEXT[] NOT NULL DEFAULT ARRAY['read'],  -- read | write
    ativo BOOLEAN NOT NULL DEFAULT true,
    ultimo_uso_em TIMESTAMPTZ,
    criado_por UUID REFERENCES users(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expira_em TIMESTAMPTZ,
    CONSTRAINT api_keys_scopes_check CHECK (
        scopes <@ ARRAY['read','write']::TEXT[]
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_workspace ON api_keys(workspace_id, ativo);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix);

-- RLS — isolar por workspace
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS api_keys_workspace_isolation ON api_keys;
CREATE POLICY api_keys_workspace_isolation ON api_keys
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- Disponibilizar flag "api_publica" no plano (so Enterprise = true)
ALTER TABLE plans ADD COLUMN IF NOT EXISTS api_publica BOOLEAN NOT NULL DEFAULT false;
UPDATE plans SET api_publica = true WHERE slug = 'enterprise';

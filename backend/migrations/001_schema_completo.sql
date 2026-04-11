-- ============================================================
-- Migration 001 — Schema completo do banco de dados
-- Plataforma de Automação de Vídeos para Marketing de Apps
-- Versão: PRD v1.1
-- ============================================================

-- ============================================================
-- 1. ENUM TYPES
-- ============================================================

CREATE TYPE papel_usuario AS ENUM ('admin', 'editor', 'viewer');

CREATE TYPE status_app AS ENUM ('ativo', 'pausado', 'arquivado');

CREATE TYPE status_video AS ENUM (
    'processando',
    'aguardando_aprovacao',
    'aprovado',
    'rejeitado',
    'publicado',
    'erro_validacao',
    'erro_publicacao',
    'rejeitado_telegram'
);

CREATE TYPE status_conteudo AS ENUM (
    'gerado',
    'em_producao',
    'erro',
    'concluido'
);

CREATE TYPE tipo_conteudo AS ENUM (
    'problema_solucao',
    'tutorial_rapido',
    'beneficio_destaque',
    'prova_social',
    'comparativo',
    'curiosidade_nicho'
);

CREATE TYPE tipo_midia AS ENUM ('imagem', 'video');

CREATE TYPE canal_aprovacao AS ENUM ('painel', 'telegram');

CREATE TYPE frequencia_publicacao AS ENUM ('diaria', '3x_semana', '1x_semana');

-- ============================================================
-- 2. TABELAS
-- ============================================================

-- Workspaces
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(255) NOT NULL,
    segmento VARCHAR(100),
    tom_voz VARCHAR(100),
    idioma VARCHAR(10) DEFAULT 'pt-BR',
    logo_url TEXT,
    cor_primaria VARCHAR(7),
    cor_secundaria VARCHAR(7),
    telegram_bot_token TEXT,
    telegram_chat_id TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Usuários
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash TEXT,
    papel papel_usuario DEFAULT 'editor',
    telegram_user_id BIGINT,
    ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Aplicativos
CREATE TABLE apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    categoria VARCHAR(100),
    descricao TEXT,
    publico_alvo TEXT,
    funcionalidades JSONB,
    diferenciais JSONB,
    cta VARCHAR(255),
    link_download TEXT,
    plataformas JSONB DEFAULT '["instagram", "youtube"]'::jsonb,
    formato_instagram VARCHAR(10) DEFAULT '9_16',
    formato_youtube VARCHAR(20) DEFAULT 'ambos',
    frequencia frequencia_publicacao DEFAULT 'diaria',
    horario_disparo INTEGER CHECK (horario_disparo >= 0 AND horario_disparo <= 23),
    dias_semana JSONB,
    tom_voz VARCHAR(100),
    status status_app DEFAULT 'ativo',
    keywords JSONB,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

-- Banco de imagens
CREATE TABLE media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    app_id UUID REFERENCES apps(id) ON DELETE CASCADE,
    nome VARCHAR(255),
    url_storage TEXT NOT NULL,
    tipo tipo_midia,
    tags JSONB,
    tamanho_bytes INTEGER,
    largura INTEGER,
    altura INTEGER,
    ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Conteúdos gerados
CREATE TABLE conteudos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    tipo_conteudo tipo_conteudo,
    roteiro TEXT,
    titulo VARCHAR(255),
    descricao_youtube TEXT,
    descricao_instagram TEXT,
    hashtags_youtube JSONB,
    hashtags_instagram JSONB,
    keywords_visuais JSONB,
    keywords_seo JSONB,
    status status_conteudo DEFAULT 'gerado',
    erro_msg TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Vídeos
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conteudo_id UUID NOT NULL REFERENCES conteudos(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    url_storage_vertical TEXT,
    duracao_vertical_segundos INTEGER,
    url_storage_horizontal TEXT,
    duracao_horizontal_segundos INTEGER,
    tamanho_bytes_total INTEGER,
    status status_video DEFAULT 'processando',
    aprovado_por UUID REFERENCES users(id),
    aprovado_via canal_aprovacao,
    aprovado_em TIMESTAMPTZ,
    motivo_rejeicao TEXT,
    telegram_message_id BIGINT,
    url_youtube TEXT,
    url_instagram TEXT,
    publicado_em TIMESTAMPTZ,
    erro_msg TEXT,
    tentativas_publicacao INTEGER DEFAULT 0,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Logs de execução
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE SET NULL,
    etapa VARCHAR(50),
    status VARCHAR(20),
    mensagem TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 3. ÍNDICES DE PERFORMANCE
-- ============================================================

CREATE INDEX idx_apps_workspace_status_horario
    ON apps (workspace_id, status, horario_disparo);

CREATE INDEX idx_videos_app_status_criado
    ON videos (app_id, status, criado_em);

CREATE INDEX idx_media_assets_app_workspace_ativo
    ON media_assets (app_id, workspace_id, ativo);

CREATE INDEX idx_execution_logs_app_criado
    ON execution_logs (app_id, criado_em);

CREATE INDEX idx_users_workspace
    ON users (workspace_id);

CREATE INDEX idx_conteudos_app
    ON conteudos (app_id);

-- ============================================================
-- 4. ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Habilitar RLS em todas as tabelas
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE apps ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE conteudos ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_logs ENABLE ROW LEVEL SECURITY;

-- Função auxiliar: retorna o workspace_id do usuário autenticado
CREATE OR REPLACE FUNCTION auth_workspace_id()
RETURNS UUID AS $$
    SELECT workspace_id
    FROM users
    WHERE id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- ---- WORKSPACES ----
CREATE POLICY "Usuários veem apenas seu workspace"
    ON workspaces FOR SELECT
    USING (id = auth_workspace_id());

CREATE POLICY "Admins atualizam seu workspace"
    ON workspaces FOR UPDATE
    USING (id = auth_workspace_id())
    WITH CHECK (id = auth_workspace_id());

-- ---- USERS ----
CREATE POLICY "Usuários veem membros do próprio workspace"
    ON users FOR SELECT
    USING (workspace_id = auth_workspace_id());

CREATE POLICY "Admins inserem usuários no próprio workspace"
    ON users FOR INSERT
    WITH CHECK (workspace_id = auth_workspace_id());

CREATE POLICY "Admins atualizam usuários do próprio workspace"
    ON users FOR UPDATE
    USING (workspace_id = auth_workspace_id())
    WITH CHECK (workspace_id = auth_workspace_id());

-- ---- APPS ----
CREATE POLICY "Usuários veem apps do próprio workspace"
    ON apps FOR SELECT
    USING (workspace_id = auth_workspace_id());

CREATE POLICY "Editores criam apps no próprio workspace"
    ON apps FOR INSERT
    WITH CHECK (workspace_id = auth_workspace_id());

CREATE POLICY "Editores atualizam apps do próprio workspace"
    ON apps FOR UPDATE
    USING (workspace_id = auth_workspace_id())
    WITH CHECK (workspace_id = auth_workspace_id());

CREATE POLICY "Editores removem apps do próprio workspace"
    ON apps FOR DELETE
    USING (workspace_id = auth_workspace_id());

-- ---- MEDIA_ASSETS ----
CREATE POLICY "Usuários veem mídia do próprio workspace"
    ON media_assets FOR SELECT
    USING (workspace_id = auth_workspace_id());

CREATE POLICY "Editores criam mídia no próprio workspace"
    ON media_assets FOR INSERT
    WITH CHECK (workspace_id = auth_workspace_id());

CREATE POLICY "Editores atualizam mídia do próprio workspace"
    ON media_assets FOR UPDATE
    USING (workspace_id = auth_workspace_id())
    WITH CHECK (workspace_id = auth_workspace_id());

CREATE POLICY "Editores removem mídia do próprio workspace"
    ON media_assets FOR DELETE
    USING (workspace_id = auth_workspace_id());

-- ---- CONTEUDOS ----
CREATE POLICY "Usuários veem conteúdos dos apps do próprio workspace"
    ON conteudos FOR SELECT
    USING (
        app_id IN (SELECT id FROM apps WHERE workspace_id = auth_workspace_id())
    );

CREATE POLICY "Sistema cria conteúdos"
    ON conteudos FOR INSERT
    WITH CHECK (
        app_id IN (SELECT id FROM apps WHERE workspace_id = auth_workspace_id())
    );

CREATE POLICY "Sistema atualiza conteúdos"
    ON conteudos FOR UPDATE
    USING (
        app_id IN (SELECT id FROM apps WHERE workspace_id = auth_workspace_id())
    );

-- ---- VIDEOS ----
CREATE POLICY "Usuários veem vídeos dos apps do próprio workspace"
    ON videos FOR SELECT
    USING (
        app_id IN (SELECT id FROM apps WHERE workspace_id = auth_workspace_id())
    );

CREATE POLICY "Sistema cria vídeos"
    ON videos FOR INSERT
    WITH CHECK (
        app_id IN (SELECT id FROM apps WHERE workspace_id = auth_workspace_id())
    );

CREATE POLICY "Sistema atualiza vídeos"
    ON videos FOR UPDATE
    USING (
        app_id IN (SELECT id FROM apps WHERE workspace_id = auth_workspace_id())
    );

-- ---- EXECUTION_LOGS ----
CREATE POLICY "Usuários veem logs dos apps do próprio workspace"
    ON execution_logs FOR SELECT
    USING (
        app_id IN (SELECT id FROM apps WHERE workspace_id = auth_workspace_id())
    );

CREATE POLICY "Sistema cria logs"
    ON execution_logs FOR INSERT
    WITH CHECK (
        app_id IN (SELECT id FROM apps WHERE workspace_id = auth_workspace_id())
    );

-- ============================================================
-- 5. FUNÇÃO: get_apps_for_hour
-- Retorna apps elegíveis para disparo em uma dada hora
-- ============================================================

CREATE OR REPLACE FUNCTION get_apps_for_hour(hora INTEGER)
RETURNS TABLE (
    app_id UUID,
    app_nome VARCHAR,
    workspace_id UUID,
    frequencia frequencia_publicacao,
    dias_semana JSONB,
    plataformas JSONB,
    formato_youtube VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id AS app_id,
        a.nome AS app_nome,
        a.workspace_id,
        a.frequencia,
        a.dias_semana,
        a.plataformas,
        a.formato_youtube
    FROM apps a
    WHERE a.status = 'ativo'
      AND a.horario_disparo = hora
      AND (
          -- Frequência diária: sempre elegível
          a.frequencia = 'diaria'
          OR (
              -- Frequência menor: verificar dia da semana (0=dom, 1=seg, ..., 6=sab)
              a.dias_semana IS NOT NULL
              AND a.dias_semana @> to_jsonb(EXTRACT(DOW FROM now())::integer)
          )
      );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================
-- 6. TRIGGER: atualizar campo atualizado_em na tabela apps
-- ============================================================

CREATE OR REPLACE FUNCTION atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_apps_atualizado_em
    BEFORE UPDATE ON apps
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();

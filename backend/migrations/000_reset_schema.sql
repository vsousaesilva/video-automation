-- ============================================================
-- Migration 000 — Reset completo do schema
-- ATENÇÃO: Apaga TODOS os dados e recria do zero
-- Executar apenas em ambiente de desenvolvimento
-- ============================================================

-- Dropar tabelas (ordem respeita dependências)
DROP TABLE IF EXISTS execution_logs CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS conteudos CASCADE;
DROP TABLE IF EXISTS media_assets CASCADE;
DROP TABLE IF EXISTS apps CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS workspaces CASCADE;

-- Dropar função e trigger
DROP FUNCTION IF EXISTS auth_workspace_id() CASCADE;
DROP FUNCTION IF EXISTS get_apps_for_hour(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS atualizar_timestamp() CASCADE;

-- Dropar enums
DROP TYPE IF EXISTS papel_usuario CASCADE;
DROP TYPE IF EXISTS status_app CASCADE;
DROP TYPE IF EXISTS status_video CASCADE;
DROP TYPE IF EXISTS status_conteudo CASCADE;
DROP TYPE IF EXISTS tipo_conteudo CASCADE;
DROP TYPE IF EXISTS tipo_midia CASCADE;
DROP TYPE IF EXISTS canal_aprovacao CASCADE;
DROP TYPE IF EXISTS frequencia_publicacao CASCADE;

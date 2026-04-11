-- Sessao 13: Adicionar colunas de credenciais do Instagram ao workspace
-- Permite armazenar access_token e account_id do Instagram por workspace (isolamento de credenciais)

ALTER TABLE workspaces
ADD COLUMN IF NOT EXISTS meta_access_token text;

ALTER TABLE workspaces
ADD COLUMN IF NOT EXISTS meta_instagram_account_id text;

COMMENT ON COLUMN workspaces.meta_access_token
IS 'Access token da Meta Graph API para publicacao no Instagram, armazenado por workspace';

COMMENT ON COLUMN workspaces.meta_instagram_account_id
IS 'ID da conta Business do Instagram (ig-user-id) para publicacao de Reels';

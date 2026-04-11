-- Sessao 12: Adicionar coluna youtube_refresh_token ao workspace
-- Permite armazenar refresh token do YouTube por workspace (isolamento de credenciais)

ALTER TABLE workspaces
ADD COLUMN IF NOT EXISTS youtube_refresh_token text;

COMMENT ON COLUMN workspaces.youtube_refresh_token
IS 'OAuth2 refresh token do YouTube Data API v3, armazenado por workspace';

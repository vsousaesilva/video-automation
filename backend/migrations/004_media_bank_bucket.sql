-- =============================================
-- Migration 004: Configuracao do bucket media-bank
-- Sessao 6: Banco de Imagens
-- =============================================

-- 1. Criar bucket media-bank (publico para leitura das URLs nos videos)
INSERT INTO storage.buckets (id, name, public)
VALUES ('media-bank', 'media-bank', true)
ON CONFLICT (id) DO NOTHING;

-- 2. Politica de upload: apenas usuarios autenticados via service_key
-- (o backend usa service_key, entao o upload ja funciona por padrao)

-- 3. Politica de leitura publica (necessario para URLs nos videos)
CREATE POLICY "Leitura publica media-bank"
ON storage.objects FOR SELECT
USING (bucket_id = 'media-bank');

-- 4. Politica de insercao (service role)
CREATE POLICY "Upload via service role media-bank"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'media-bank');

-- 5. Politica de exclusao (service role)
CREATE POLICY "Delete via service role media-bank"
ON storage.objects FOR DELETE
USING (bucket_id = 'media-bank');

-- 6. Verificar que a tabela media_assets existe (ja criada na migration 001)
-- Se nao existir, criar:
CREATE TABLE IF NOT EXISTS media_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid REFERENCES workspaces(id),
  app_id uuid REFERENCES apps(id),
  nome varchar(255),
  url_storage text NOT NULL,
  tipo varchar(10),
  tags jsonb,
  tamanho_bytes integer,
  largura integer,
  altura integer,
  ativo boolean DEFAULT true,
  criado_em timestamptz DEFAULT now()
);

-- 7. Indices para performance das queries de selecao
CREATE INDEX IF NOT EXISTS idx_media_assets_app_id ON media_assets(app_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_workspace_id ON media_assets(workspace_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_tags ON media_assets USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_media_assets_ativo ON media_assets(ativo);
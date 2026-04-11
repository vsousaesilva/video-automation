-- ============================================================
-- Migração 008: pg_cron escalonado para disparo de pipelines
-- ============================================================
-- Pré-requisito: ativar extensões pg_cron e pg_net no Supabase
-- Dashboard → Database → Extensions → habilitar "pg_cron" e "pg_net"
-- ============================================================

-- 1. Ativar extensões (executar no SQL Editor do Supabase)
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- 2. Cron job horário: a cada hora cheia, dispara o pipeline
--    para os apps agendados naquele horário.
--    IMPORTANTE: substitua 'https://video-automation-api.onrender.com'
--    pela URL real do seu backend no Render.
SELECT cron.schedule(
  'pipeline-hourly-trigger',
  '0 * * * *',  -- a cada hora cheia
  $$
  SELECT net.http_post(
    url := 'https://video-automation-api.onrender.com/pipeline/trigger',
    body := json_build_object('hora_atual', EXTRACT(HOUR FROM NOW() AT TIME ZONE 'America/Sao_Paulo')::int)::text,
    headers := '{"Content-Type": "application/json"}'::jsonb
  );
  $$
);

-- 3. (Opcional) Cron de limpeza: purge de vídeos publicados há mais de 7 dias
--    para economizar espaço no Supabase Storage (bucket media-bank)
SELECT cron.schedule(
  'storage-purge-weekly',
  '0 3 * * 0',  -- domingo às 3h da manhã
  $$
  UPDATE videos
  SET url_storage_vertical = NULL,
      url_storage_horizontal = NULL
  WHERE status = 'publicado'
    AND publicado_em < NOW() - INTERVAL '7 days'
    AND (url_storage_vertical IS NOT NULL OR url_storage_horizontal IS NOT NULL);
  $$
);

-- ============================================================
-- Verificação: listar cron jobs ativos
-- ============================================================
-- SELECT * FROM cron.job;

-- ============================================================
-- Para remover um job:
-- SELECT cron.unschedule('pipeline-hourly-trigger');
-- SELECT cron.unschedule('storage-purge-weekly');
-- ============================================================

-- ============================================================
-- NOTAS DE OPERAÇÃO:
--
-- 1. O pg_cron usa timezone UTC por padrão. O SQL acima
--    converte para 'America/Sao_Paulo' antes de extrair a hora.
--
-- 2. O Render free tier dorme após 15 min de inatividade.
--    O primeiro request (cold start) leva ~30-60s.
--    O pg_net é fire-and-forget, então o cron não bloqueia.
--
-- 3. Para testar sem esperar o cron, chame manualmente:
--    POST /pipeline/trigger {"hora_atual": 10}
--
-- 4. Recomendação: máximo 1 app por hora no free tier
--    para evitar timeout do Render (30s no plano gratuito).
-- ============================================================

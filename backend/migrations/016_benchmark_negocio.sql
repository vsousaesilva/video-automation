-- Migration 016: associa concorrentes e relatorios de benchmark a um negocio.
-- Complemento da Sessao 10: um mesmo workspace pode ter varios negocios, cada
-- um com sua propria concorrencia isolada.

-- 1. competitors.negocio_id (NOT NULL apos preenchimento)
ALTER TABLE competitors
    ADD COLUMN IF NOT EXISTS negocio_id UUID REFERENCES negocios(id) ON DELETE CASCADE;

-- Para bases existentes com competitors sem negocio associado, associar ao
-- primeiro negocio do mesmo workspace (fallback). Workspaces sem negocios
-- terao os concorrentes removidos antes do NOT NULL.
UPDATE competitors c
SET negocio_id = (
    SELECT n.id FROM negocios n
    WHERE n.workspace_id = c.workspace_id
    ORDER BY n.criado_em ASC
    LIMIT 1
)
WHERE c.negocio_id IS NULL;

DELETE FROM competitors WHERE negocio_id IS NULL;

ALTER TABLE competitors
    ALTER COLUMN negocio_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_competitors_negocio ON competitors(negocio_id, ativo);

-- 2. benchmark_reports.negocio_id
ALTER TABLE benchmark_reports
    ADD COLUMN IF NOT EXISTS negocio_id UUID REFERENCES negocios(id) ON DELETE CASCADE;

UPDATE benchmark_reports r
SET negocio_id = (
    SELECT n.id FROM negocios n
    WHERE n.workspace_id = r.workspace_id
    ORDER BY n.criado_em ASC
    LIMIT 1
)
WHERE r.negocio_id IS NULL;

DELETE FROM benchmark_reports WHERE negocio_id IS NULL;

ALTER TABLE benchmark_reports
    ALTER COLUMN negocio_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_benchmark_reports_negocio
    ON benchmark_reports(negocio_id, criado_em DESC);

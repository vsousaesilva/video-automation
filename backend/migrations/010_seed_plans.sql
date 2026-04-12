-- ============================================================
-- Migration 010 — Seed: planos + subscription para workspaces existentes
-- ============================================================

-- 1. Inserir planos
INSERT INTO plans (slug, nome, descricao, modulos, max_negocios, max_users, max_videos_mes, max_conteudos_mes, max_campanhas, max_contatos_crm, max_benchmarks_mes, storage_max_gb, preco_centavos, intervalo)
VALUES
    ('free', 'Free', 'Plano gratuito para experimentar a plataforma',
     '["video_engine", "content_ai", "dashboard"]',
     1, 1, 5, 10, 0, 0, 0, 1.0, 0, 'mensal'),

    ('starter', 'Starter', 'Ideal para profissionais autônomos e pequenos negócios',
     '["video_engine", "content_ai", "crm", "dashboard"]',
     3, 2, 30, 50, 0, 100, 0, 5.0, 9700, 'mensal'),

    ('pro', 'Pro', 'Para agências e equipes que precisam de todos os recursos',
     '["video_engine", "content_ai", "ads_manager", "crm", "benchmark", "dashboard"]',
     10, 5, 150, 300, 10, 5000, 3, 25.0, 29700, 'mensal'),

    ('enterprise', 'Enterprise', 'Sob consulta — recursos ilimitados e suporte dedicado',
     '["video_engine", "content_ai", "ads_manager", "crm", "benchmark", "dashboard"]',
     999999, 999999, 999999, 999999, 999999, 999999, 999999, 100.0, 0, 'mensal');

-- 2. Criar subscription ativa (Pro, 1 ano) para workspaces existentes
INSERT INTO subscriptions (workspace_id, plan_id, status, current_period_start, current_period_end)
SELECT
    w.id,
    (SELECT id FROM plans WHERE slug = 'pro'),
    'active',
    now(),
    now() + interval '1 year'
FROM workspaces w
WHERE NOT EXISTS (SELECT 1 FROM subscriptions s WHERE s.workspace_id = w.id);

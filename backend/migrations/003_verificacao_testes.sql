-- ============================================================
-- Migration 003 — Consultas de verificação
-- Execute após 001 e 002 para validar o schema
-- ============================================================

-- 1. Verificar se todas as tabelas foram criadas
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 2. Verificar enums criados
SELECT typname, enumlabel
FROM pg_enum e
JOIN pg_type t ON e.enumtypid = t.oid
ORDER BY typname, enumsortorder;

-- 3. Verificar dados de teste — Apps
SELECT a.nome AS app, a.status, a.horario_disparo, a.frequencia,
       w.nome AS workspace
FROM apps a
JOIN workspaces w ON a.workspace_id = w.id
ORDER BY a.horario_disparo;

-- 4. Verificar dados de teste — Usuários
SELECT u.nome, u.email, u.papel, w.nome AS workspace
FROM users u
JOIN workspaces w ON u.workspace_id = w.id;

-- 5. Verificar dados de teste — Media assets
SELECT ma.nome, ma.tipo, ma.tags, a.nome AS app
FROM media_assets ma
LEFT JOIN apps a ON ma.app_id = a.id;

-- 6. Testar função get_apps_for_hour
-- Deve retornar FocusTimer (hora 8), MeditaCalma (hora 9), GastoZero (hora 10)
SELECT * FROM get_apps_for_hour(8);
SELECT * FROM get_apps_for_hour(9);
SELECT * FROM get_apps_for_hour(10);

-- 7. Verificar índices criados
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename;

-- 8. Verificar RLS habilitado
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND rowsecurity = true
ORDER BY tablename;

-- 9. Verificar políticas RLS
SELECT schemaname, tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- 10. Teste de isolamento cross-workspace (simulação)
-- Este SELECT deve mostrar que cada workspace tem apenas seus apps
SELECT w.nome AS workspace, count(a.id) AS total_apps
FROM workspaces w
LEFT JOIN apps a ON a.workspace_id = w.id
GROUP BY w.nome;

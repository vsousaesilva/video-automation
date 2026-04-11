-- ============================================================
-- Migration 002 — Dados fictícios para teste
-- ATENÇÃO: Executar apenas em ambiente de desenvolvimento
-- ============================================================

-- ============================================================
-- 1. WORKSPACES
-- ============================================================

INSERT INTO workspaces (id, nome, segmento, tom_voz, idioma, cor_primaria, cor_secundaria)
VALUES
    ('a1111111-1111-1111-1111-111111111111', 'AppStudio Brasil', 'tecnologia', 'profissional', 'pt-BR', '#2563EB', '#1E40AF'),
    ('b2222222-2222-2222-2222-222222222222', 'Saúde Digital Co', 'saúde', 'motivacional', 'pt-BR', '#10B981', '#059669');

-- ============================================================
-- 2. USUÁRIOS
-- ============================================================

INSERT INTO users (id, workspace_id, nome, email, senha_hash, papel, ativo)
VALUES
    -- Workspace AppStudio
    ('d1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111',
     'Carlos Admin', 'carlos@appstudio.com', '$2b$12$placeholder_hash_admin', 'admin', true),
    ('d2222222-2222-2222-2222-222222222222', 'a1111111-1111-1111-1111-111111111111',
     'Ana Editora', 'ana@appstudio.com', '$2b$12$placeholder_hash_editor', 'editor', true),
    -- Workspace Saúde Digital
    ('d3333333-3333-3333-3333-333333333333', 'b2222222-2222-2222-2222-222222222222',
     'Beatriz Admin', 'beatriz@saudedigital.com', '$2b$12$placeholder_hash_admin2', 'admin', true);

-- ============================================================
-- 3. APLICATIVOS
-- ============================================================

INSERT INTO apps (id, workspace_id, nome, categoria, descricao, publico_alvo,
                  funcionalidades, diferenciais, cta, link_download,
                  plataformas, formato_youtube, frequencia, horario_disparo,
                  dias_semana, status, keywords)
VALUES
    -- App 1 — Workspace AppStudio (disparo às 8h, diário)
    ('aa111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111',
     'FocusTimer Pro', 'produtividade',
     'Aplicativo de timer Pomodoro com gamificação e relatórios de produtividade.',
     'Profissionais e estudantes 18-35 anos que buscam aumentar produtividade',
     '["Timer Pomodoro personalizável", "Gamificação com conquistas", "Relatórios semanais", "Modo foco com bloqueio de apps"]'::jsonb,
     '["Único com gamificação integrada", "Relatórios detalhados de produtividade", "Sincronização entre dispositivos"]'::jsonb,
     'Baixe grátis e seja mais produtivo!',
     'https://play.google.com/store/apps/details?id=com.focustimer',
     '["instagram", "youtube"]'::jsonb,
     'ambos', 'diaria', 8, NULL, 'ativo',
     '["produtividade", "pomodoro", "foco", "gestão de tempo"]'::jsonb),

    -- App 2 — Workspace AppStudio (disparo às 10h, 3x/semana)
    ('aa222222-2222-2222-2222-222222222222', 'a1111111-1111-1111-1111-111111111111',
     'GastoZero', 'finanças',
     'Controle financeiro pessoal simplificado com categorização automática por IA.',
     'Jovens adultos 20-40 anos que querem organizar finanças pessoais',
     '["Categorização automática de gastos", "Alertas de orçamento", "Metas de economia", "Dashboard visual"]'::jsonb,
     '["IA categoriza gastos automaticamente", "Setup em menos de 2 minutos", "100% gratuito sem anúncios"]'::jsonb,
     'Organize suas finanças em 2 minutos!',
     'https://apps.apple.com/app/gastozero',
     '["instagram", "youtube"]'::jsonb,
     '16_9', '3x_semana', 10, '[1, 3, 5]'::jsonb, 'ativo',
     '["finanças pessoais", "controle financeiro", "economia", "orçamento"]'::jsonb),

    -- App 3 — Workspace Saúde Digital (disparo às 9h, diário)
    ('aa333333-3333-3333-3333-333333333333', 'b2222222-2222-2222-2222-222222222222',
     'MeditaCalma', 'saúde',
     'App de meditação guiada com sessões de 5 a 30 minutos para iniciantes e avançados.',
     'Mulheres 25-45 interessadas em bem-estar mental e meditação',
     '["Meditações guiadas de 5-30min", "Sons da natureza", "Rastreador de humor", "Lembretes personalizados"]'::jsonb,
     '["Meditações em português com sotaque brasileiro", "Programa de 21 dias para iniciantes", "Modo offline"]'::jsonb,
     'Comece a meditar hoje — é grátis!',
     'https://play.google.com/store/apps/details?id=com.meditacalma',
     '["instagram", "youtube"]'::jsonb,
     'ambos', 'diaria', 9, NULL, 'ativo',
     '["meditação", "mindfulness", "saúde mental", "bem-estar", "relaxamento"]'::jsonb);

-- ============================================================
-- 4. MEDIA ASSETS
-- ============================================================

INSERT INTO media_assets (workspace_id, app_id, nome, url_storage, tipo, tags, tamanho_bytes, largura, altura)
VALUES
    -- Assets do app FocusTimer
    ('a1111111-1111-1111-1111-111111111111', 'aa111111-1111-1111-1111-111111111111',
     'screenshot_timer.png', 'media-bank/appstudio/focustimer/screenshot_timer.png',
     'imagem', '["screenshot", "produto", "timer"]'::jsonb, 524288, 1080, 1920),
    ('a1111111-1111-1111-1111-111111111111', 'aa111111-1111-1111-1111-111111111111',
     'demo_gamificacao.mp4', 'media-bank/appstudio/focustimer/demo_gamificacao.mp4',
     'video', '["produto", "demo", "gamificação"]'::jsonb, 5242880, 1080, 1920),
    -- Asset global do workspace AppStudio
    ('a1111111-1111-1111-1111-111111111111', NULL,
     'logo_appstudio.png', 'media-bank/appstudio/global/logo.png',
     'imagem', '["logo", "marca"]'::jsonb, 102400, 512, 512),
    -- Asset do app MeditaCalma
    ('b2222222-2222-2222-2222-222222222222', 'aa333333-3333-3333-3333-333333333333',
     'meditacao_natureza.jpg', 'media-bank/saudedigital/meditacalma/natureza.jpg',
     'imagem', '["lifestyle", "natureza", "relaxamento"]'::jsonb, 819200, 1920, 1080);

-- ============================================================
-- 5. CONTEÚDOS
-- ============================================================

INSERT INTO conteudos (id, app_id, tipo_conteudo, roteiro, titulo,
                       descricao_youtube, descricao_instagram,
                       hashtags_youtube, hashtags_instagram,
                       keywords_visuais, keywords_seo, status)
VALUES
    ('cc111111-1111-1111-1111-111111111111', 'aa111111-1111-1111-1111-111111111111',
     'problema_solucao',
     'Você sente que o dia passa e você não conseguiu fazer nada produtivo? O FocusTimer Pro vai mudar isso. Com o método Pomodoro adaptado e gamificação, você transforma sua rotina em missões diárias. Cada foco completado é uma conquista desbloqueada. Baixe grátis e seja mais produtivo!',
     'Como ser MAIS PRODUTIVO com o método Pomodoro gamificado',
     'Descubra como o FocusTimer Pro usa gamificação para turbinar sua produtividade com o método Pomodoro. Timer personalizável, conquistas e relatórios detalhados.',
     'Cansou de procrastinar? O FocusTimer Pro transforma foco em jogo. Baixe grátis!',
     '["produtividade", "pomodoro", "foco", "gestão de tempo", "app produtividade"]'::jsonb,
     '["#produtividade", "#pomodoro", "#foco", "#gestaoDeTempo", "#appProdutividade"]'::jsonb,
     '["pessoa trabalhando", "timer", "foco", "escritório"]'::jsonb,
     '["app produtividade", "pomodoro timer", "foco"]'::jsonb,
     'concluido');

-- ============================================================
-- 6. VÍDEOS
-- ============================================================

INSERT INTO videos (id, conteudo_id, app_id,
                    url_storage_vertical, duracao_vertical_segundos,
                    url_storage_horizontal, duracao_horizontal_segundos,
                    tamanho_bytes_total, status)
VALUES
    ('ef111111-1111-1111-1111-111111111111',
     'cc111111-1111-1111-1111-111111111111',
     'aa111111-1111-1111-1111-111111111111',
     'videos/focustimer/v1_vertical.mp4', 45,
     'videos/focustimer/v1_horizontal.mp4', 45,
     15728640, 'aguardando_aprovacao');

-- ============================================================
-- 7. EXECUTION LOGS
-- ============================================================

INSERT INTO execution_logs (app_id, video_id, etapa, status, mensagem)
VALUES
    ('aa111111-1111-1111-1111-111111111111', 'ef111111-1111-1111-1111-111111111111',
     'geracao_conteudo', 'sucesso', 'Conteúdo gerado pelo Gemini com sucesso'),
    ('aa111111-1111-1111-1111-111111111111', 'ef111111-1111-1111-1111-111111111111',
     'geracao_audio', 'sucesso', 'Narração gerada via Edge TTS (pt-BR-AntonioNeural)'),
    ('aa111111-1111-1111-1111-111111111111', 'ef111111-1111-1111-1111-111111111111',
     'montagem_video', 'sucesso', 'Vídeo vertical e horizontal montados com sucesso'),
    ('aa111111-1111-1111-1111-111111111111', 'ef111111-1111-1111-1111-111111111111',
     'validacao', 'sucesso', 'Validação automática passou em ambos os formatos');

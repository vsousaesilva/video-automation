# Sessoes de Implementacao — Usina do Tempo

## Sessao 1 — Modularizacao do Backend
- **Data:** 2026-04-12
- **Status:** Concluida
- **O que foi feito:**
  - Criada estrutura `core/` com arquivos compartilhados:
    - `core/config.py` — configuracao Pydantic (movido de `config.py`)
    - `core/db.py` — cliente Supabase (movido de `db.py`)
    - `core/auth.py` — autenticacao JWT, hash de senha, roles (movido de `auth_deps.py`)
    - `core/schemas.py` — schemas compartilhados (auth, workspace, user)
  - Criada estrutura `modules/video_engine/` com:
    - `schemas.py` — schemas do video engine (App, Video, Conteudo, Media, Pipeline)
    - `routers/` — 8 routers (apps, media, pipeline, conteudos, videos, publish, approvals, telegram_webhook)
    - `services/` — 12 services (gemini, tts, pexels, video_builder, video_validator, media_selector, storage, publisher_youtube, publisher_instagram, publisher_orchestrator, telegram_bot, notifier)
  - Core routers (auth, workspaces, users) permanecem em `routers/` com imports atualizados para `core.*`
  - Backward-compatibility wrappers criados nos arquivos antigos (config.py, db.py, auth_deps.py, models/schemas.py, services/*.py, routers/*.py antigos)
  - `main.py` atualizado para importar de `core` e `modules.video_engine.routers`
  - Endpoint `/health` mantido
  - Todos os endpoints mantidos nos mesmos paths (zero breaking changes)
- **Decisoes tomadas:**
  - Core routers (auth, workspaces, users) ficam em `routers/` (sao plataforma, nao modulo)
  - Video engine routers e services movidos para `modules/video_engine/`
  - Wrappers de re-export mantidos nos locais antigos para compatibilidade
  - Renomeacao App -> Negocio adiada para Sessao 2
- **Estrutura final:**
  ```
  backend/
  ├── main.py (atualizado)
  ├── core/
  │   ├── __init__.py
  │   ├── config.py
  │   ├── db.py
  │   ├── auth.py
  │   └── schemas.py
  ├── modules/
  │   ├── __init__.py
  │   └── video_engine/
  │       ├── __init__.py
  │       ├── schemas.py
  │       ├── routers/ (8 routers)
  │       └── services/ (12 services)
  ├── routers/ (core: auth, workspaces, users)
  ├── config.py (wrapper)
  ├── db.py (wrapper)
  ├── auth_deps.py (wrapper)
  ├── models/schemas.py (wrapper)
  ├── services/*.py (wrappers)
  └── migrations/
  ```
- **Pendencias:**
  - Renomeacao App -> Negocio (planejada para Sessao 2)
  - Deploy no Render para validar em producao
  - Remover wrappers de compatibilidade quando todos os imports estiverem atualizados
- **Proxima sessao:** Sessao 2 — Signup, Onboarding, Billing (Asaas) + Renomeacao App -> Negocio

---

## Sessao 2 — Signup, Onboarding, Billing (Asaas) + Renomeacao App -> Negocio
- **Data:** 2026-04-12
- **Status:** Concluida
- **O que foi feito:**

  **Migrations:**
  - `009_billing_and_rename_negocios.sql` — Rename apps->negocios + FKs, criar tabelas plans, subscriptions, invoices, usage_metrics, audit_log, ALTER workspaces (billing fields), atualizar RLS, add reset_token to users
  - `010_seed_plans.sql` — Seed 4 planos (free R$0, starter R$97, pro R$297, enterprise), criar subscription Pro para workspaces existentes

  **Backend — Billing:**
  - `core/config.py` — adicionados: asaas_api_key, asaas_base_url, asaas_webhook_token, frontend_url
  - `core/billing.py` — classe AsaasService (create_customer, create_subscription, get_subscription, cancel_subscription, get_payment_link) + helpers (get_workspace_subscription, get_workspace_usage, increment_usage)
  - `core/schemas.py` — adicionados: SignupRequest, ForgotPasswordRequest, ResetPasswordRequest, PlanResponse, SubscriptionResponse, CheckoutRequest, UsageResponse, InvoiceResponse
  - `routers/auth.py` — 3 novos endpoints: POST /auth/signup, POST /auth/forgot-password, POST /auth/reset-password
  - `routers/billing.py` — router completo: GET /billing/plans, GET /billing/subscription, GET /billing/usage, GET /billing/invoices, POST /billing/checkout, POST /billing/webhook, POST /billing/cancel

  **Backend — Renomeacao App -> Negocio (20+ arquivos):**
  - `modules/video_engine/schemas.py` — StatusApp->StatusNegocio, AppCreate->NegocioCreate, etc
  - `modules/video_engine/routers/negocios.py` — novo router (antigo apps.py reescrito)
  - `modules/video_engine/routers/__init__.py` — import negocios (nao mais apps)
  - `modules/video_engine/routers/pipeline.py` — process_app->process_negocio, tabelas apps->negocios
  - `modules/video_engine/routers/conteudos.py, videos.py, media.py, approvals.py, publish.py, telegram_webhook.py` — app_id->negocio_id, tabelas apps->negocios
  - `modules/video_engine/services/gemini.py, publisher_orchestrator.py, media_selector.py, publisher_youtube.py, publisher_instagram.py, video_builder.py, video_validator.py` — app_id->negocio_id em execution_logs
  - `main.py` — import negocios, registrar billing.router, title="Usina do Tempo"

  **Frontend — Novas paginas:**
  - `pages/Signup.jsx` — formulario de cadastro publico (nome, email, senha, workspace)
  - `pages/ForgotPassword.jsx` — solicitar link de recuperacao por email
  - `pages/ResetPassword.jsx` — redefinir senha com token via query param
  - `pages/Onboarding.jsx` — wizard 3 etapas (dados workspace -> integracoes -> primeiro negocio)
  - `pages/Billing.jsx` — plano atual, uso do mes, grid de planos, faturas

  **Frontend — Renomeacao App -> Negocio:**
  - `pages/Negocios.jsx` — novo (antigo Apps.jsx reescrito com API /negocios)
  - `pages/History.jsx` — apps->negocios, /apps->>/negocios, app_nome->negocio_nome
  - `pages/Dashboard.jsx` — app_id->negocio_id
  - `pages/Approvals.jsx` — app_nome->negocio_nome, app_id->negocio_id
  - `pages/Settings.jsx` — MediaUploader prop appId->negocioId
  - `pages/Login.jsx` — branding "Usina do Tempo", links signup/forgot-password
  - `components/MediaUploader.jsx` — prop appId->negocioId, API /media/app->>/media/negocio
  - `components/Layout.jsx` — nav "Apps"->"Negocios", branding, add link Billing
  - `components/PipelineTimeline.jsx` — item.app->item.negocio
  - `stores/dashboardStore.js` — /apps->>/negocios, apps->negocios
  - `stores/authStore.js` — adicionado action signup
  - `App.jsx` — rotas: /signup, /forgot-password, /reset-password, /onboarding, /negocios, /settings/billing

- **Decisoes tomadas:**
  - Asaas sandbox como default, producao via env
  - Signup cria workspace + user admin + subscription trial 7 dias
  - Webhook Asaas trata PAYMENT_CONFIRMED, PAYMENT_OVERDUE, SUBSCRIPTION_DELETED
  - Onboarding e tela separada (sem layout), acessivel apos login
  - Billing acessivel em /settings/billing com link no sidebar
  - Apps.jsx mantido como arquivo legado (nao mais importado)
- **Pendencias:**
  - Executar migrations 009 e 010 no Supabase
  - Configurar variaveis de ambiente Asaas (ASAAS_API_KEY, ASAAS_WEBHOOK_TOKEN)
  - Testar fluxo completo: signup -> login -> onboarding -> billing
  - Remover arquivo legado Apps.jsx quando confirmado
- **Proxima sessao:** Sessao 3 — Fila de Processamento (Redis + Celery)

---

## Sessao 3 — Fila de Processamento (Redis + Celery)
- **Data:** 2026-04-12
- **Status:** Concluida
- **O que foi feito:**

  **Infraestrutura (render.yaml):**
  - Adicionado serviço Redis (`usina-redis`, plano starter $7/mês)
  - Adicionado Celery worker (`usina-celery-video`, plano starter $7/mês) — consome filas `video` e `default`
  - Adicionado Flower dashboard (`usina-flower`, plano free) — monitoramento de tasks com basic auth
  - `REDIS_URL` injetada via `fromService` nos serviços API, worker e Flower

  **Backend — Celery Core:**
  - `core/config.py` — adicionado `redis_url` (default `redis://localhost:6379/0`)
  - `core/tasks.py` — configuração do Celery app (`usina_do_tempo`): broker/backend Redis, task_acks_late, worker_prefetch_multiplier=1, task_reject_on_worker_lost, rotas de filas por módulo, autodiscover de tasks
  - `requirements.txt` — adicionados `celery[redis]>=5.4.0`, `redis>=5.0.0`, `flower>=2.0.0`

  **Backend — Tasks do Video Engine:**
  - `modules/video_engine/tasks.py` — 3 tasks Celery:
    - `process_negocio_task` — processa 1 negócio (retry 3x, backoff exponencial, jitter)
    - `publish_all_platforms_task` — publica vídeo em todas plataformas (retry 3x, backoff)
    - `process_all_negocios_task` — fan-out: enfileira cada negócio como task individual

  **Backend — Migração de Jobs:**
  - `modules/video_engine/routers/pipeline.py`:
    - Removido `BackgroundTasks` do endpoint `/trigger`
    - Adicionada função `_celery_available()` que verifica conectividade com Redis
    - Endpoint agora usa `process_negocio_task.delay()` com fallback para `asyncio.create_task` se Redis indisponível
  - `modules/video_engine/routers/telegram_webhook.py`:
    - `_handle_aprovar()` — publicação via `publish_all_platforms_task.delay()` com fallback asyncio
    - `_handle_regenerar()` — regeneração via `process_negocio_task.delay()` com fallback asyncio

  **Backend — Endpoint de Status:**
  - `routers/tasks.py` — novo router:
    - `GET /tasks/status/{task_id}` — consulta status de tarefa Celery (PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED)
    - `POST /tasks/revoke/{task_id}` — cancela tarefa pendente/em execução
  - `main.py` — registrado `tasks.router`

- **Decisoes tomadas:**
  - Celery workers síncronos — funções async executadas via `asyncio.run()` dentro das tasks
  - Fallback para asyncio quando Redis indisponível (resilência em dev e durante deploys)
  - Fan-out: trigger enfileira cada negócio como task individual (retry independente por negócio)
  - `task_acks_late=True` + `task_reject_on_worker_lost=True` — tasks sobrevivem a crash do worker
  - Backoff exponencial com jitter para evitar thundering herd em retries
  - Filas separadas: `video` para tasks pesadas, `default` para o resto
  - Flower com basic auth para monitoramento em produção

- **Pendencias:**
  - Criar serviço Redis no Render e configurar `REDIS_URL`
  - Configurar `FLOWER_USER` e `FLOWER_PASSWORD` no Render
  - Testar fluxo completo: trigger → Celery → worker → banco
  - Testar retry: simular falha e verificar reprocessamento
  - Testar fallback: parar Redis e verificar que asyncio assume

- **Proxima sessao:** Sessao 4 — Segurança, Auditoria e Hardening

---

## Sessao 4 — Segurança, Auditoria e Hardening
- **Data:** 2026-04-12
- **Status:** Concluida
- **O que foi feito:**

  **Migration (011_security_hardening.sql):**
  - Campos brute-force: `login_attempts`, `locked_until` na tabela users
  - Campos verificação de email: `email_verified`, `email_verification_code`, `email_verification_expires_at`
  - Campos LGPD: `deletion_requested_at`, `deletion_scheduled_for` na tabela workspaces
  - Índices adicionais para audit_log (user_id, acao, recurso)
  - Índice para brute-force lookup (users.email + ativo)
  - Funções SQL `rotate_execution_logs(dias)` e `rotate_audit_logs(dias)`
  - RLS habilitado em audit_log com policy de isolamento por workspace
  - Users existentes marcados como email_verified=true

  **Backend — Rate Limiting (core/rate_limit.py):**
  - SlowAPI integrado com identificador por workspace_id (autenticado) ou IP (anônimo)
  - Storage via Redis em produção, memória em desenvolvimento
  - Login: 5 req/min por IP
  - Signup: 3 req/min por IP
  - API geral: 60 req/min por workspace (default)
  - Reenvio de verificação: 2 req/min
  - Handler customizado para 429 com mensagem em português

  **Backend — Brute-force Protection (core/rate_limit.py):**
  - `check_login_lockout()` — verifica se conta está bloqueada
  - `record_failed_login()` — incrementa tentativas, bloqueia após 5 falhas por 15 min
  - `reset_login_attempts()` — reseta contadores após login bem-sucedido
  - Integrado no endpoint POST /auth/login

  **Backend — CORS Restritivo (main.py):**
  - Dev: permite apenas `frontend_url` (localhost:5173)
  - Produção: whitelist de `app.usinadotempo.com.br`, `usinadotempo.com.br`, `www.usinadotempo.com.br`
  - `allow_methods` e `allow_headers` explícitos (não mais `*`)

  **Backend — Security Headers Middleware (core/middleware.py):**
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
  - Produção: `Strict-Transport-Security` (HSTS) + `Content-Security-Policy`

  **Backend — Audit Log Middleware (core/middleware.py):**
  - Middleware intercepta requests e registra ações sensíveis na tabela audit_log
  - Ações rastreadas: login, signup, forgot_password, reset_password, change_password, create_negocio, delete_negocio, trigger_pipeline, publish_video, approve_video, billing_checkout, billing_cancel, invite_user, remove_user, export_data, delete_data_request
  - Registra: user_id, workspace_id, IP, user_agent, status code

  **Backend — Billing Enforcement Middleware (core/middleware.py):**
  - Verifica limites do plano antes de executar ações que consomem recursos
  - POST /pipeline/trigger → verifica videos_gerados vs max_videos_mes
  - POST /negocios → verifica contagem de negócios vs max_negocios
  - Retorna 429 com mensagem clara quando limite atingido

  **Backend — Criptografia de Credenciais (core/crypto.py):**
  - Fernet (AES-128-CBC) para criptografar tokens de APIs externas
  - Chave derivada do secret_key via PBKDF2 (100k iterações)
  - `encrypt_value()` / `decrypt_value()` prontas para uso nos services

  **Backend — LGPD Endpoints (routers/privacy.py):**
  - `GET /privacy/my-data` — exporta todos os dados do workspace em JSON (Art. 18 LGPD)
  - `DELETE /privacy/my-data` — agenda exclusão para 30 dias (carência para cancelamento)
  - `POST /privacy/cancel-deletion` — cancela solicitação de exclusão pendente

  **Backend — Rotação de Logs (core/maintenance.py):**
  - Task Celery `rotate_logs_task` executada diariamente via beat_schedule
  - Remove execution_logs > 90 dias via função SQL
  - Remove audit_logs > 365 dias via função SQL
  - Processa exclusões LGPD agendadas (anonimiza workspaces após 30 dias)

  **Backend — Verificação de Email:**
  - Signup gera código de 6 dígitos e envia via Resend
  - `POST /auth/verify-email` — verifica código
  - `POST /auth/resend-verification` — reenvia código (rate limited: 2/min)
  - Schema `VerifyEmailRequest` adicionado

  **Backend — Configuração:**
  - `requirements.txt` — adicionados `slowapi`, `cryptography`, `bcrypt`
  - `core/config.py` — adicionados `flower_user`, `flower_password`, `log_level`
  - `core/tasks.py` — beat_schedule para rotação diária, autodiscover de `core`
  - `main.py` — versão 0.2.0, middlewares registrados, privacy router incluído

  **Frontend — Páginas Públicas:**
  - `pages/TermosDeUso.jsx` — Termos de Uso completos (10 seções)
  - `pages/PoliticaPrivacidade.jsx` — Política de Privacidade LGPD (10 seções)
  - Rotas `/termos` e `/privacidade` adicionadas ao App.jsx

  **Frontend — Billing Banner:**
  - `components/BillingBanner.jsx` — banner contextual no topo do layout
  - Banner vermelho para pagamento pendente (past_due)
  - Banner laranja para assinatura cancelada/expirada
  - Banner amarelo para trial expirando (< 3 dias)
  - Banner azul para uso próximo do limite (>= 80%)
  - Banner vermelho para limite atingido (100%)
  - Todos com botão de dismiss e link para billing
  - Integrado no Layout.jsx acima do Outlet

  **Frontend — Links de Compliance:**
  - Login.jsx — links para Termos e Privacidade no footer
  - Signup.jsx — texto de consentimento com links antes do botão de cadastro

- **Decisoes tomadas:**
  - SlowAPI com storage Redis em prod, memória em dev (evita dependência Redis em dev)
  - Brute-force no banco (não em Redis) para persistir entre restarts do servidor
  - Fernet com chave derivada do secret_key (não requer nova variável de ambiente)
  - LGPD com carência de 30 dias antes da anonimização (evita exclusão acidental)
  - Audit log via middleware (não decorators) para capturar tudo sem modificar cada endpoint
  - Billing enforcement via middleware para bloquear antes do handler processar
  - Verificação de email não bloqueia o uso (pode usar sem verificar, mas é incentivado)

- **Arquivos criados/modificados:**
  ```
  Criados:
  - backend/migrations/011_security_hardening.sql
  - backend/core/middleware.py (SecurityHeaders, AuditLog, BillingEnforcement)
  - backend/core/crypto.py (Fernet encrypt/decrypt)
  - backend/core/rate_limit.py (SlowAPI + brute-force)
  - backend/core/maintenance.py (rotação de logs Celery task)
  - backend/routers/privacy.py (LGPD endpoints)
  - frontend/src/pages/TermosDeUso.jsx
  - frontend/src/pages/PoliticaPrivacidade.jsx
  - frontend/src/components/BillingBanner.jsx

  Modificados:
  - backend/main.py (CORS restritivo, middlewares, privacy router, v0.2.0)
  - backend/core/config.py (novos campos)
  - backend/core/schemas.py (VerifyEmailRequest)
  - backend/core/tasks.py (beat_schedule, autodiscover core)
  - backend/routers/auth.py (brute-force, rate limit, email verification)
  - backend/requirements.txt (slowapi, cryptography, bcrypt)
  - frontend/src/App.jsx (rotas /termos, /privacidade)
  - frontend/src/components/Layout.jsx (BillingBanner)
  - frontend/src/pages/Login.jsx (links Termos/Privacidade)
  - frontend/src/pages/Signup.jsx (consentimento Termos/Privacidade)
  ```

- **Pendencias:**
  - Executar migration 011 no Supabase
  - Configurar `SECRET_KEY` forte em produção (obrigatório para Fernet)
  - Testar rate limiting com Redis em produção
  - Testar brute-force: 5 tentativas → lockout → desbloqueio após 15 min
  - Testar CORS: requisição de domínio não autorizado deve ser rejeitada
  - Testar billing enforcement: criar vídeo além do limite → 429
  - Testar export de dados LGPD (GET /privacy/my-data)
  - Integrar `encrypt_value`/`decrypt_value` nos services que salvam tokens de APIs externas
  - Configurar pg_cron ou Celery Beat em produção para rotação de logs

- **Proxima sessao:** Sessao 5 — Dashboard Unificado

---

## Sessao 5 — Dashboard Unificado
- **Data:** 2026-04-13
- **Status:** Concluida
- **O que foi feito:**

  **Backend — Modulo Dashboard (modules/dashboard/):**
  - `modules/dashboard/__init__.py` — init do modulo
  - `modules/dashboard/router.py` — 4 endpoints:
    - `GET /dashboard/overview` — KPIs gerais (negocios ativos, videos gerados/publicados mes, aprovacoes pendentes, taxa aprovacao 30d, plano atual)
    - `GET /dashboard/video-engine` — metricas detalhadas (videos por status, evolucao diaria 30d, top negocios por publicacoes)
    - `GET /dashboard/usage` — consumo vs limites do plano (negocios, videos, conteudos, storage com barras de progresso)
    - `GET /dashboard/timeline` — atividade recente cross-modulo via audit_log (ultimas N acoes com descricao humanizada)
  - `modules/dashboard/services/__init__.py`
  - `modules/dashboard/services/aggregator.py` — servico de agregacao com:
    - Cache Redis (TTL 60s para KPIs, 30s para timeline) com fallback sem cache
    - `get_overview()` — query otimizada para KPIs gerais
    - `get_video_engine_metrics()` — metricas por status, evolucao 30d, top negocios
    - `get_usage_vs_limits()` — consumo atual com percentuais vs limites do plano
    - `get_timeline()` — audit_log com `_humanize_acao()` para textos legiveis

  **Backend — Configuracao:**
  - `main.py` — import dashboard router, versao 0.3.0, registrado dashboard_router.router

  **Frontend — Dashboard Reescrito (Dashboard.jsx):**
  - 4 cards KPI com icones: negocios ativos, videos gerados/publicados (mes), aprovacoes pendentes + taxa aprovacao
  - Grafico de evolucao (Recharts AreaChart) — ultimos 14 dias, linhas gerados vs publicados com gradientes
  - Painel de videos por status — breakdown com dots coloridos por status
  - Widget de uso do plano — barras de progresso com cores por nivel (verde < 80%, amarelo >= 80%, vermelho >= 100%), link para gerenciar plano
  - Timeline de atividade recente — lista scrollavel com timestamps formatados pt-BR
  - Top negocios — ranking por videos publicados nos ultimos 30 dias
  - Acoes rapidas — atalhos para criar negocio, revisar aprovacoes (com badge de pendentes), banco de midia, historico
  - Aprovacoes pendentes — grid de cards com link para revisar (so aparece se houver pendentes)

  **Frontend — dashboardStore.js:**
  - Reescrito para consumir 4 novos endpoints do backend (/dashboard/overview, /video-engine, /usage, /timeline)
  - Mantido fetchPendingVideos para badge no Layout
  - fetchAll() executa todos os fetches em paralelo

  **Frontend — Dependencia:**
  - `recharts ^2.15.0` adicionado ao package.json para graficos

- **Decisoes tomadas:**
  - Aggregator com cache Redis + fallback sem cache (funciona em dev sem Redis)
  - Queries otimizadas no backend (contagem via count="exact", filtros por data) em vez de N+1 no frontend
  - Dashboard antigo fazia N+1 requests (1 por negocio para buscar historico); novo faz 5 requests paralelos independente do numero de negocios
  - Recharts escolhido por ser leve, declarativo e compativel com React 19
  - Grafico mostra 14 dias (nao 30) para melhor legibilidade visual
  - Timeline consome audit_log (ja populado pelo AuditLogMiddleware da Sessao 4)
  - Top negocios limitado a 5 para nao poluir o dashboard
  - Cache TTL curto (60s KPIs, 30s timeline) para dados quase real-time

- **Arquivos criados/modificados:**
  ```
  Criados:
  - backend/modules/dashboard/__init__.py
  - backend/modules/dashboard/router.py
  - backend/modules/dashboard/services/__init__.py
  - backend/modules/dashboard/services/aggregator.py

  Modificados:
  - backend/main.py (import dashboard, v0.3.0)
  - frontend/src/pages/Dashboard.jsx (reescrito completo)
  - frontend/src/stores/dashboardStore.js (reescrito para novos endpoints)
  - frontend/package.json (adicionado recharts)
  ```

- **Pendencias:**
  - Executar `npm install` no frontend para instalar recharts
  - Testar dashboard com dados reais no Supabase
  - Verificar que audit_log esta sendo populado pelo middleware (necessario para timeline)
  - Testar cache Redis em producao
  - Testar dashboard com plano Free (dados limitados/zerados)

- **Proxima sessao:** Sessao 6 — Content AI

---

## Sessao 6 — Content AI
- **Data:** 2026-04-13
- **Status:** Concluida
- **O que foi feito:**

  **Migration (012_content_ai.sql):**
  - Tabela `content_templates` — templates de prompts reutilizaveis (nome, tipo, tom_voz, prompt_template com placeholders, variaveis JSONB)
  - Tabela `content_requests` — requisicoes de geracao (tipo, tom_voz, idioma, prompt_usuario, contexto JSONB, quantidade, status)
  - Tabela `generated_contents` — conteudos gerados (titulo, conteudo, metadata JSONB, tokens_usados, avaliacao 1-5, usado_em)
  - Indices otimizados por workspace_id, tipo, status, criado_em
  - RLS habilitado em todas as tabelas com policy de isolamento por workspace

  **Backend — Modulo Content AI (modules/content_ai/):**
  - `schemas.py` — enums TipoConteudoAI (6 tipos) e TomVoz (8 tons), schemas de request/response para generate, templates, rate, use-in-video
  - `router.py` — 9 endpoints:
    - `POST /content-ai/generate` — gerar conteudo (copy, legenda, roteiro, artigo, resposta_comentario, email_marketing)
    - `GET /content-ai/history` — historico com filtros (tipo, negocio_id, paginacao)
    - `GET /content-ai/history/{id}` — detalhes de uma geracao com conteudos
    - `GET /content-ai/templates` — listar templates do workspace
    - `POST /content-ai/templates` — criar template customizado
    - `PUT /content-ai/templates/{id}` — atualizar template
    - `DELETE /content-ai/templates/{id}` — soft-delete template
    - `POST /content-ai/rate/{id}` — avaliar conteudo gerado (1-5 estrelas)
    - `POST /content-ai/use-in-video` — enviar conteudo para Video Engine (cria na tabela conteudos)
  - `services/generator.py` — integracao Gemini com:
    - Prompts especializados por tipo (SYSTEM_PROMPTS e OUTPUT_FORMATS)
    - Suporte a templates customizados com placeholders {{variavel}}
    - Contexto automatico do negocio (busca dados se negocio_id fornecido)
    - Multiplas variacoes (1-5) com temperatura variavel
    - Retry 3x com fallback
    - Incremento automatico de conteudos_gerados no billing

  **Backend — Celery Tasks (modules/content_ai/tasks.py):**
  - `generate_content_task` — task individual com retry 2x, backoff exponencial
  - `generate_batch_task` — fan-out: enfileira multiplas geracoes como tasks individuais

  **Backend — Configuracao:**
  - `core/tasks.py` — autodiscover atualizado para incluir `modules.content_ai`
  - `core/middleware.py` — billing enforcement para `POST /content-ai/generate` (verifica conteudos_gerados vs max_conteudos_mes)
  - `core/middleware.py` — audit log para `POST /content-ai/generate` e `POST /content-ai/use-in-video`
  - `main.py` — import content_ai router, versao 0.4.0

  **Frontend — Pagina Content AI (ContentAI.jsx):**
  - 3 abas: Gerar Conteudo, Historico, Templates
  - Aba Gerar:
    - Seletor visual de tipo de conteudo (6 opcoes com descricao)
    - Seletor de tom de voz (8 opcoes)
    - Seletor de negocio (opcional, puxa dados automaticamente)
    - Seletor de plataforma (para copy_ads e legenda)
    - Seletor de template (filtra por tipo)
    - Campo de instrucoes adicionais (textarea)
    - Slider de variacoes (1-5)
    - Preview de resultado com copiar, avaliar (estrelas) e usar no Video Engine
    - Loading state com animacao
  - Aba Historico:
    - Filtro por tipo de conteudo
    - Lista expansivel de geracoes com status, data, quantidade de resultados
    - Detalhes expandidos com conteudos gerados, copiar, avaliacao
  - Aba Templates:
    - Grid de templates com nome, tipo, preview do prompt
    - Formulario de criacao com placeholders
    - Soft-delete e acao "Usar este template"

  **Frontend — Navegacao:**
  - `App.jsx` — rota `/content-ai` adicionada
  - `Layout.jsx` — link "Content AI" no sidebar com icone de lampada

- **Decisoes tomadas:**
  - 6 tipos de conteudo cobrindo os principais formatos de marketing digital
  - Prompts especializados por tipo (system prompt diferente para cada)
  - Templates com placeholders {{variavel}} para reutilizacao
  - Temperatura variavel entre variacoes (0.85 + 0.05 * i) para diversidade
  - Integracao com Video Engine via endpoint dedicado (cria conteudo na tabela conteudos)
  - Billing enforcement via middleware (reutiliza padrao da Sessao 4)
  - Avaliacao de conteudo (1-5 estrelas) para feedback loop futuro
  - Soft-delete em templates (campo ativo=false)

- **Arquivos criados/modificados:**
  ```
  Criados:
  - backend/migrations/012_content_ai.sql
  - backend/modules/content_ai/__init__.py
  - backend/modules/content_ai/schemas.py
  - backend/modules/content_ai/router.py
  - backend/modules/content_ai/tasks.py
  - backend/modules/content_ai/services/__init__.py
  - backend/modules/content_ai/services/generator.py
  - frontend/src/pages/ContentAI.jsx

  Modificados:
  - backend/main.py (import content_ai, v0.4.0)
  - backend/core/tasks.py (autodiscover content_ai)
  - backend/core/middleware.py (billing + audit para content-ai)
  - frontend/src/App.jsx (rota /content-ai)
  - frontend/src/components/Layout.jsx (nav link + icone ContentAI)
  ```

- **Pendencias:**
  - Executar migration 012 no Supabase
  - Testar geracao de cada tipo (copy_ads, legenda, roteiro, artigo, resposta_comentario, email_marketing)
  - Testar template customizado com placeholders
  - Testar integracao "Usar no Video Engine" (gerar roteiro → criar conteudo no pipeline)
  - Testar billing enforcement (limite de conteudos_gerados)
  - Testar avaliacao de conteudo (1-5 estrelas)
  - Verificar que audit_log registra geracoes

- **Proxima sessao:** Sessao 7 — CRM

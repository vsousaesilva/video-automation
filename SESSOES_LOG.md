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

---

## Sessao 7 — CRM
- **Data:** 2026-04-13
- **Status:** Concluida
- **O que foi feito:**

  **Migration (013_crm.sql):**
  - Tabela `deal_stages` — etapas do funil personalizaveis (nome, posicao, cor) com RLS
  - Tabela `contacts` — contatos com nome, email, telefone, empresa, cargo, origem, notas, dados_extras JSONB
  - Tabela `contact_tags` — tags com nome e cor (unique por workspace)
  - Tabela `contacts_tags` — juncao N:N contato <-> tag
  - Tabela `deals` — oportunidades com titulo, valor_centavos, status (aberto/ganho/perdido), stage_id, contact_id, responsavel_id, posicao_kanban
  - Tabela `activities` — atividades (nota, email, ligacao, reuniao, tarefa) vinculadas a contato e/ou deal
  - Indices otimizados por workspace_id, email, nome, criado_em, stage_id, contact_id
  - RLS habilitado em todas as tabelas com policy de isolamento por workspace
  - Seed: 6 etapas padrao do funil para workspaces existentes (Novo Lead, Qualificado, Proposta, Negociacao, Ganho, Perdido)

  **Backend — Modulo CRM (modules/crm/):**
  - `schemas.py` — enums OrigemContato (6), TipoAtividade (5), StatusDeal (3); schemas de request/response para contacts, tags, stages, deals, activities, import
  - `router.py` — 24 endpoints:
    - CRUD de contatos (`GET/POST/PUT/DELETE /crm/contacts`, `GET /crm/contacts/{id}`)
    - Importacao CSV (`POST /crm/contacts/import`)
    - CRUD de tags (`GET/POST/PUT/DELETE /crm/tags`)
    - CRUD de etapas do funil (`GET/POST/PUT/DELETE /crm/stages`)
    - CRUD de deals (`GET/POST/PUT/DELETE /crm/deals`, `PUT /crm/deals/{id}/move`)
    - CRUD de atividades (`GET/POST/PUT/DELETE /crm/activities`)
  - `services/importer.py` — importacao de contatos via CSV/Excel:
    - Mapeamento flexivel de colunas (nome/name, email/e-mail, phone/telefone, etc.)
    - Suporte a CSV (utf-8-sig para BOM do Excel) e Excel (openpyxl)
    - Incremento automatico de contatos_crm no billing
    - Retorno detalhado de erros por linha

  **Backend — Integracao:**
  - `main.py` — import crm router, versao 0.5.0, registrado crm_router.router
  - `core/middleware.py` — billing enforcement para `POST /crm/contacts` (verifica contatos vs max_contatos_crm)
  - `core/middleware.py` — audit log para create_contact, delete_contact, import_contacts, create_deal, update_deal, delete_deal

  **Frontend — Pagina Contatos (Contacts.jsx):**
  - Tabela de contatos com busca (nome, email, empresa, telefone), filtro por tag, paginacao
  - Modal de criar/editar contato (nome, email, telefone, empresa, cargo, origem, tags, notas)
  - Importacao CSV com preview de resultado (criados/erros/detalhes)
  - Gerenciamento de tags (criar com cor, remover)
  - Soft-delete (desativar) contatos
  - Click na linha navega para detalhe do contato

  **Frontend — Detalhe do Contato (ContactDetail.jsx):**
  - Card com informacoes do contato (nome, cargo, email, telefone, empresa, tags, notas)
  - Timeline de atividades com icones por tipo (nota, email, ligacao, reuniao, tarefa)
  - Criar nova atividade (tipo, titulo, descricao)
  - Toggle concluida para tarefas
  - Remover atividade com confirmacao
  - Lista de deals/oportunidades vinculados ao contato

  **Frontend — Funil de Vendas (Funnel.jsx):**
  - Board kanban com colunas por etapa do funil
  - Drag-and-drop nativo (HTML5 DnD) para mover deals entre etapas
  - Cards com titulo, valor, contato associado
  - Totalizador por etapa e total do pipeline
  - Filtro por status (aberto/ganho/perdido)
  - Marcar deal como ganho/perdido direto do card
  - Modal de criar/editar deal (titulo, valor, etapa, contato, notas)
  - Atividade automatica registrada ao mover deal

  **Frontend — Navegacao:**
  - `App.jsx` — rotas `/crm`, `/crm/contacts/:id`, `/crm/funnel`
  - `Layout.jsx` — links "Contatos" e "Funil" no sidebar com icones

- **Decisoes tomadas:**
  - Soft-delete para contatos (ativo=false) para preservar historico de deals e atividades
  - Tags N:N com tabela de juncao (flexivel, sem limite de tags por contato)
  - Stages personalizaveis por workspace (seed com 6 padrao)
  - Deals com posicao_kanban para ordenacao dentro da etapa
  - Atividade automatica ao mover deal (rastreabilidade)
  - Importacao CSV com mapeamento flexivel de colunas (aceita ingles e portugues)
  - Billing enforcement via middleware (max_contatos_crm no plano)
  - Drag-and-drop nativo HTML5 (sem dependencia extra como react-beautiful-dnd)

- **Arquivos criados/modificados:**
  ```
  Criados:
  - backend/migrations/013_crm.sql
  - backend/modules/crm/__init__.py
  - backend/modules/crm/schemas.py
  - backend/modules/crm/router.py
  - backend/modules/crm/services/__init__.py
  - backend/modules/crm/services/importer.py
  - frontend/src/pages/Contacts.jsx
  - frontend/src/pages/ContactDetail.jsx
  - frontend/src/pages/Funnel.jsx

  Modificados:
  - backend/main.py (import crm, v0.5.0)
  - backend/core/middleware.py (billing + audit para CRM)
  - frontend/src/App.jsx (rotas /crm, /crm/contacts/:id, /crm/funnel)
  - frontend/src/components/Layout.jsx (nav links Contatos + Funil)
  ```

- **Pendencias:**
  - Executar migration 013 no Supabase
  - Testar CRUD de contatos (criar, editar, buscar, desativar)
  - Testar importacao CSV (com e sem erros)
  - Testar funil kanban (drag-and-drop entre etapas)
  - Testar timeline de atividades (criar nota, email, ligacao, reuniao, tarefa)
  - Testar billing enforcement (limite de contatos por plano)
  - Testar RLS (contatos isolados entre workspaces)
  - Instalar openpyxl se quiser suporte a Excel: `pip install openpyxl`

- **Proxima sessao:** Sessao 8 — Ads Manager (Meta Ads)

---

## Sessao 8 — Ads Manager (Meta Ads)
- **Data:** 2026-04-13
- **Status:** Concluida
- **O que foi feito:**

  **Migration (014_ads_manager.sql):**
  - `ad_accounts` — contas de anuncios vinculadas (plataforma, external_id, tokens criptografados, status, ultimo_sync)
  - `campaigns` — campanhas (objetivo, status, orcamento diario/total, datas, vinculo com ad_account)
  - `ad_sets` — conjuntos de anuncios (publico_alvo JSONB, orcamento)
  - `ads` — criativos (criativo JSONB com texto, headline, video_url, cta)
  - `ad_metrics_daily` — metricas diarias (impressoes, cliques, conversoes, gasto, receita, CTR, CPC, CPA, ROAS)
  - `ad_rules` — regras de automacao (escopo, condicao JSONB, acao, ativa, ultima_execucao)
  - Indices otimizados e unique constraints por (ad_account_id, external_id)
  - RLS habilitado em todas as tabelas com isolamento por workspace

  **Backend — Modulo Ads Manager (modules/ads_manager/):**
  - `schemas.py` — enums Plataforma (3), StatusAdAccount (3), EscopoRegra (3), AcaoRegra (4); schemas AdAccountConnect, CampaignAction, CampaignBudgetUpdate, RegraCondicao, AdRuleCreate/Update
  - `router.py` — 13 endpoints:
    - OAuth: `GET /ads/oauth/meta/url`
    - Contas: `POST /ads/accounts/connect`, `GET /ads/accounts`, `PUT/DELETE /ads/accounts/{id}`, `POST /ads/accounts/{id}/sync`
    - Campanhas: `GET /ads/campaigns`, `POST /ads/campaigns/{id}/action`, `PATCH /ads/campaigns/{id}/budget`
    - Metricas: `GET /ads/metrics` (totais + serie diaria)
    - Regras: `GET/POST /ads/rules`, `PUT/DELETE /ads/rules/{id}`, `POST /ads/rules/{id}/run`
  - Helper `_ensure_pro_plan` — bloqueia rotas sensiveis para planos free/starter (403)
  - `services/meta_ads.py`:
    - OAuth flow: `build_oauth_url`, `exchange_code_for_token` (short + long-lived tokens)
    - `list_ad_accounts` — lista contas do token
    - `sync_campaigns` — sincroniza campanhas e insights dos ultimos 7 dias via Graph API v20.0
    - `update_campaign_status` / `update_campaign_budget` — acoes na Meta Marketing API
    - Tokens criptografados via `core.crypto.decrypt_value` (Fernet — Sessao 4)
    - Tratamento de erros: token invalido marca conta como expirada
  - `services/rules_engine.py`:
    - `execute_rule` — avalia condicao (cpa/roas/ctr/gasto/cliques/impressoes) contra janelas de 1-30 dias
    - Operadores: >, <, >=, <=, ==
    - Acoes: pause, activate, adjust_budget (com ajuste_pct), notify
    - Registra ultima_execucao e ultima_acao no banco
    - `run_all_active_rules` — executa todas as regras ativas
  - `tasks.py`:
    - `sync_meta_campaigns_task` — diaria (autodiscover Celery)
    - `run_ad_rules_task` — horaria

  **Backend — Integracao:**
  - `main.py` — import ads_manager_router, versao 0.6.0, registrado ads_manager_router.router
  - `core/middleware.py` — audit log para ads_connect_account, ads_delete_account, ads_campaign_action, ads_campaign_budget, ads_create_rule, ads_update_rule, ads_delete_rule
  - `core/tasks.py` — autodiscover modules.ads_manager + beat schedule: sync-meta-campaigns-daily (24h), run-ad-rules-hourly (1h)

  **Frontend — Pagina Ads (Ads.jsx):**
  - 4 tabs: Campanhas, Metricas, Contas, Regras
  - **Campanhas:** tabela com nome, objetivo, status, orcamento; acoes pausar/ativar inline
  - **Metricas:** 7 cards (impressoes, cliques, conversoes, gasto, CPA, ROAS, CTR) + grafico de barras diario (gasto)
  - **Contas:** lista contas vinculadas com sync/desvincular; modal de vincular com external_id + access_token
  - **Regras:** builder visual "SE metrica operador valor em N dias ENTAO acao"; toggle ativa/pausada; executar agora; historico de ultima execucao
  - Tratamento de 403 (plano insuficiente) com CTA para upgrade
  - Uso do axios `api` client com auto-refresh de token

  **Frontend — Navegacao:**
  - `App.jsx` — rota `/ads`
  - `Layout.jsx` — link "Anuncios" no sidebar com icone megafone

- **Decisoes tomadas:**
  - Tokens OAuth criptografados com Fernet (core.crypto) — reuso da Sessao 4
  - `_ensure_pro_plan` como helper no router em vez de middleware global (permite endpoints de leitura acessiveis a Free)
  - Sync idempotente via upsert (on_conflict em external_id)
  - Insights de 7 dias em cada sync (diario via Celery beat)
  - Meta retorna budgets ja em centavos — armazenados sem conversao
  - Regras avaliam janelas agregadas (1-30 dias) para evitar ruido diario
  - `adjust_budget` recebe `ajuste_pct` (negativo reduz, positivo aumenta)
  - OAuth URL gerada no backend com state token (seguranca CSRF)
  - Conexao manual (external_id + access_token) tambem permitida para fluxo sem OAuth dialog

- **Arquivos criados/modificados:**
  ```
  Criados:
  - backend/migrations/014_ads_manager.sql
  - backend/modules/ads_manager/__init__.py
  - backend/modules/ads_manager/schemas.py
  - backend/modules/ads_manager/router.py
  - backend/modules/ads_manager/tasks.py
  - backend/modules/ads_manager/services/__init__.py
  - backend/modules/ads_manager/services/meta_ads.py
  - backend/modules/ads_manager/services/rules_engine.py
  - frontend/src/pages/Ads.jsx

  Modificados:
  - backend/main.py (import ads_manager, v0.6.0)
  - backend/core/middleware.py (audit log ads_*)
  - backend/core/tasks.py (autodiscover + beat: sync-meta-daily, run-rules-hourly)
  - frontend/src/App.jsx (rota /ads)
  - frontend/src/components/Layout.jsx (nav Anuncios + AdsIcon)
  ```

- **Pendencias:**
  - Executar migration 014 no Supabase
  - Cadastrar app Meta for Developers e configurar credenciais (meta_app_id, meta_app_secret)
  - Submeter app Meta a review (permissoes ads_management, ads_read, business_management)
  - Configurar redirect_uri no frontend para fluxo OAuth completo
  - Testar conexao manual (act_*** + access_token) antes do review
  - Testar sync real com conta Meta de teste
  - Testar pause/activate + ajuste de orcamento
  - Testar regras: criar regra "CPA > R$50 em 3d → pausar" e executar
  - Validar que planos Free/Starter recebem 403 nos endpoints sensiveis
  - Validar audit_log com eventos ads_*
  - Validar beat schedule rodando sync diario

- **Proxima sessao:** Sessao 9 — Ads Manager (Google Ads + TikTok Ads)

---

## Sessao 9 — Ads Manager (Google Ads + TikTok Ads)
- **Data:** 2026-04-13
- **Status:** Concluida
- **O que foi feito:**

  **Backend — core/config.py:**
  - Adicionados settings: `google_ads_client_id`, `google_ads_client_secret`, `google_ads_developer_token`, `google_ads_login_customer_id`, `google_ads_api_version` (default v17)
  - Adicionados settings: `tiktok_ads_app_id`, `tiktok_ads_app_secret`, `tiktok_ads_api_base` (default business-api.tiktok.com/open_api/v1.3)

  **Backend — services/google_ads.py (novo):**
  - OAuth: `build_oauth_url`, `exchange_code_for_token`, `refresh_access_token` com scope adwords
  - `_get_valid_token` — renovacao automatica via refresh_token (Google emite access_token curto de 1h; refresh_token de longa duracao)
  - `sync_campaigns` — GAQL via endpoint `googleAds:searchStream` para campanhas (status, budget, objetivo) + metricas diarias (impressions, clicks, cost_micros, conversions, conversion_value, ctr, avg_cpc)
  - Conversao micros → centavos (micros/10.000) para valores monetarios Google
  - `update_campaign_status` — mutate `customers/{id}/campaigns:mutate` com updateMask
  - `update_campaign_budget` — stub local (Google Ads requer mutate em campaign_budget separado; anotado para refinamento futuro)
  - Headers incluem `developer-token` e `login-customer-id` (MCC) quando configurado

  **Backend — services/tiktok_ads.py (novo):**
  - OAuth: `build_oauth_url`, `exchange_code_for_token` via `/oauth2/access_token/`, `list_advertisers`
  - TikTok retorna `advertiser_ids` no payload do OAuth — usado para pre-preenchimento se nao fornecido
  - `sync_campaigns` — GET `/campaign/get/` para campanhas + POST `/report/integrated/get/` (BASIC, AUCTION_CAMPAIGN) para metricas dos ultimos 7 dias
  - Normalizacao de status: STATUS_DISABLE/PAUSED → paused, STATUS_ENABLE/DELIVERY_OK → active
  - `update_campaign_status` — `/campaign/status/update/` com operation_status ENABLE/DISABLE
  - `update_campaign_budget` — `/campaign/update/` com budget (em unidades, nao centavos — conversao automatica) + budget_mode DAY/TOTAL

  **Backend — router.py (refatorado):**
  - Helper `_get_service(plataforma)` — dispatcher que carrega o modulo certo (meta_ads, google_ads, tiktok_ads)
  - `GET /ads/oauth/{plataforma}/url` — generico, funciona para meta/google/tiktok
  - `POST /ads/oauth/{plataforma}/callback` — troca code por token e faz upsert em ad_accounts. Suporta external_id via query param (ou extrai de `advertiser_ids` no TikTok)
  - `GET /ads/accounts?plataforma=` — filtro por plataforma
  - `POST /ads/accounts/{id}/sync` — roteia por plataforma da conta
  - `POST /ads/campaigns/{id}/action` — carrega `ad_accounts(plataforma)` via join, roteia
  - `PATCH /ads/campaigns/{id}/budget` — idem
  - `GET /ads/campaigns?plataforma=` — filtro cross-platform via join `ad_accounts!inner`
  - `GET /ads/metrics?plataforma=` — filtro por plataforma (via subquery em ad_account_ids)
  - `GET /ads/metrics/cross-platform` (novo) — agrega gasto/impressoes/cliques/conversoes/receita por plataforma + calcula CPA/ROAS/CTR de cada uma. Ordenado por gasto

  **Backend — services/rules_engine.py:**
  - Helper `_platform_service(plataforma)` — mesmo dispatcher
  - Query de campanhas agora faz join com `ad_accounts(plataforma)`
  - Em cada campanha avaliada, carrega o servico correto e chama `update_campaign_status`/`update_campaign_budget` da plataforma dela
  - Resposta inclui `plataforma` em cada acao aplicada

  **Backend — tasks.py:**
  - Refatorado para helper `_run_sync_for_platform(plataforma, account_id)`
  - Novas tasks: `sync_google_campaigns_task`, `sync_tiktok_campaigns_task`, `sync_all_ads_task` (executa as 3)
  - `sync_meta_campaigns_task` mantida por compatibilidade

  **Backend — core/tasks.py:**
  - Beat schedule: `sync-google-campaigns-daily` (24h), `sync-tiktok-campaigns-daily` (24h) alem do Meta existente

  **Backend — core/middleware.py:**
  - Audit log: `POST /ads/oauth` → `ads_oauth_callback`; `POST /ads/accounts` → `ads_sync_account` (sync manual)

  **Backend — main.py:** versao bump para 0.7.0

  **Frontend — Ads.jsx:**
  - Novo state `plataforma` (filtro) + componente `PlatformBadge` (cores por plataforma)
  - Toggle de plataforma no header (Todas / Meta / Google / TikTok) que filtra campanhas e metricas
  - Nova aba "Comparativo" com componente `CrossPlatformTab`: 3 cards lado a lado com metricas por plataforma + barras horizontais comparativas de gasto
  - Tabela de campanhas ganhou coluna "Plataforma" com badge
  - AccountsTab: 3 botoes coloridos "Conectar Meta/Google/TikTok" que disparam fluxo OAuth via `/ads/oauth/{plat}/url`. Mantem fallback manual com seletor de plataforma no modal (external_id placeholder muda por plataforma)

  **Frontend — AdsOAuthCallback.jsx (novo):**
  - Pagina de callback em `/ads/oauth/:plataforma/callback`
  - Le `code` da URL, solicita external_id do usuario (exceto TikTok, que vem no payload), faz POST em `/ads/oauth/{plat}/callback` e redireciona para `/ads`

  **Frontend — App.jsx:**
  - Rota nova: `ads/oauth/:plataforma/callback` → AdsOAuthCallback

- **Decisoes tomadas:**
  - Dispatcher por plataforma em 3 camadas (router, rules_engine, tasks) em vez de herdar/abstrair classes — pragmatico dado 3 APIs heterogeneas
  - Google Ads: versionamento da API em settings (default v17) para facilitar upgrade
  - Google Ads `update_campaign_budget` documentado como stub — a mutacao real requer alterar o `campaign_budget` vinculado, nao a campaign em si (a ser refinado quando houver conta de teste)
  - TikTok `budget` e enviado em unidades (nao centavos) — conversao feita no servico
  - CrossPlatform endpoint nao suporta filtros alem do periodo para manter analise comparativa limpa
  - Campaign list usa `ad_accounts!inner` no select para permitir filtro por plataforma na coluna do relacionamento
  - OAuth callback precisa external_id para Meta/Google (o OAuth nao retorna a conta escolhida); para TikTok e extraido do payload (advertiser_ids)
  - Versao da API 0.6.0 → 0.7.0 marca a extensao do Ads Manager para 3 plataformas

- **Arquivos criados/modificados:**
  ```
  Criados:
  - backend/modules/ads_manager/services/google_ads.py
  - backend/modules/ads_manager/services/tiktok_ads.py
  - frontend/src/pages/AdsOAuthCallback.jsx

  Modificados:
  - backend/core/config.py (settings google_ads_*, tiktok_ads_*)
  - backend/core/tasks.py (beat schedule google/tiktok)
  - backend/core/middleware.py (audit ads_oauth_callback, ads_sync_account)
  - backend/main.py (versao 0.7.0)
  - backend/modules/ads_manager/router.py (dispatcher multi-plataforma, OAuth generico, cross-platform)
  - backend/modules/ads_manager/tasks.py (sync_google/tiktok/all)
  - backend/modules/ads_manager/services/rules_engine.py (roteamento por plataforma)
  - frontend/src/App.jsx (rota ads/oauth/:plataforma/callback)
  - frontend/src/pages/Ads.jsx (filtro plataforma, CrossPlatformTab, 3 botoes OAuth, PlatformBadge)
  ```

- **Pendencias:**
  - Cadastrar app Google Cloud + habilitar Google Ads API + gerar developer_token (basic access) e configurar OAuth consent screen
  - Cadastrar app TikTok for Business Developers (business-api) + submeter a review para scopes de leitura/escrita
  - Configurar credenciais em .env (GOOGLE_ADS_*, TIKTOK_ADS_*)
  - Refinar `google_ads.update_campaign_budget` para mutar `campaign_budget` resource (requer query prévia do budget_id vinculado)
  - Testar refresh_token do Google Ads em producao (48h sem uso pode invalidar refresh_tokens de apps em testing)
  - Testar OAuth callback flow end-to-end para cada plataforma
  - Validar conversao de micros → centavos no Google com moedas diferentes de BRL
  - Validar TikTok report endpoint com filtros corretos de campaign_ids (formato da string JSON pode variar por versao)
  - Validar audit_log com eventos novos (ads_oauth_callback)
  - Validar beat schedule rodando sync diario para google e tiktok
  - Atualizar frontend Ads.jsx subtitle mencionando 3 plataformas (feito) + testar UI com dados reais

- **Proxima sessao:** Sessao 10 — Benchmark

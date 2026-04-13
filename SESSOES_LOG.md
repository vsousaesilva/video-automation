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

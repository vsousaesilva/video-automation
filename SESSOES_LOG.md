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

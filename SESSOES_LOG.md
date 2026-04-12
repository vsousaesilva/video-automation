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

## Sessao 2 — Signup, Onboarding, Billing + Renomeacao App -> Negocio
- **Status:** Pendente
- **Escopo planejado:**
  - Tabelas: plans, subscriptions, invoices, usage_metrics
  - Signup publico, forgot/reset password
  - Integracao Asaas (customer, subscription, webhooks)
  - Middleware de limites por plano
  - Renomeacao de "App" para "Negocio" (banco + API + frontend)
  - Onboarding wizard no frontend
  - Pagina de billing no frontend

# PRD — Usina do Tempo

**Plataforma SaaS de Marketing Digital com Automação por IA**

- **Versão:** 1.0 (rascunho para revisão)
- **Data:** 2026-04-12
- **Autor:** Vinícius Sousa + Claude
- **Status:** Em revisão

---

## 1. Visão do Produto

A **Usina do Tempo** é uma plataforma SaaS multi-módulo de marketing digital que automatiza a produção de conteúdo, gerenciamento de campanhas publicitárias e relacionamento com clientes. O produto unifica ferramentas que hoje exigem múltiplas assinaturas e integrações manuais, usando IA generativa como diferencial competitivo.

### 1.1 Proposta de valor

> "Uma única plataforma para produzir, publicar, anunciar e mensurar — com IA fazendo o trabalho pesado."

### 1.2 Público-alvo

- Agências de marketing digital (5-50 clientes)
- Produtores de conteúdo e influenciadores
- Pequenas e médias empresas com presença digital
- Freelancers de social media

### 1.3 Módulos planejados

| Módulo | Descrição | Prioridade |
|---|---|---|
| **Video Engine** | Produção, aprovação e publicação automatizada de vídeos (YouTube, Instagram) | Existente |
| **Content AI** | Geração de textos, legendas, roteiros e copies com IA | Alta |
| **Ads Manager** | Gerenciamento unificado de campanhas Meta Ads, Google Ads e TikTok Ads | Alta |
| **CRM** | Gestão de contatos, funil de vendas e automações de relacionamento | Média |
| **Benchmark** | Pesquisa e monitoramento de concorrentes | Média |
| **Dashboard** | Painel unificado com métricas de todos os módulos | Alta |

---

## 2. Estado Atual (Baseline)

### 2.1 Arquitetura atual

```
Frontend (React 19 + Vite 6 + Tailwind 4)
    ↓ HTTPS
Backend (FastAPI monolítico)
    ↓
Supabase (PostgreSQL + Storage + RLS)
    ↓
APIs externas (Gemini, Pexels, YouTube, Instagram, Telegram)
```

### 2.2 O que já funciona

- Autenticação JWT com roles (admin/editor/viewer)
- CRUD de workspaces, apps, usuários
- Pipeline de geração de conteúdo (Gemini) → montagem de vídeo → validação
- Aprovação por painel web e Telegram Bot
- Publicação orquestrada (YouTube + Instagram) com retry
- Banco de mídia (upload de imagens/vídeos)
- Logs de execução por etapa
- RLS no Supabase (isolamento por workspace)

### 2.3 Estrutura do backend atual

```
backend/
├── main.py
├── config.py
├── db.py
├── auth_deps.py
├── models/schemas.py
├── routers/
│   ├── auth.py, workspaces.py, users.py
│   ├── apps.py, media.py, pipeline.py
│   ├── conteudos.py, videos.py
│   ├── publish.py, approvals.py
│   └── telegram_webhook.py
├── services/
│   ├── gemini.py, tts.py, pexels.py
│   ├── video_builder.py, video_validator.py
│   ├── media_selector.py, storage.py
│   ├── publisher_youtube.py, publisher_instagram.py
│   ├── publisher_orchestrator.py
│   ├── telegram_bot.py, notifier.py
│   └── resend_service.py (placeholder)
└── migrations/ (000-008)
```

### 2.4 Limitações identificadas

| Limitação | Impacto | Sessão de resolução |
|---|---|---|
| Monolito sem separação de módulos | Dificulta crescimento | Sessão 1 |
| `asyncio.create_task` para jobs pesados | Perda de tarefas se servidor reinicia | Sessão 3 |
| Sem billing/planos | Impossível monetizar | Sessão 2 |
| Sem signup público | Onboarding 100% manual | Sessão 2 |
| Sem rate limiting | Vulnerável a abuso | Sessão 4 |
| Credenciais de API no `.env` global | Não escala para múltiplos clientes | Sessão 1 |
| Sem recuperação de senha | UX incompleto | Sessão 2 |
| CORS aberto (`allow_origins=["*"]`) | Inseguro em produção | Sessão 4 |

---

## 3. Arquitetura-Alvo

### 3.1 Visão geral

```
                    ┌──────────────────────┐
                    │   CDN (Cloudflare)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Frontend (React)   │
                    │   Static Site        │
                    └──────────┬───────────┘
                               │ HTTPS
                    ┌──────────▼───────────┐
                    │   API Gateway        │
                    │   (FastAPI)          │
                    │                     │
                    │  ┌── core/          │
                    │  │   auth, billing  │
                    │  │   config, db     │
                    │  │   middleware     │
                    │  │                 │
                    │  ├── modules/      │
                    │  │   video_engine  │
                    │  │   content_ai    │
                    │  │   ads_manager   │
                    │  │   crm           │
                    │  │   benchmark     │
                    │  │   dashboard     │
                    │  └─────────────────│
                    └──────┬────────┬────┘
                           │        │
              ┌────────────▼─┐  ┌───▼──────────┐
              │  Supabase    │  │  Redis       │
              │  (Postgres   │  │  (Fila +     │
              │   + Storage) │  │   Cache)     │
              └──────────────┘  └───┬──────────┘
                                    │
                            ┌───────▼──────────┐
                            │  Workers         │
                            │  (Celery)        │
                            │  - video_render  │
                            │  - publisher     │
                            │  - ads_sync      │
                            │  - benchmark     │
                            └──────────────────┘
```

### 3.2 Estrutura de diretórios-alvo

```
usina-do-tempo/
├── backend/
│   ├── main.py                      # FastAPI app + registro de módulos
│   ├── core/                        # Compartilhado entre módulos
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── auth.py                  # Auth deps + JWT
│   │   ├── billing.py               # Middleware de planos/limites
│   │   ├── middleware.py            # Rate limit, CORS, logging
│   │   ├── permissions.py           # Roles + module access
│   │   ├── tasks.py                 # Celery app config
│   │   └── schemas.py               # Schemas compartilhados
│   │
│   ├── modules/
│   │   ├── video_engine/
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # Routers consolidados
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   │   ├── gemini.py
│   │   │   │   ├── tts.py
│   │   │   │   ├── pexels.py
│   │   │   │   ├── video_builder.py
│   │   │   │   ├── video_validator.py
│   │   │   │   ├── media_selector.py
│   │   │   │   ├── publisher_youtube.py
│   │   │   │   ├── publisher_instagram.py
│   │   │   │   ├── publisher_orchestrator.py
│   │   │   │   └── telegram_bot.py
│   │   │   └── tasks.py            # Tarefas Celery do módulo
│   │   │
│   │   ├── content_ai/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   └── tasks.py
│   │   │
│   │   ├── ads_manager/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   │   ├── meta_ads.py
│   │   │   │   ├── google_ads.py
│   │   │   │   └── tiktok_ads.py
│   │   │   └── tasks.py
│   │   │
│   │   ├── crm/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   └── tasks.py
│   │   │
│   │   ├── benchmark/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   └── tasks.py
│   │   │
│   │   └── dashboard/
│   │       ├── router.py
│   │       ├── schemas.py
│   │       └── services/
│   │
│   ├── migrations/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── lib/api.js
│   │   ├── stores/
│   │   ├── components/
│   │   │   ├── Layout.jsx           # Navegação modular
│   │   │   ├── ModuleGuard.jsx      # Verifica acesso ao módulo
│   │   │   └── shared/              # Componentes reutilizáveis
│   │   ├── pages/
│   │   │   ├── auth/                # Login, Signup, ForgotPassword
│   │   │   ├── onboarding/          # Wizard de configuração
│   │   │   ├── billing/             # Planos, checkout, faturas
│   │   │   ├── dashboard/           # Dashboard unificado
│   │   │   ├── video-engine/        # Páginas do Video Engine
│   │   │   ├── content-ai/          # Páginas do Content AI
│   │   │   ├── ads-manager/         # Páginas do Ads Manager
│   │   │   ├── crm/                 # Páginas do CRM
│   │   │   ├── benchmark/           # Páginas do Benchmark
│   │   │   └── settings/            # Configurações
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── render.yaml
├── PRD_USINA_DO_TEMPO.md
└── README.md
```

### 3.3 Princípios arquiteturais

1. **Monolito modular** — Deploy único, mas módulos com fronteiras claras. Cada módulo tem seus próprios routers, schemas, services e tasks. Sem dependências cruzadas entre módulos (comunicação apenas via `core/`).

2. **Módulos como feature flags** — Acesso a módulos controlado pelo plano do workspace. O middleware `billing.py` verifica permissão antes de cada request.

3. **Processamento assíncrono via fila** — Jobs pesados (render de vídeo, sync de campanhas, scraping de benchmark) vão para Redis/Celery. A API responde imediatamente.

4. **Credenciais por workspace** — Cada cliente configura suas próprias chaves de API. Sem fallback para `.env` global em produção.

5. **Banco compartilhado com isolamento** — Todas as tabelas usam `workspace_id` com RLS ativo. Cada módulo adiciona suas próprias tabelas.

---

## 4. Modelo de Dados

### 4.1 Tabelas do Core (compartilhadas)

```sql
-- Já existentes (sem alterações)
-- workspaces, users, execution_logs

-- Novas tabelas do Core

CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(30) UNIQUE NOT NULL,       -- free, starter, pro, enterprise
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    modulos JSONB NOT NULL DEFAULT '[]',    -- ["video_engine", "content_ai", ...]
    max_apps INTEGER NOT NULL DEFAULT 1,
    max_users INTEGER NOT NULL DEFAULT 1,
    max_videos_mes INTEGER DEFAULT 5,
    max_conteudos_mes INTEGER DEFAULT 20,
    max_campanhas INTEGER DEFAULT 0,
    max_contatos_crm INTEGER DEFAULT 0,
    max_benchmarks_mes INTEGER DEFAULT 0,
    storage_max_gb NUMERIC(5,2) DEFAULT 1.0,
    preco_centavos INTEGER NOT NULL DEFAULT 0,
    intervalo VARCHAR(10) DEFAULT 'mensal', -- mensal, anual
    ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id),
    asaas_subscription_id TEXT,             -- ID da assinatura no Asaas
    asaas_customer_id TEXT,                 -- ID do customer no Asaas
    status VARCHAR(20) NOT NULL DEFAULT 'trial',
        -- trial, active, past_due, canceled, expired
    trial_ends_at TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    asaas_payment_id TEXT,
    valor_centavos INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending, confirmed, overdue, refunded
    url_boleto TEXT,
    url_pix TEXT,
    vencimento DATE,
    pago_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    mes_referencia DATE NOT NULL,           -- primeiro dia do mês
    videos_gerados INTEGER DEFAULT 0,
    videos_publicados INTEGER DEFAULT 0,
    conteudos_gerados INTEGER DEFAULT 0,
    campanhas_criadas INTEGER DEFAULT 0,
    contatos_crm INTEGER DEFAULT 0,
    benchmarks_executados INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    UNIQUE(workspace_id, mes_referencia)
);

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    user_id UUID,
    acao VARCHAR(50) NOT NULL,              -- login, create_app, publish_video, etc.
    recurso VARCHAR(50),                    -- app, video, campaign, etc.
    recurso_id UUID,
    detalhes JSONB,
    ip_address INET,
    user_agent TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Índices
CREATE INDEX idx_subscriptions_workspace ON subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_usage_metrics_workspace_mes ON usage_metrics(workspace_id, mes_referencia);
CREATE INDEX idx_audit_log_workspace_criado ON audit_log(workspace_id, criado_em);
CREATE INDEX idx_invoices_workspace ON invoices(workspace_id);
```

### 4.2 Alterações na tabela workspaces

```sql
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    onboarding_completed BOOLEAN DEFAULT false;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    asaas_customer_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    documento_titular VARCHAR(18);         -- CPF ou CNPJ
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    email_cobranca VARCHAR(255);
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    telefone VARCHAR(20);

-- Credenciais de APIs externas (criptografadas em repouso)
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    youtube_client_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    youtube_client_secret_enc TEXT;         -- criptografado
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    youtube_refresh_token_enc TEXT;         -- criptografado
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    meta_app_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    meta_app_secret_enc TEXT;              -- criptografado
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    meta_access_token_enc TEXT;            -- criptografado
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    meta_instagram_account_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    google_ads_customer_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    google_ads_refresh_token_enc TEXT;     -- criptografado
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    tiktok_ads_advertiser_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    tiktok_ads_access_token_enc TEXT;      -- criptografado
```

### 4.3 Tabelas por módulo

As tabelas específicas de cada módulo serão definidas na sessão de implementação correspondente. A seguir, uma visão geral:

**Content AI:**
```
content_requests    — solicitações de geração (tipo, tom, contexto)
generated_contents  — conteúdos gerados (texto, copy, legenda)
content_templates   — templates reutilizáveis
```

**Ads Manager:**
```
ad_accounts         — contas vinculadas (Meta, Google, TikTok)
campaigns           — campanhas sincronizadas
ad_sets             — conjuntos de anúncios
ads                 — anúncios individuais
ad_metrics_daily    — métricas diárias por anúncio
ad_rules            — regras de automação (pausar se CPA > X)
```

**CRM:**
```
contacts            — contatos com tags e score
deals               — oportunidades no funil
deal_stages         — etapas do funil (personalizáveis)
activities          — histórico de interações
automations         — regras de automação (se X, então Y)
```

**Benchmark:**
```
competitors         — concorrentes monitorados
benchmark_reports   — relatórios de análise
benchmark_metrics   — métricas por concorrente
benchmark_keywords  — palavras-chave rastreadas
```

---

## 5. Planos e Billing

### 5.1 Estrutura de planos

| Recurso | Free | Starter | Pro | Enterprise |
|---|---|---|---|---|
| **Preço** | Grátis | R$ 97/mês | R$ 297/mês | Sob consulta |
| **Apps/Projetos** | 1 | 3 | 10 | Ilimitado |
| **Usuários** | 1 | 2 | 5 | Ilimitado |
| **Vídeos/mês** | 5 | 30 | 150 | Ilimitado |
| **Conteúdos IA/mês** | 10 | 50 | 300 | Ilimitado |
| **Storage** | 1 GB | 5 GB | 25 GB | 100 GB |
| **Video Engine** | Sim | Sim | Sim | Sim |
| **Content AI** | Básico | Completo | Completo | Completo |
| **Ads Manager** | — | — | Sim | Sim |
| **CRM** | — | Sim (100 contatos) | Sim (5.000) | Ilimitado |
| **Benchmark** | — | — | Sim (3/mês) | Ilimitado |
| **Dashboard** | Básico | Completo | Completo | Personalizado |
| **Aprovação Telegram** | — | Sim | Sim | Sim |
| **Suporte** | Comunidade | E-mail | Prioritário | Dedicado |
| **Trial** | — | 14 dias | 14 dias | — |

### 5.2 Integração Asaas

**Fluxo de assinatura:**

```
1. Signup → cria workspace + user admin + subscription (trial/free)
2. Escolhe plano → frontend redireciona para checkout Asaas
3. Asaas processa pagamento → webhook notifica backend
4. Backend ativa subscription → libera módulos do plano
5. Renovação automática → Asaas cobra → webhook confirma
6. Inadimplência → webhook marca past_due → aviso ao cliente
7. Cancelamento → webhook marca canceled → acesso restrito ao Free
```

**Endpoints Asaas necessários:**

| Endpoint | Uso |
|---|---|
| `POST /customers` | Criar customer no signup |
| `POST /subscriptions` | Criar assinatura |
| `GET /subscriptions/{id}` | Consultar status |
| `DELETE /subscriptions/{id}` | Cancelar assinatura |
| `POST /payments` | Gerar cobrança avulsa |
| Webhook `PAYMENT_CONFIRMED` | Ativar/renovar |
| Webhook `PAYMENT_OVERDUE` | Marcar inadimplência |
| Webhook `SUBSCRIPTION_DELETED` | Cancelar acesso |

### 5.3 Middleware de limites

Toda request passa por verificação de acesso ao módulo e limites de uso:

```python
# Pseudocódigo do middleware
async def check_billing(request, workspace_id):
    subscription = get_active_subscription(workspace_id)
    plan = subscription.plan

    # 1. Verificar acesso ao módulo
    module = extract_module_from_path(request.path)
    if module not in plan.modulos:
        raise HTTPException(403, "Módulo não disponível no seu plano")

    # 2. Verificar limites (apenas em ações de criação)
    if request.method == "POST" and is_create_action(request.path):
        usage = get_current_month_usage(workspace_id)
        check_limit("videos_gerados", usage, plan.max_videos_mes)
        check_limit("conteudos_gerados", usage, plan.max_conteudos_mes)
        # ... etc

    # 3. Incrementar uso
    increment_usage(workspace_id, action_type)
```

---

## 6. Segurança, Privacidade e Performance

### 6.1 Segurança

| Camada | Medida | Sessão |
|---|---|---|
| **Autenticação** | JWT com rotação de refresh tokens | Já existe |
| **Autorização** | RBAC (admin/editor/viewer) + acesso por módulo | Sessão 1-2 |
| **Rate limiting** | Por IP + por tenant, configurável por plano | Sessão 4 |
| **CORS** | Whitelist de domínios permitidos (não `*`) | Sessão 4 |
| **Criptografia em trânsito** | HTTPS obrigatório (Render + Cloudflare) | Sessão 4 |
| **Criptografia em repouso** | Tokens de API criptografados com Fernet (AES-128) | Sessão 4 |
| **Auditoria** | Log de todas as ações sensíveis | Sessão 4 |
| **Input validation** | Pydantic em todas as rotas (já existe) | Já existe |
| **SQL injection** | Supabase client parameterizado (já existe) | Já existe |
| **XSS** | React escapa por padrão + CSP headers | Sessão 4 |
| **CSRF** | JWT em header Authorization (não cookie) | Já existe |
| **Secrets management** | Variáveis de ambiente no Render (não no código) | Já existe |
| **2FA** | TOTP para planos Pro/Enterprise | Sessão futura |
| **Brute-force** | Lockout após 5 tentativas falhas de login | Sessão 4 |

**Ponderações:**
- **Fernet para criptografia de tokens:** Simples, suficiente para o estágio. Se escalar para Enterprise com requisitos de compliance (SOC2, ISO 27001), migrar para AWS KMS ou Vault.
- **RLS do Supabase:** Boa primeira barreira, mas não substitui validação no backend. O backend usa `service_key` (bypassa RLS), então a verificação de workspace_id deve acontecer nos routers.
- **Rate limiting:** SlowAPI (baseado em Redis) é suficiente até 500 clientes. Acima disso, considerar API gateway dedicado (Kong, AWS API Gateway).

### 6.2 Privacidade (LGPD)

| Requisito | Implementação | Sessão |
|---|---|---|
| **Consentimento** | Checkbox de termos no signup | Sessão 2 |
| **Acesso aos dados** | Endpoint `GET /privacy/my-data` (exporta dados do workspace) | Sessão 4 |
| **Exclusão de dados** | Endpoint `DELETE /privacy/my-data` (anonimiza + deleta) | Sessão 4 |
| **Política de privacidade** | Página pública no frontend | Sessão 2 |
| **Termos de uso** | Página pública no frontend | Sessão 2 |
| **DPA** | Documento para clientes Enterprise | Sessão futura |
| **Retenção de dados** | Logs rotacionados (90 dias), dados de cliente retidos enquanto ativo | Sessão 4 |
| **Notificação de breach** | Procedimento documentado, não automático inicialmente | Sessão futura |

**Ponderações:**
- Para planos Enterprise com clientes do setor de saúde ou financeiro, pode ser necessário oferecer isolamento de banco (schema separado por tenant ou banco dedicado). Isso é complexo e caro — adiar para quando houver demanda real.
- O Asaas já é PCI-DSS compliant, então dados de cartão não transitam pelo backend.

### 6.3 Performance

| Aspecto | Meta | Estratégia |
|---|---|---|
| **Latência da API** | p95 < 300ms para reads, < 1s para writes | Cache Redis para dados frequentes, índices otimizados |
| **Render de vídeo** | < 5 min por vídeo | Workers Celery dedicados, fila com prioridade por plano |
| **Sync de Ads** | Diário, < 30s por conta | Worker background, batch processing |
| **Concorrência** | 500 workspaces, ~50 simultâneos | Connection pooling (pgBouncer), auto-scale Render |
| **Frontend** | LCP < 2.5s, FID < 100ms | Lazy loading de módulos, CDN, code splitting |
| **Uptime** | 99.5% (free), 99.9% (pro/enterprise) | Health checks, auto-restart, monitoramento |

**Ponderações:**
- **Render free tier:** Dorme após 15 min de inatividade (cold start ~30s). Para SaaS, migrar backend para plano pago (Render Starter: $7/mês) que mantém instância ativa.
- **Supabase connection limit:** Plano Free permite 60 conexões. Com 500 clientes, precisa do Pro (500 conexões) ou pooling via pgBouncer.
- **Redis:** Render oferece Redis nativo ($7/mês). Alternativa: Upstash (serverless, free tier generoso).
- **Celery workers:** Podem rodar como Background Workers no Render ($7/mês cada). Iniciar com 1 worker para vídeo + 1 worker geral. Escalar conforme demanda.

**Estimativa de custos de infraestrutura para 500 clientes:**

| Serviço | Plano | Custo/mês |
|---|---|---|
| Render (API) | Starter | $7 |
| Render (Worker Video) | Starter | $7 |
| Render (Worker Geral) | Starter | $7 |
| Render (Frontend) | Static (free) | $0 |
| Render (Redis) | Starter | $7 |
| Supabase | Pro | $25 |
| Cloudflare | Free | $0 |
| Sentry | Developer | $0 |
| **Total** | | **~$53/mês** |

Com 500 clientes pagantes (estimando 30% no Starter a R$97), a receita mínima seria R$14.550/mês, cobrindo infraestrutura com ampla margem.

---

## 7. Sessões de Implementação

### Princípio fundamental: Zero downtime

Todas as sessões seguem esta regra:
- O Video Engine **nunca** fica fora do ar durante as mudanças
- Cada sessão termina com o sistema funcional e testado
- Rollback é possível a qualquer momento (git revert + migration down)

---

### Sessão 1 — Modularização do Backend (sem alterar funcionalidade)

**Objetivo:** Reorganizar o código existente na estrutura modular sem quebrar nada.

**Escopo:**
1. Criar estrutura `core/` e mover `config.py`, `db.py`, `auth_deps.py`
2. Criar `modules/video_engine/` e mover routers e services existentes
3. Atualizar imports em todos os arquivos
4. Atualizar `main.py` para registrar routers do módulo
5. Manter todos os endpoints com os mesmos paths (sem breaking changes)
6. **Renomear conceito "App" para "Negócio"** — cada cliente cadastra um negócio (físico, virtual, app, loja, etc.), não apenas um aplicativo mobile. Afeta: schemas, routers, frontend, banco de dados (tabela `apps` → `negocios`), endpoints (`/apps` → `/negocios`)

**Arquivos afetados:**
- Todos os routers e services (mudança de import paths)
- `main.py` (novo registro de módulos)
- Nenhuma mudança de schema ou banco

**Testes de finalização:**
- [ ] `GET /health` retorna 200
- [ ] Login funciona
- [ ] Listar apps funciona
- [ ] Pipeline trigger funciona
- [ ] Aprovação via Telegram funciona
- [ ] Publicação YouTube/Instagram funciona
- [ ] Todos os endpoints existentes respondem nos mesmos paths
- [ ] Deploy no Render completa sem erros

**Critério de aceite:** Nenhuma mudança funcional visível para o usuário. O Video Engine continua operando normalmente.

**Estimativa:** 2-3 horas

---

### Sessão 2 — Signup, Onboarding e Billing (Asaas)

**Objetivo:** Permitir que novos clientes se cadastrem, escolham um plano e paguem.

**Escopo:**

**Backend:**
1. Migration: criar tabelas `plans`, `subscriptions`, `invoices`, `usage_metrics`
2. Seed: inserir planos (free, starter, pro, enterprise)
3. `core/billing.py` — serviço de integração Asaas (criar customer, subscription, webhooks)
4. `POST /auth/signup` — criar workspace + user + subscription trial
5. `POST /auth/forgot-password` — enviar email com token de reset
6. `POST /auth/reset-password` — redefinir senha com token
7. `GET /billing/plans` — listar planos disponíveis
8. `GET /billing/subscription` — assinatura atual do workspace
9. `POST /billing/checkout` — gerar link de checkout Asaas
10. `POST /billing/webhook` — receber eventos do Asaas
11. `GET /billing/invoices` — listar faturas
12. Middleware de verificação de módulo e limites (logging only, não bloqueia ainda)
13. Alterações na tabela `workspaces` (campos de billing)

**Frontend:**
1. Página de Signup (`/signup`) — nome, email, senha, workspace
2. Página de Forgot Password (`/forgot-password`)
3. Página de Reset Password (`/reset-password`)
4. Onboarding Wizard (3 etapas: dados do workspace → conectar integrações → criar primeiro app)
5. Página de Billing (`/settings/billing`) — plano atual, upgrade, faturas
6. Termos de uso e política de privacidade (páginas estáticas)
7. Componente `PlanBadge` (exibe plano atual no sidebar)

**Testes de finalização:**
- [ ] Signup cria workspace + user + subscription (trial 14 dias)
- [ ] Login com novo usuário funciona
- [ ] Onboarding wizard completa sem erros
- [ ] Forgot/reset password funciona via email (Resend)
- [ ] `GET /billing/plans` retorna lista de planos
- [ ] `GET /billing/subscription` retorna subscription do workspace
- [ ] Webhook do Asaas ativa subscription ao confirmar pagamento
- [ ] Video Engine continua funcionando para workspaces existentes
- [ ] Workspace existente (Usina do Tempo) recebe subscription ativa automaticamente na migration

**Critério de aceite:** Novo usuário consegue se cadastrar, ver planos, e o workspace existente não é afetado.

**Estimativa:** 6-8 horas

---

### Sessão 3 — Fila de Processamento (Redis + Celery)

**Objetivo:** Migrar jobs pesados de `asyncio.create_task` para Celery com Redis.

**Escopo:**

**Infraestrutura:**
1. Adicionar Redis ao `render.yaml`
2. Adicionar Celery worker ao `render.yaml`
3. Atualizar `requirements.txt` (celery, redis)

**Backend:**
1. `core/tasks.py` — configuração do Celery app
2. `modules/video_engine/tasks.py` — tarefas: `process_app_task`, `publish_all_platforms_task`
3. Migrar `pipeline.py` de `background_tasks.add_task` para `task.delay()`
4. Migrar `telegram_webhook.py` de `asyncio.create_task` para `task.delay()`
5. Adicionar retry automático com backoff exponencial
6. Dashboard de status das tarefas (Flower ou endpoint customizado)

**Mudança de fluxo:**

```
ANTES:
  POST /pipeline/trigger → background_tasks.add_task(process) → (se crash, perde)

DEPOIS:
  POST /pipeline/trigger → celery_task.delay() → Redis → Worker processa → (se crash, retry)
```

**Testes de finalização:**
- [ ] Redis está acessível
- [ ] Celery worker inicia e consome tarefas
- [ ] Pipeline trigger enfileira tarefa corretamente
- [ ] Worker processa vídeo e salva resultado no banco
- [ ] Aprovação via Telegram enfileira publicação
- [ ] Retry funciona após falha (simular timeout)
- [ ] `GET /tasks/status/{task_id}` retorna status da tarefa
- [ ] Sistema sobrevive a restart do worker sem perder tarefas

**Critério de aceite:** Jobs pesados executam via Celery. Se o worker reinicia, tarefas pendentes são reprocessadas.

**Estimativa:** 4-6 horas

---

### Sessão 4 — Segurança, Auditoria e Hardening

**Objetivo:** Proteger o sistema para operação multi-tenant em produção.

**Escopo:**

**Backend:**
1. **Rate limiting** — SlowAPI (por IP + por workspace)
   - Login: 5 req/min por IP
   - API geral: 60 req/min por workspace
   - Upload: 10 req/min por workspace
2. **CORS restritivo** — whitelist de domínios do frontend
3. **Brute-force protection** — lockout após 5 falhas de login (15 min)
4. **Criptografia de credenciais** — Fernet para tokens de APIs externas no banco
5. **Audit log** — middleware que registra ações sensíveis
6. **CSP headers** — Content-Security-Policy no frontend
7. **LGPD endpoints**:
   - `GET /privacy/my-data` — exporta todos os dados do workspace em JSON
   - `DELETE /privacy/my-data` — solicita exclusão (marca para processamento)
8. **Rotação de logs** — cron job para limpar `execution_logs` > 90 dias
9. **Billing enforcement** — middleware bloqueia ações quando limite atingido (antes era log only)
10. **Verificação de email** — enviar código de verificação no signup

**Frontend:**
1. Página de Termos de Uso (`/termos`)
2. Página de Política de Privacidade (`/privacidade`)
3. Exibir aviso quando próximo do limite do plano
4. Exibir banner quando plano expirado/inadimplente

**Testes de finalização:**
- [ ] Rate limiting bloqueia após exceder limite (retorna 429)
- [ ] Login com senha errada 5x bloqueia por 15 min
- [ ] CORS rejeita requisições de domínios não autorizados
- [ ] Credenciais de API são armazenadas criptografadas no banco
- [ ] Audit log registra login, criação de app, publicação
- [ ] Endpoint de exportação de dados retorna JSON completo
- [ ] Middleware de billing bloqueia criação de vídeo quando limite atingido
- [ ] Video Engine continua funcionando normalmente

**Critério de aceite:** Sistema seguro para multi-tenant. Nenhuma vulnerabilidade OWASP Top 10.

**Estimativa:** 5-7 horas

---

### Sessão 5 — Dashboard Unificado

**Objetivo:** Criar painel central com métricas de todos os módulos.

**Escopo:**

**Backend:**
1. `modules/dashboard/router.py` — endpoints de agregação
   - `GET /dashboard/overview` — KPIs gerais do workspace
   - `GET /dashboard/video-engine` — métricas de vídeos (gerados, publicados, taxa de aprovação)
   - `GET /dashboard/usage` — consumo vs. limites do plano
   - `GET /dashboard/timeline` — atividade recente cross-módulo
2. `modules/dashboard/services/aggregator.py` — queries otimizadas com cache Redis

**Frontend:**
1. Página Dashboard com cards de KPIs
2. Gráficos de evolução (chart.js ou recharts)
3. Timeline de atividade recente
4. Widget de uso do plano (barra de progresso)
5. Atalhos rápidos para ações frequentes

**Testes de finalização:**
- [ ] Dashboard carrega em < 2s
- [ ] KPIs refletem dados reais do workspace
- [ ] Timeline mostra últimas ações (vídeos, publicações)
- [ ] Widget de uso mostra consumo correto vs. limite do plano
- [ ] Dashboard funciona para plano Free (dados limitados)

**Critério de aceite:** Dashboard exibe métricas do Video Engine. Preparado para receber dados de módulos futuros.

**Estimativa:** 4-5 horas

---

### Sessão 6 — Content AI

**Objetivo:** Módulo de geração de conteúdo com IA para múltiplos formatos.

**Escopo:**

**Backend:**
1. Migration: tabelas `content_requests`, `generated_contents`, `content_templates`
2. `modules/content_ai/router.py`:
   - `POST /content-ai/generate` — gerar conteúdo (copy, legenda, roteiro, artigo)
   - `GET /content-ai/history` — histórico de gerações
   - `GET /content-ai/templates` — templates disponíveis
   - `POST /content-ai/templates` — salvar template customizado
3. `modules/content_ai/services/generator.py` — integração Gemini com prompts especializados
4. Tipos de conteúdo:
   - Copy para anúncios (Meta, Google, TikTok)
   - Legendas para redes sociais
   - Roteiros de vídeo (integra com Video Engine)
   - Artigos para blog
   - Respostas para comentários
   - E-mails de marketing
5. Tarefa Celery para gerações em batch

**Frontend:**
1. Página Content AI com formulário de geração
2. Seletor de tipo de conteúdo e tom de voz
3. Pré-visualização com opção de editar
4. Botão "Usar no Video Engine" (cria conteúdo no pipeline)
5. Biblioteca de conteúdos gerados com filtros
6. Gerenciador de templates

**Testes de finalização:**
- [ ] Gerar copy para Meta Ads retorna texto adequado
- [ ] Gerar legenda para Instagram retorna com hashtags
- [ ] Histórico lista gerações anteriores
- [ ] Template customizado é salvo e pode ser reutilizado
- [ ] Limite de gerações/mês é respeitado pelo billing
- [ ] Integração com Video Engine funciona (gerar roteiro → criar vídeo)

**Critério de aceite:** Usuário consegue gerar conteúdo de múltiplos tipos com IA e reutilizar nos outros módulos.

**Estimativa:** 5-7 horas

---

### Sessão 7 — CRM

**Objetivo:** Módulo de gestão de contatos e funil de vendas.

**Escopo:**

**Backend:**
1. Migration: tabelas `contacts`, `deals`, `deal_stages`, `activities`, `contact_tags`
2. `modules/crm/router.py`:
   - CRUD de contatos (com importação CSV)
   - CRUD de deals (oportunidades)
   - Kanban de funil (mover entre etapas)
   - Timeline de atividades por contato
   - Tags e segmentação
3. `modules/crm/services/importer.py` — importação de contatos via CSV/Excel

**Frontend:**
1. Página de Contatos (lista, busca, filtros, tags)
2. Detalhe do contato (dados + timeline de atividades)
3. Página de Funil (kanban drag-and-drop)
4. Importação de contatos (upload CSV)
5. Modal de nova atividade (nota, email, ligação)

**Testes de finalização:**
- [ ] CRUD de contatos funciona (criar, editar, listar, buscar)
- [ ] Importação CSV cria contatos corretamente
- [ ] Funil kanban permite arrastar deals entre etapas
- [ ] Timeline de atividades mostra histórico do contato
- [ ] Limite de contatos por plano é respeitado
- [ ] RLS isola contatos entre workspaces

**Critério de aceite:** Usuário consegue gerenciar contatos e funil de vendas completo.

**Estimativa:** 6-8 horas

---

### Sessão 8 — Ads Manager (Meta Ads)

**Objetivo:** Integrar gerenciamento de campanhas Meta Ads (Facebook + Instagram Ads).

**Escopo:**

**Backend:**
1. Migration: tabelas `ad_accounts`, `campaigns`, `ad_sets`, `ads`, `ad_metrics_daily`, `ad_rules`
2. `modules/ads_manager/router.py`:
   - `POST /ads/accounts/connect` — vincular conta Meta Ads via OAuth
   - `GET /ads/campaigns` — listar campanhas (sync do Meta)
   - `POST /ads/campaigns/{id}/pause` — pausar campanha
   - `GET /ads/metrics` — métricas agregadas
   - `POST /ads/rules` — criar regra de automação
3. `modules/ads_manager/services/meta_ads.py`:
   - Sync diário de campanhas via Meta Marketing API
   - Leitura de métricas (impressões, cliques, CPA, ROAS)
   - Ações: pausar, ativar, ajustar orçamento
4. Tarefa Celery: `sync_meta_campaigns` (diário)

**Frontend:**
1. Página de contas vinculadas (Meta, Google, TikTok — Meta primeiro)
2. Lista de campanhas com métricas em cards
3. Gráficos de performance (CPA, ROAS, impressões)
4. Regras de automação (UI simples: "Se CPA > X, pausar")
5. Integração: botão "Criar copy com IA" → Content AI

**Testes de finalização:**
- [ ] OAuth do Meta conecta conta de anúncios
- [ ] Sync traz campanhas do Meta Ads
- [ ] Métricas de campanhas são exibidas corretamente
- [ ] Pausar/ativar campanha reflete no Meta
- [ ] Regra de automação é salva e executada pelo worker
- [ ] Módulo acessível apenas para planos Pro/Enterprise

**Critério de aceite:** Usuário visualiza e gerencia campanhas Meta Ads sem sair da plataforma.

**Estimativa:** 8-10 horas

---

### Sessão 9 — Ads Manager (Google Ads + TikTok Ads)

**Objetivo:** Expandir o Ads Manager para Google Ads e TikTok Ads.

**Escopo:**

**Backend:**
1. `modules/ads_manager/services/google_ads.py`:
   - OAuth com Google Ads API
   - Sync de campanhas e métricas
   - Ações: pausar, ativar, ajustar orçamento
2. `modules/ads_manager/services/tiktok_ads.py`:
   - Autenticação TikTok Marketing API
   - Sync de campanhas
   - Leitura de métricas
3. Unificar visualização cross-platform (Meta + Google + TikTok em uma única tela)
4. Tarefas Celery: `sync_google_campaigns`, `sync_tiktok_campaigns`

**Frontend:**
1. Seletor de plataforma na tela de campanhas
2. Visão unificada (todas as plataformas lado a lado)
3. Comparativo de métricas cross-platform

**Testes de finalização:**
- [ ] OAuth do Google Ads funciona
- [ ] OAuth do TikTok Ads funciona
- [ ] Sync traz campanhas de todas as plataformas
- [ ] Visão unificada exibe campanhas de múltiplas plataformas
- [ ] Ações (pausar/ativar) funcionam em cada plataforma

**Critério de aceite:** Gestão unificada de anúncios em Meta, Google e TikTok.

**Estimativa:** 6-8 horas

---

### Sessão 10 — Benchmark

**Objetivo:** Módulo de pesquisa e monitoramento de concorrentes.

**Escopo:**

**Backend:**
1. Migration: tabelas `competitors`, `benchmark_reports`, `benchmark_metrics`, `benchmark_keywords`
2. `modules/benchmark/router.py`:
   - CRUD de concorrentes
   - `POST /benchmark/analyze` — executar análise
   - `GET /benchmark/reports` — listar relatórios
   - `GET /benchmark/reports/{id}` — detalhe do relatório
3. `modules/benchmark/services/analyzer.py`:
   - Análise de presença em redes sociais (Instagram, YouTube, TikTok)
   - Análise de palavras-chave (via Gemini)
   - Comparativo de métricas públicas
   - Geração de insights com IA
4. Tarefa Celery: `run_benchmark_analysis`

**Frontend:**
1. Página de concorrentes cadastrados
2. Formulário de análise (selecionar concorrentes + parâmetros)
3. Relatório visual com comparativos
4. Insights gerados por IA
5. Histórico de relatórios

**Testes de finalização:**
- [ ] Cadastro de concorrente funciona
- [ ] Análise executa e gera relatório
- [ ] Relatório exibe comparativos visuais
- [ ] Insights de IA são relevantes
- [ ] Limite de benchmarks/mês respeitado pelo billing
- [ ] Worker processa análise em background

**Critério de aceite:** Usuário consegue analisar concorrentes e receber insights acionáveis.

**Estimativa:** 5-7 horas

---

### Sessão 11 — Monitoramento, Observabilidade e Polimento

**Objetivo:** Garantir que o sistema é monitorável, estável e pronto para produção em escala.

**Escopo:**

**Backend:**
1. Integrar Sentry para error tracking
2. Health check detalhado (`/health/detailed` — DB, Redis, Celery, APIs)
3. Endpoint de métricas para monitoramento (`/metrics`)
4. Structured logging (JSON) com correlation IDs
5. Alertas configurados (Sentry + Render)

**Frontend:**
1. Error boundary global com report para Sentry
2. Toast notifications para erros de rede
3. Skeleton loaders em todas as páginas
4. Testes de responsividade mobile
5. Polimento visual de todas as telas

**Infraestrutura:**
1. Cloudflare DNS + CDN para frontend
2. Uptime monitoring (Render ou BetterUptime)
3. Backup verification (Supabase point-in-time recovery)
4. Documentação de runbook (procedimentos de emergência)

**Testes de finalização:**
- [ ] Sentry captura erros do backend e frontend
- [ ] Health check detalhado reporta status de cada componente
- [ ] Logs são estruturados (JSON) e pesquisáveis
- [ ] Frontend é usável em mobile
- [ ] Sistema opera por 48h sem intervenção manual
- [ ] Backup do Supabase pode ser restaurado

**Critério de aceite:** Sistema pronto para 500 clientes com monitoramento ativo.

**Estimativa:** 4-6 horas

---

## 8. Estratégia de Migração

### 8.1 Proteção do Video Engine durante a migração

```
Sessão 1: Mover código para modules/ → Video Engine roda igual, só muda endereço de import
Sessão 2: Adicionar billing → Workspace existente recebe subscription "active" na migration
Sessão 3: Migrar para Celery → Fallback para asyncio se Celery indisponível
Sessão 4: Hardening → Apenas adiciona camadas, não remove nada
Sessões 5-10: Novos módulos → Aditivos, não alteram Video Engine
```

### 8.2 Migration de dados existentes

Na Sessão 2, uma migration automática garante que:

```sql
-- Criar subscription ativa para o workspace existente
INSERT INTO subscriptions (workspace_id, plan_id, status, current_period_start, current_period_end)
SELECT
    w.id,
    (SELECT id FROM plans WHERE slug = 'pro'),
    'active',
    now(),
    now() + interval '1 year'
FROM workspaces w
WHERE NOT EXISTS (SELECT 1 FROM subscriptions s WHERE s.workspace_id = w.id);
```

O workspace "Usina do Tempo" recebe plano Pro ativo por 1 ano, sem interrupção.

### 8.3 Feature flags simplificados

Cada módulo é registrado condicionalmente no `main.py`:

```python
# main.py
from modules.video_engine.router import router as video_engine_router
app.include_router(video_engine_router)  # sempre ativo

# Novos módulos — ativados progressivamente
try:
    from modules.content_ai.router import router as content_ai_router
    app.include_router(content_ai_router)
except ImportError:
    pass  # módulo ainda não implementado
```

---

## 9. Cronograma Resumido

| Sessão | Nome | Dependência | Estimativa |
|---|---|---|---|
| 1 | Modularização do backend | — | 2-3h |
| 2 | Signup, onboarding, billing (Asaas) | Sessão 1 | 6-8h |
| 3 | Fila de processamento (Redis + Celery) | Sessão 1 | 4-6h |
| 4 | Segurança, auditoria, hardening | Sessões 2-3 | 5-7h |
| 5 | Dashboard unificado | Sessão 2 | 4-5h |
| 6 | Content AI | Sessão 4 | 5-7h |
| 7 | CRM | Sessão 4 | 6-8h |
| 8 | Ads Manager (Meta) | Sessão 4 | 8-10h |
| 9 | Ads Manager (Google + TikTok) | Sessão 8 | 6-8h |
| 10 | Benchmark | Sessão 4 | 5-7h |
| 11 | Monitoramento e polimento | Sessão 10 | 4-6h |
| **Total** | | | **55-75h** |

As Sessões 2 e 3 podem ser executadas em paralelo (sem dependência entre si). As Sessões 5-10 podem ser reordenadas conforme prioridade de negócio.

---

## 10. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Meta/Google/TikTok rejeitam review do app | Alta | Alto | Iniciar review na Sessão 4, antes de implementar. Preparar documentação e screencasts antecipadamente |
| Asaas fora do ar afeta signup | Baixa | Médio | Permitir signup com trial sem passar pelo Asaas. Sincronizar quando voltar |
| Render free tier insuficiente para 500 clientes | Média | Alto | Planejar migração para Render Pro na Sessão 3 (com workers) |
| Supabase connection exhaustion | Média | Alto | Implementar connection pooling na Sessão 3 |
| Celery/Redis adiciona complexidade operacional | Média | Médio | Flower dashboard + alertas Sentry. Documentar runbook na Sessão 11 |
| Token do Instagram expira (60 dias) | Alta | Médio | Lembrete automático no Dashboard. Implementar refresh automático quando possível |
| LGPD: cliente solicita exclusão de dados | Baixa | Médio | Endpoint automatizado na Sessão 4. Testar com dados reais |

---

## 11. Métricas de Sucesso (pós-lançamento)

| Métrica | Meta 3 meses | Meta 6 meses | Meta 12 meses |
|---|---|---|---|
| Workspaces ativos | 50 | 200 | 500 |
| MRR (Monthly Recurring Revenue) | R$ 5.000 | R$ 20.000 | R$ 50.000 |
| Churn mensal | < 10% | < 7% | < 5% |
| NPS | > 30 | > 40 | > 50 |
| Uptime | 99% | 99.5% | 99.9% |
| Tempo médio de onboarding | < 10 min | < 7 min | < 5 min |
| Tickets de suporte/cliente/mês | < 2 | < 1.5 | < 1 |

---

## 12. Decisões em aberto (para revisão)

1. ~~**Domínio definitivo:**~~ **DEFINIDO** → `app.usinadotempo.com.br` (aplicação SaaS). API em `api.usinadotempo.com.br`.
2. **Landing page:** Construir em `usinadotempo.com.br` (sem o `app.`) — mesmo frontend ou plataforma separada (Framer, Webflow)?
3. **Suporte ao cliente:** Chat in-app (Intercom/Crisp) ou apenas email?
4. **App mobile:** PWA é suficiente ou precisa de app nativo?
5. **Idiomas:** Apenas pt-BR ou suporte a outros idiomas desde o início?
6. **White-label:** Permitir que agências usem a plataforma com marca própria?
7. **API pública:** Oferecer API para integrações de terceiros no plano Enterprise?
8. **Marketplace:** Permitir que terceiros criem templates/integrações?

---

---

## 13. Terminologia — "App" → "Negócio"

A plataforma originalmente foi pensada para marketing de aplicativos mobile. Com a expansão para SaaS multi-segmento, o conceito de "App" é renomeado para **"Negócio"**, pois cada cliente pode cadastrar qualquer tipo de empreendimento:

- Aplicativo mobile
- E-commerce / loja virtual
- Negócio físico (restaurante, clínica, academia)
- Serviço profissional (consultoria, advocacia)
- Marca pessoal / influenciador
- Produto digital (curso, ebook)

### Impacto no código

| Antes | Depois | Onde |
|---|---|---|
| tabela `apps` | tabela `negocios` | Banco de dados |
| `app_id` (FK) | `negocio_id` (FK) | Todas as tabelas que referenciam |
| `/apps` | `/negocios` | Endpoints da API |
| `AppCreate`, `AppResponse` | `NegocioCreate`, `NegocioResponse` | Schemas |
| Página "Apps" / "Aplicativos" | Página "Negócios" | Frontend |
| `app.nome`, `app.categoria` | `negocio.nome`, `negocio.categoria` | Código backend |

### Estratégia de migração

A renomeação será feita na **Sessão 2** (junto com signup/onboarding), pois:
1. A Sessão 2 já altera banco e frontend significativamente
2. Novos clientes via signup já verão "Negócio" desde o início
3. Evita fazer duas ondas de breaking changes

**Migration SQL:**
```sql
ALTER TABLE apps RENAME TO negocios;
ALTER TABLE negocios RENAME COLUMN workspace_id TO workspace_id; -- mantém
-- Atualizar FKs em todas as tabelas
ALTER TABLE conteudos RENAME COLUMN app_id TO negocio_id;
ALTER TABLE videos RENAME COLUMN app_id TO negocio_id;
ALTER TABLE media_assets RENAME COLUMN app_id TO negocio_id;
ALTER TABLE execution_logs RENAME COLUMN app_id TO negocio_id;
-- Renomear índices e constraints correspondentes
```

---

## 14. Protocolo de Sessões — Continuidade entre Contextos

Cada sessão de implementação será executada em uma **janela de contexto independente**. Para garantir coerência:

### Ao iniciar uma nova sessão

O usuário deve colar o seguinte na nova conversa:

```
Estou trabalhando no projeto Usina do Tempo. Leia os seguintes arquivos para contexto:

1. PRD completo: video-automation/PRD_USINA_DO_TEMPO.md
2. Histórico de sessões: video-automation/SESSOES_LOG.md
3. Estrutura atual do backend: listar backend/core/, backend/modules/, backend/routers/

Sessão atual: [NÚMERO DA SESSÃO]
```

### Ao finalizar uma sessão

O desenvolvedor (Claude) deve:
1. Atualizar `SESSOES_LOG.md` com o resumo da sessão concluída
2. Listar o que foi feito, o que mudou e qualquer decisão tomada
3. Registrar pendências ou problemas encontrados
4. Commitar tudo com mensagem descritiva

### Formato do SESSOES_LOG.md

```markdown
# Sessões de Implementação — Usina do Tempo

## Sessão 1 — Modularização do Backend
- **Data:** 2026-04-12
- **Status:** Concluída
- **O que foi feito:**
  - Criada estrutura core/ (config, db, auth, schemas)
  - Criada estrutura modules/video_engine/ (routers, services, schemas)
  - Backward-compatibility wrappers nos arquivos antigos
  - main.py atualizado para nova estrutura
- **Decisões tomadas:**
  - Core routers (auth, workspaces, users) ficam em routers/
  - Video engine routers e services movidos para modules/video_engine/
  - Wrappers de re-export mantidos para compatibilidade
- **Pendências:**
  - Renomeação App → Negócio (planejada para Sessão 2)
  - Testes de deploy no Render pendentes
- **Próxima sessão:** Sessão 2 — Signup, Onboarding e Billing

## Sessão 2 — (pendente)
...
```

---

*Este documento é um rascunho para revisão. Após alinhamento, as decisões em aberto serão resolvidas e o documento será versionado como PRD v1.0 final.*

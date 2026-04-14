# Análise de Segurança, Bugs e Riscos em Escala — Usina do Tempo

> Documento de referência gerado em 2026-04-13 a partir de revisão do backend FastAPI e frontend React.
> Use como checklist vivo: marque itens resolvidos e registre a data de mitigação.

---

## 🔴 Vulnerabilidades e problemas críticos

### 1. `secret_key` com default inseguro
- **Arquivo:** [backend/core/config.py:61](backend/core/config.py#L61)
- **Problema:** default `"insecure-dev-key-change-me"`. Se a env não for carregada em prod, JWTs ficam forjáveis.
- **Mitigação:** validar em `get_settings()` que, quando `environment == "production"`, `secret_key` tem ≥32 chars e não é o default — abortar startup caso contrário.

### 2. Webhook do Asaas sem token obrigatório
- **Arquivo:** [backend/routers/billing.py:163](backend/routers/billing.py#L163)
- **Problema:** se `asaas_webhook_token` estiver vazio, a validação é pulada — qualquer um pode ativar assinaturas.
- **Mitigação:** recusar webhook quando o token de config estiver vazio em produção.

### 3. Webhook de billing cria `invoices` duplicadas
- **Arquivo:** [backend/routers/billing.py:196](backend/routers/billing.py#L196)
- **Problema:** `insert` sem checar `asaas_payment_id` existente. Asaas reentrega webhooks → invoices duplicadas, receita e uso contados em dobro.
- **Mitigação:** upsert por `asaas_payment_id` (unique index).

### 4. Endpoint `/debug/my-context` exposto em prod
- **Arquivo:** [backend/main.py:127](backend/main.py#L127)
- **Problema:** expõe estrutura interna do workspace a qualquer usuário autenticado.
- **Mitigação:** restringir a `require_role(["admin"])` ou gatear por `environment != "production"`.

### 5. JWT decodificado 3× por request sem cache
- **Arquivos:** [middleware.py:127](backend/core/middleware.py#L127), [middleware.py:209](backend/core/middleware.py#L209), [rate_limit.py:30](backend/core/rate_limit.py#L30)
- **Problema:** cada request paga 3× HMAC verify + `get_current_user` ainda consulta Supabase.
- **Mitigação:** decodificar uma vez em `CorrelationIdMiddleware` e salvar em `request.state.claims`.

### 6. BillingEnforcement faz 2 queries Supabase por request
- **Arquivo:** [backend/core/middleware.py:222-252](backend/core/middleware.py#L222-L252)
- **Problema:** rotas caras (`/pipeline/trigger`, `/content-ai/generate`) round-trip ao Supabase sem cache.
- **Mitigação:** cache em Redis com TTL 30–60s por workspace para subscription + plano.

### 7. AuditLogMiddleware escreve síncrono no Supabase
- **Arquivo:** [backend/core/middleware.py:153](backend/core/middleware.py#L153)
- **Problema:** bloqueia a thread; acopla latência do request à saúde do Supabase.
- **Mitigação:** usar Celery (já instalado) ou `BackgroundTasks` do FastAPI.

### 8. Rate limiter por `workspace_id` sem fallback seguro
- **Arquivo:** [backend/core/rate_limit.py:37](backend/core/rate_limit.py#L37)
- **Problema:** um workspace com 100 usuários legítimos compartilha 60 req/min; atacante com token expirado cai no IP.
- **Mitigação:** limites separados por par (workspace, user).

### 9. Login lockout habilita DoS contra contas-alvo
- **Arquivo:** [backend/core/rate_limit.py:102](backend/core/rate_limit.py#L102)
- **Problema:** 5 tentativas de qualquer IP bloqueiam a vítima — atacante pode travar contas em massa.
- **Mitigação:** lockout pelo par (user + IP) ou backoff exponencial; manter rate-limit por IP separado.

### 10. `accept-invite` não revalida `ativo`
- **Arquivo:** [backend/routers/auth.py:108](backend/routers/auth.py#L108)
- **Problema:** usuário removido/desativado após o envio ainda pode aceitar o convite.
- **Mitigação:** checar `user["ativo"]` antes de gravar senha.

### 11. Signup sem validação de força de senha no backend
- **Arquivo:** `backend/core/schemas.py` (validar)
- **Problema:** se não houver validator Pydantic, senhas fracas (`"123456"`) passam.
- **Mitigação:** validator mínimo (≥10 chars, classes de caracteres) + zxcvbn.

### 12. CSP permite `unsafe-inline` e `unsafe-eval`
- **Arquivo:** [backend/core/middleware.py:36](backend/core/middleware.py#L36)
- **Problema:** neutraliza boa parte da proteção contra XSS. Necessário hoje por causa do script inline de tema em `index.html`.
- **Mitigação:** mover script de tema para arquivo externo + usar nonce/hash por request.

### 13. CORS de dev pode vazar para prod
- **Arquivo:** [backend/main.py:76](backend/main.py#L76)
- **Problema:** `settings.frontend_url` é incluído incondicionalmente — se mal configurado em prod, adiciona origem extra.
- **Mitigação:** gatear inclusão por `environment != "production"`.

### 14. Telegram webhook registrado no lifespan com race em multi-réplica
- **Arquivo:** [backend/main.py:51](backend/main.py#L51)
- **Problema:** 2+ réplicas disputam o `setWebhook` a cada boot.
- **Mitigação:** lock distribuído em Redis ou mover para job dedicado (CLI / one-shot).

### 15. Lifespan faz `except Exception` e loga apenas como warning
- **Arquivo:** [backend/main.py:53](backend/main.py#L53)
- **Problema:** mascara falhas graves de inicialização.
- **Mitigação:** logar ERROR + enviar a Sentry; considerar falhar o boot em prod.

### 16. Signup sem transação
- **Arquivo:** [backend/routers/auth.py:137](backend/routers/auth.py#L137)
- **Problema:** 4 operações Supabase consecutivas; falha no meio deixa workspace/user/subscription órfãos.
- **Mitigação:** stored procedure / RPC Supabase envolvendo as 4 escritas.

### 17. Envio de email (Resend) bloqueia o request
- **Arquivo:** [backend/routers/auth.py:184](backend/routers/auth.py#L184)
- **Problema:** signup/forgot-password ficam pendurados se Resend lentificar.
- **Mitigação:** Celery task com retry exponencial.

### 18. Crisp carregado em runtime sem CSP adequada
- **Arquivo:** [frontend/index.html:36](frontend/index.html#L36)
- **Problema:** `script-src` precisa incluir `https://client.crisp.chat` quando CRISP_WEBSITE_ID é injetado.
- **Mitigação:** revisar CSP no backend para permitir o domínio.

### 19. Service worker em `public/sw.js`
- **Arquivo:** [frontend/public/sw.js](frontend/public/sw.js)
- **Problema:** SW mal configurado pode servir versão obsoleta indefinidamente.
- **Mitigação:** estratégia `network-first` para `index.html`; versionar cache (`caches.open('usina-v{N}')`).

### 20. Storage sem auditoria (URLs públicas vs assinadas)
- **Arquivo:** `backend/services/storage.py`
- **Problema:** se vídeos usam URLs públicas permanentes, qualquer pessoa com o ID vaza conteúdo.
- **Mitigação:** URLs assinadas com TTL curto (ex.: 1h) para buckets privados.

---

## 📈 Escalabilidade e operacional

- **Workers Celery de render:** MoviePy consome muita CPU/RAM. Em VPS único, 2 jobs paralelos saturam. Criar filas dedicadas (tts, render, publish) com `-Q` e worker count separado.
- **Rate limiter em memória com uvicorn multi-worker:** limites se multiplicam pelo número de workers. Redis é obrigatório em prod — alertar (não apenas logar) se fallback for acionado.
- **Cliente Supabase sem pool:** cada request abre HTTP novo. Monitorar latência p95 e considerar httpx client reutilizável.
- **Logs síncronos em JSON:** ok hoje; em alto volume considerar batching/buffering.
- **Feature flag / kill switch para IA ausente:** sem controle, workspace pode queimar cota inteira do Gemini/Pexels.
- **Rastreamento de custo por workspace ausente:** monitorar tokens Gemini consumidos por workspace para quota por plano.

---

## 🎯 Top 5 prioridades imediatas

1. **Validar `secret_key` e `asaas_webhook_token` em produção** (bloqueador — startup crash se ausentes).
2. **Corrigir duplicidade de `invoices` no webhook Asaas** (bug de receita).
3. **Deduplicar decode JWT** entre os 3 middlewares (performance).
4. **Mover envio de email e audit log para Celery** (latência + resiliência).
5. **Remover ou restringir `/debug/my-context`** (exposição).

---

## 📋 Roadmap de testes (resumo — ver conversa original para detalhes)

1. Fumaça e autenticação (health, signup, login, lockout, forgot/reset, refresh, convite, change-password)
2. RBAC e isolamento multi-tenant (cross-workspace reads, papéis, JWT adulterado, webhook Asaas token)
3. Core Video Engine (pipeline, Gemini/Pexels mock, aprovar, publicar, reprocessar, Telegram, aspect ratios)
4. Módulos complementares (Content AI, CRM, Ads Manager OAuth, Benchmark)
5. Billing e limites (limite free → 429, checkout sandbox, webhooks confirmed/overdue, reentrega sem duplicar, cancel)
6. Segurança (SlowAPI, CORS, headers, SQLi, XSS, upload malicioso, URL guess de mídia, Redis down, LGPD)
7. Escala / carga (k6/Locust em login, 50 pipelines simultâneos, Supabase exhaustion, falhas de deps externas)
8. Frontend E2E (Playwright: signup→onboarding→vídeo→aprovação; tema; mobile/PWA; i18n; toasts; sessão expirada)
9. Observabilidade (correlation id em Sentry, `/metrics` protegido, audit log completo)

---

## 📝 Registro de mitigações

| Data | Item | Responsável | Status |
|------|------|-------------|--------|
|      |      |             |        |

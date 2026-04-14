# Runbook Operacional — Usina do Tempo

Procedimentos de emergencia e verificacao para operacao da plataforma em producao.
Mantido como parte da Sessao 11 (Monitoramento e Polimento).

> Audiencia: on-call/dev responsavel por manter o servico no ar.
> Assumir: acesso a Render, Supabase, Sentry, Cloudflare e repositorio GitHub.

---

## 1. Endpoints de diagnostico

| Endpoint | Uso | Auth |
|---|---|---|
| `GET /health` | Liveness — processo responde | Publico |
| `GET /health/detailed` | DB, Redis, Celery, integracoes | Publico |
| `GET /metrics` | Contadores agregados (workspaces, videos, etc.) | Header `X-Metrics-Token` |

- `status=ok` — tudo saudavel.
- `status=degraded` — DB ok, Redis ou Celery com problema. App opera, mas filas podem estar paradas.
- `status=error` (503) — DB indisponivel. Servico nao funcional.

---

## 2. Alertas e painéis

- **Sentry** (`SENTRY_DSN` no backend, `VITE_SENTRY_DSN` no frontend) — erros 5xx e excecoes de render.
- **Render** — metrics nativas de CPU/RAM/requests; alertas por email.
- **Flower** (Celery) — `https://<host>/flower/` — saude de workers e filas.

Em uma pagina grafana/uptime externa, monitorar:
- `GET /health/detailed` a cada 60s (espera `status=ok` ou `degraded`).
- `status=error` por >2 min → paginar oncall.

---

## 3. Procedimentos de emergencia

### 3.1. Backend fora do ar (5xx generalizado)

1. Verificar Render dashboard → logs do servico `usina-backend`.
2. `GET /health/detailed` — identificar qual componente falhou.
3. Se DB: conferir status do Supabase (https://status.supabase.com).
4. Se Redis: conferir `REDIS_URL`; reiniciar o servico Redis no Render.
5. Rollback de deploy via Render → Deploys → selecionar commit anterior → "Redeploy".

### 3.2. Videos travados em "processando"

1. Flower → conferir workers ativos.
2. Se nenhum worker: reiniciar o servico `usina-worker` no Render.
3. Se Celery com task zumbi: `celery -A core.tasks purge` dentro do container.
4. Marcar videos travados como `erro`:
   ```sql
   UPDATE videos SET status='erro', erro_msg='timeout recovery'
   WHERE status='processando' AND criado_em < now() - interval '1 hour';
   ```

### 3.3. Signup/checkout falhando (Asaas)

1. `/health/detailed` → `integrations.asaas=true`.
2. Conferir status do Asaas: https://status.asaas.com.
3. Se Asaas indisponivel: flag de fallback (signup em trial sem cobranca) — documentado em Sessao 2.
4. Webhook nao recebido: reprocessar via `/billing/webhook/retry` (admin).

### 3.4. Token Instagram/Meta expirado (60 dias)

1. Usuario verá erro ao publicar.
2. Acessar `/settings` → secao Instagram → "Reconectar".
3. Para usuarios massivos afetados, logar via audit_log e enviar email em lote.

### 3.5. LGPD — solicitacao de exclusao

1. Usuario dispara `DELETE /privacy/my-data`.
2. Backend marca workspace para soft delete em 30 dias.
3. Para exclusao definitiva imediata: rodar script `backend/scripts/delete_workspace.py <workspace_id>`.

---

## 4. Deploy e rollback

- Deploys automaticos por push na branch `main`.
- Versao atual: `GET /health` → campo `version` (espelho de `app_version` em settings).
- Rollback: Render → Deploys → commit anterior → Redeploy.
- Migrations: `backend/migrations/NNN_*.sql` aplicadas manualmente via Supabase SQL Editor em ordem numerica.

---

## 5. Backup e restore (Supabase)

- Backup automatico: diario (14 dias de retencao no plano free; ajustar em producao).
- Point-in-time recovery disponivel em planos Pro.
- Restore de emergencia:
  1. Supabase Dashboard → Database → Backups → Select restore point.
  2. Confirmar em janela de mudanca para evitar downtime.
  3. Apos restore, executar `SELECT count(*) FROM workspaces` — sanity check.

---

## 6. Logs e correlation ID

- Em producao, logs backend sao JSON com `correlation_id`, `method`, `path`, `duration_ms`.
- Frontend envia header `X-Correlation-ID` em toda request (`lib/api.js`).
- Rastreio de um erro de usuario: pedir o header `X-Correlation-ID` da resposta no DevTools e buscar nos logs do Render.

---

## 7. Contatos

- Bot Telegram de emergencia: `@usinadotempo_bot` → `chat_id=5625119936`.
- Responsavel tecnico: registrar em `TEAM.md` quando houver time.

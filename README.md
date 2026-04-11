# Video Automation Platform

Plataforma de automação de vídeos para marketing de aplicativos mobile.
Gera conteúdo por IA, produz vídeos com narração (vertical + horizontal), valida com aprovação humana e publica no YouTube e Instagram.

## Arquitetura

```
pg_cron (Supabase) → POST /pipeline/trigger → Gemini (roteiro)
    → Edge TTS (narração) → FFmpeg + MoviePy (vídeo dual)
    → Aprovação (Painel Web / Telegram Bot)
    → YouTube Data API + Meta Graph API (publicação)
```

## Stack

| Camada | Tecnologia |
|---|---|
| Banco de dados | Supabase (PostgreSQL + pg_cron + Storage) |
| Backend | Python 3.11 + FastAPI |
| Frontend | React 19 + Vite + TailwindCSS v4 |
| IA | Google Gemini API |
| Narração | Edge TTS |
| Vídeo | FFmpeg + MoviePy |
| Deploy | Render.com (backend) + Render Static (frontend) |

## Setup Local

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Linux/macOS
# ou: venv\Scripts\activate  # Windows

pip install -r requirements.txt
cp ../.env.example .env
# Edite o .env com suas credenciais

uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`. O Vite faz proxy de `/api` para `localhost:8000`.

### 3. Verificar

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

Documentação da API: `http://localhost:8000/docs`

## Deploy em Produção (Render.com)

### Opção A: Deploy automático via render.yaml

1. Suba o projeto para um repositório no GitHub
2. No Render Dashboard, clique em **New → Blueprint**
3. Conecte o repositório — o Render detecta o `render.yaml`
4. Configure as variáveis de ambiente marcadas como `sync: false`
5. Deploy!

### Opção B: Deploy manual

**Backend (Web Service):**
- Runtime: Python 3
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

> **FFmpeg:** o Render inclui FFmpeg na imagem base do Python.
> Se usar Docker, o Dockerfile no diretório `backend/` já instala o FFmpeg.

**Frontend (Static Site):**
- Root Directory: `frontend`
- Build Command: `npm install && npm run build`
- Publish Directory: `dist`
- Adicione variável: `VITE_API_URL=https://SEU-BACKEND.onrender.com`
- Adicione rewrite rule: `/*` → `/index.html` (SPA)

### Variáveis de Ambiente

Veja `.env.example` para a lista completa. As obrigatórias para o pipeline funcionar:

| Variável | Obrigatória | Descrição |
|---|---|---|
| `SUPABASE_URL` | Sim | URL do projeto Supabase |
| `SUPABASE_KEY` | Sim | Anon key |
| `SUPABASE_SERVICE_KEY` | Sim | Service role key |
| `GEMINI_API_KEY` | Sim | API key do Google Gemini |
| `SECRET_KEY` | Sim | Chave JWT (gere com `openssl rand -hex 32`) |
| `BASE_URL` | Sim | URL pública do backend |
| `PEXELS_API_KEY` | Não* | Fallback de imagens (recomendado) |
| `YOUTUBE_CLIENT_ID` | Para YT | OAuth 2.0 do Google Cloud |
| `YOUTUBE_CLIENT_SECRET` | Para YT | OAuth 2.0 do Google Cloud |
| `YOUTUBE_REFRESH_TOKEN` | Para YT | Token de refresh OAuth |
| `META_ACCESS_TOKEN` | Para IG | Token de acesso Meta Graph API |
| `META_INSTAGRAM_ACCOUNT_ID` | Para IG | ID da conta Business |
| `TELEGRAM_BOT_TOKEN` | Não | Aprovação via Telegram |
| `RESEND_API_KEY` | Não | Notificações por e-mail |

## Supabase: pg_cron Escalonado

### Ativar extensões

No Supabase Dashboard → Database → Extensions → habilitar:
- `pg_cron`
- `pg_net`

### Criar o cron job

Execute no SQL Editor do Supabase:

```sql
SELECT cron.schedule(
  'pipeline-hourly-trigger',
  '0 * * * *',
  $$
  SELECT net.http_post(
    url := 'https://SEU-BACKEND.onrender.com/pipeline/trigger',
    body := json_build_object(
      'hora_atual',
      EXTRACT(HOUR FROM NOW() AT TIME ZONE 'America/Sao_Paulo')::int
    )::text,
    headers := '{"Content-Type": "application/json"}'::jsonb
  );
  $$
);
```

> Substitua a URL pelo endereço real do seu backend no Render.

Verificar cron jobs ativos:
```sql
SELECT * FROM cron.job;
```

### Purge automático do Storage (opcional)

```sql
SELECT cron.schedule(
  'storage-purge-weekly',
  '0 3 * * 0',
  $$
  UPDATE videos
  SET url_storage_vertical = NULL, url_storage_horizontal = NULL
  WHERE status = 'publicado'
    AND publicado_em < NOW() - INTERVAL '7 days'
    AND (url_storage_vertical IS NOT NULL OR url_storage_horizontal IS NOT NULL);
  $$
);
```

## Telegram Webhook

Após deploy do backend, registre o webhook:

```bash
curl "https://api.telegram.org/bot{SEU_BOT_TOKEN}/setWebhook?url=https://SEU-BACKEND.onrender.com/telegram/webhook&secret_token={SEU_WEBHOOK_SECRET}"
```

Verificar:
```bash
curl "https://api.telegram.org/bot{SEU_BOT_TOKEN}/getWebhookInfo"
```

## Teste End-to-End

```bash
cd backend
python test_e2e.py http://localhost:8000        # local
python test_e2e.py https://SEU-BACKEND.onrender.com  # produção
```

O script cria um workspace, cadastra um app, dispara o pipeline e verifica cada etapa.

## Migrações

Execute as migrações no SQL Editor do Supabase, na ordem:

```
migrations/
├── 000_reset_schema.sql
├── 001_schema_completo.sql
├── 002_dados_teste.sql
├── 003_verificacao_testes.sql
├── 004_media_bank_bucket.sql
├── 005_youtube_workspace.sql
├── 006_instagram_workspace.sql
├── 007_add_publicando_status.sql
└── 008_pg_cron_escalonado.sql
```

## Estrutura do Projeto

```
video-automation/
├── render.yaml                  # Blueprint de deploy Render
├── .env.example                 # Variáveis de ambiente
├── backend/
│   ├── main.py                  # App FastAPI + CORS + routers
│   ├── config.py                # Settings via pydantic-settings
│   ├── db.py                    # Cliente Supabase
│   ├── auth_deps.py             # JWT, bcrypt, get_current_user
│   ├── Dockerfile               # Build com FFmpeg
│   ├── requirements.txt
│   ├── routers/
│   │   ├── auth.py              # Login, refresh, logout, convites
│   │   ├── workspaces.py        # CRUD workspace
│   │   ├── users.py             # Gestão de usuários
│   │   ├── apps.py              # CRUD apps + schedule + history
│   │   ├── media.py             # Upload, listagem, seleção de mídia
│   │   ├── pipeline.py          # Trigger do pipeline (cron target)
│   │   ├── conteudos.py         # Consulta de conteúdos gerados
│   │   ├── videos.py            # Listagem de vídeos + retry
│   │   ├── approvals.py         # Aprovar, rejeitar, regenerar
│   │   ├── publish.py           # Orquestrador de publicação
│   │   └── telegram_webhook.py  # Webhook do bot Telegram
│   ├── services/
│   │   ├── gemini.py            # Motor de conteúdo (Gemini API)
│   │   ├── tts.py               # Narração (Edge TTS)
│   │   ├── media_selector.py    # Seleção hierárquica de mídia
│   │   ├── pexels.py            # Busca stock via Pexels API
│   │   ├── video_builder.py     # FFmpeg + MoviePy (dual formato)
│   │   ├── video_validator.py   # Validação automática
│   │   ├── publisher_youtube.py # YouTube Data API v3
│   │   ├── publisher_instagram.py # Meta Graph API
│   │   ├── publisher_orchestrator.py # Orquestrador multi-plataforma
│   │   ├── storage.py           # Supabase Storage helpers
│   │   ├── notifier.py          # E-mail (Resend) + Telegram
│   │   └── telegram_bot.py      # Bot Telegram (envio + botões inline)
│   ├── models/
│   │   └── schemas.py           # Schemas Pydantic
│   ├── migrations/              # SQL para Supabase
│   └── test_e2e.py              # Teste end-to-end
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx              # Rotas + proteção
        ├── lib/api.js           # Axios + interceptor JWT
        ├── stores/
        │   ├── authStore.js     # Zustand: autenticação
        │   └── dashboardStore.js # Zustand: dados do dashboard
        ├── components/
        │   ├── Layout.jsx       # Sidebar + header + badge
        │   ├── ProtectedRoute.jsx
        │   ├── PipelineTimeline.jsx
        │   ├── MediaUploader.jsx # Drag-and-drop + tags + grid
        │   └── DualVideoPreview.jsx # Player vertical + horizontal
        └── pages/
            ├── Login.jsx
            ├── Dashboard.jsx
            ├── Apps.jsx         # CRUD + formulário + banco de imagens
            ├── Approvals.jsx    # Fila de aprovação + ações
            ├── History.jsx
            ├── Settings.jsx
            └── MediaBank.jsx
```

## Operação

### Adicionar um novo app

1. Acesse o painel → Apps → Novo App
2. Preencha os dados, escolha um horário de disparo **que não conflite** com outro app
3. Faça upload de screenshots e imagens de marketing no Banco de Imagens do app
4. O cron dispara automaticamente no horário configurado

### Fluxo do pipeline

```
Hora agendada → pg_cron → POST /pipeline/trigger
  → Gemini gera roteiro + metadados
  → Edge TTS gera narração
  → Motor de mídia seleciona imagens (app → workspace → Pexels)
  → FFmpeg + MoviePy gera vídeo (vertical + horizontal)
  → Validação automática
  → Notificação: e-mail + Telegram com botões
  → Aprovação humana (painel web ou Telegram)
  → Publicação (YouTube + Instagram)
  → Notificação final com links
```

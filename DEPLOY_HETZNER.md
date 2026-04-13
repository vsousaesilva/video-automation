# Deploy Usina do Tempo — VPS Hetzner

**Documento de referencia para deploy completo em VPS Hetzner CX22**
**Data:** 2026-04-13
**Servidor:** Hetzner CX22 (2 vCPU, 4GB RAM, 40GB SSD, Ubuntu 24.04)

---

## Pre-requisitos

- [x] Servidor Hetzner criado (Ubuntu 24.04)
- [ ] IP do servidor anotado (substituir `SEU_IP` abaixo)
- [ ] Acesso SSH configurado (chave publica adicionada no Hetzner)
- [ ] DNS: acesso ao painel de DNS do dominio `usinadotempo.com.br`
- [ ] Variaveis de ambiente prontas (ver secao 7)

---

## 1. DNS — Configurar ANTES de iniciar

No painel de DNS do dominio `usinadotempo.com.br`, criar:

| Tipo | Nome | Valor | TTL |
|---|---|---|---|
| `A` | `app` | `SEU_IP` | 300 |
| `A` | `api` | `SEU_IP` | 300 |

> Fazer isso primeiro porque o Caddy precisa do DNS resolvendo para emitir o certificado SSL. A propagacao DNS pode levar ate 30 minutos.

---

## 2. Acesso inicial ao servidor

```bash
ssh root@SEU_IP
```

### 2.1 Atualizar sistema

```bash
apt update && apt upgrade -y
```

### 2.2 Criar usuario (nao usar root para os servicos)

```bash
adduser usina
# Definir senha quando solicitado

usermod -aG sudo usina

# Copiar chave SSH para o novo usuario
mkdir -p /home/usina/.ssh
cp ~/.ssh/authorized_keys /home/usina/.ssh/
chown -R usina:usina /home/usina/.ssh
chmod 700 /home/usina/.ssh
chmod 600 /home/usina/.ssh/authorized_keys
```

### 2.3 Firewall

```bash
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable
```

### 2.4 Mudar para o usuario usina

```bash
su - usina
```

> A partir daqui, todos os comandos sao executados como usuario `usina`.

---

## 3. Instalar dependencias

### 3.1 Python 3.11

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

### 3.2 FFmpeg (necessario para video rendering)

```bash
sudo apt install -y ffmpeg
```

Verificar: `ffmpeg -version`

### 3.3 Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

Verificar: `node --version && npm --version`

### 3.4 Redis

```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

Verificar: `redis-cli ping` (deve retornar `PONG`)

### 3.5 Git

```bash
sudo apt install -y git
```

### 3.6 Caddy (reverse proxy + SSL automatico)

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

Verificar: `caddy version`

---

## 4. Deploy do codigo

### 4.1 Clonar repositorio

```bash
cd /home/usina
git clone https://github.com/vsousaesilva/video-automation.git
cd video-automation
```

### 4.2 Backend — Python virtual environment

```bash
cd /home/usina/video-automation/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Se algum pacote falhar (ex: Pillow, bcrypt), instalar dependencias de build:
> ```bash
> sudo apt install -y build-essential libffi-dev libssl-dev libjpeg-dev zlib1g-dev
> ```
> E rodar `pip install -r requirements.txt` novamente.

### 4.3 Backend — Criar arquivo .env

```bash
nano /home/usina/video-automation/backend/.env
```

Colar o conteudo da secao 7 (Variaveis de ambiente) com seus valores reais.

### 4.4 Testar backend manualmente

```bash
cd /home/usina/video-automation/backend
source venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

Deve aparecer: `INFO: Uvicorn running on http://127.0.0.1:8000`

Em outro terminal SSH: `curl http://localhost:8000/health`
Deve retornar: `{"status":"ok","version":"0.3.0"}`

Parar com Ctrl+C apos confirmar.

### 4.5 Frontend — Build

```bash
cd /home/usina/video-automation/frontend

# Criar .env.production para o build
cat > .env.production << 'EOF'
VITE_API_URL=https://api.usinadotempo.com.br
EOF

npm install
npm run build
```

### 4.6 Frontend — Copiar build para diretorio do Caddy

```bash
sudo mkdir -p /var/www/usina
sudo cp -r /home/usina/video-automation/frontend/dist/* /var/www/usina/
sudo chown -R caddy:caddy /var/www/usina
```

---

## 5. Configurar servicos

### 5.1 Caddy — Reverse proxy + SSL

```bash
sudo nano /etc/caddy/Caddyfile
```

Substituir todo o conteudo por:

```
app.usinadotempo.com.br {
    root * /var/www/usina
    file_server
    try_files {path} /index.html

    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
}

api.usinadotempo.com.br {
    reverse_proxy localhost:8000
}
```

> Nota: O CORS e gerenciado pelo FastAPI (main.py), nao pelo Caddy. O Caddy apenas faz proxy.

```bash
sudo systemctl restart caddy
```

Verificar: `sudo systemctl status caddy` — deve estar `active (running)`.

Se o DNS ja estiver propagado, o Caddy obtem o certificado SSL automaticamente. Caso contrario, ele tenta novamente em alguns minutos.

### 5.2 Systemd — Backend API

```bash
sudo nano /etc/systemd/system/usina-api.service
```

```ini
[Unit]
Description=Usina do Tempo - FastAPI
After=network.target redis-server.service

[Service]
User=usina
Group=usina
WorkingDirectory=/home/usina/video-automation/backend
Environment=PATH=/home/usina/video-automation/backend/venv/bin:/usr/bin:/bin
EnvironmentFile=/home/usina/video-automation/backend/.env
ExecStart=/home/usina/video-automation/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5.3 Systemd — Celery Worker

```bash
sudo nano /etc/systemd/system/usina-celery.service
```

```ini
[Unit]
Description=Usina do Tempo - Celery Worker
After=network.target redis-server.service

[Service]
User=usina
Group=usina
WorkingDirectory=/home/usina/video-automation/backend
Environment=PATH=/home/usina/video-automation/backend/venv/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/usina/video-automation/backend
EnvironmentFile=/home/usina/video-automation/backend/.env
ExecStart=/home/usina/video-automation/backend/venv/bin/celery -A core.tasks.celery_app worker --loglevel=info --queues=video,default --concurrency=2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5.4 Systemd — Celery Beat (agendador)

```bash
sudo nano /etc/systemd/system/usina-beat.service
```

```ini
[Unit]
Description=Usina do Tempo - Celery Beat
After=network.target redis-server.service

[Service]
User=usina
Group=usina
WorkingDirectory=/home/usina/video-automation/backend
Environment=PATH=/home/usina/video-automation/backend/venv/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/usina/video-automation/backend
EnvironmentFile=/home/usina/video-automation/backend/.env
ExecStart=/home/usina/video-automation/backend/venv/bin/celery -A core.tasks.celery_app beat --loglevel=info
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5.5 Ativar e iniciar todos os servicos

```bash
sudo systemctl daemon-reload
sudo systemctl enable usina-api usina-celery usina-beat
sudo systemctl start usina-api usina-celery usina-beat
```

### 5.6 Verificar status

```bash
sudo systemctl status usina-api
sudo systemctl status usina-celery
sudo systemctl status usina-beat
sudo systemctl status caddy
sudo systemctl status redis-server
```

Todos devem estar `active (running)`.

---

## 6. Script de deploy

Para deploys futuros (apos push no GitHub):

```bash
nano /home/usina/deploy.sh
```

```bash
#!/bin/bash
set -e

echo "=== Deploy Usina do Tempo ==="
echo "$(date)"

cd /home/usina/video-automation
echo "[1/5] Git pull..."
git pull origin main

echo "[2/5] Backend: instalando dependencias..."
cd backend
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "[3/5] Frontend: build..."
cd ../frontend
npm install --silent
npm run build
sudo cp -r dist/* /var/www/usina/
sudo chown -R caddy:caddy /var/www/usina

echo "[4/5] Reiniciando servicos..."
echo "[5/5] Health check sera executado apos restart."
echo ""
echo "=== Deploy concluido! ==="

# Restart em background com delay para a resposta HTTP terminar
nohup bash -c "sleep 2 && sudo systemctl restart usina-api usina-celery usina-beat" > /dev/null 2>&1 &
```

```bash
chmod +x /home/usina/deploy.sh
```

> O script tambem pode ser executado pelo botao "Iniciar Deploy" em **Configuracoes > Admin** na propria aplicacao (apenas usuarios admin).

Uso via SSH: `ssh usina@SEU_IP './deploy.sh'`

### 6.1 Sudoers — permitir deploy sem senha

O usuario `usina` precisa de permissao sudo sem senha para os comandos do deploy:

```bash
sudo nano /etc/sudoers.d/usina-deploy
```

```
usina ALL=(ALL) NOPASSWD: /usr/bin/cp
usina ALL=(ALL) NOPASSWD: /usr/bin/chown
usina ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart usina-api usina-celery usina-beat
```

Validar: `sudo visudo -c -f /etc/sudoers.d/usina-deploy` (deve retornar `parsed OK`)

---

## 7. Variaveis de ambiente (.env)

Arquivo: `/home/usina/video-automation/backend/.env`

```bash
# === Supabase ===
SUPABASE_URL=https://XXXXX.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# === IA e APIs ===
GEMINI_API_KEY=
PEXELS_API_KEY=

# === YouTube ===
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=

# === Meta / Instagram ===
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=
META_INSTAGRAM_ACCOUNT_ID=

# === Telegram ===
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=

# === Email ===
RESEND_API_KEY=

# === Billing (Asaas) ===
ASAAS_API_KEY=
ASAAS_BASE_URL=https://api.asaas.com/v3
ASAAS_WEBHOOK_TOKEN=

# === Redis (local na VPS) ===
REDIS_URL=redis://localhost:6379/0

# === App ===
SECRET_KEY=GERE_COM_python3_-c_"import secrets; print(secrets.token_urlsafe(64))"
ENVIRONMENT=production
BASE_URL=https://api.usinadotempo.com.br
FRONTEND_URL=https://app.usinadotempo.com.br
LOG_LEVEL=INFO
```

> IMPORTANTE: Gerar SECRET_KEY forte com:
> ```bash
> python3.11 -c "import secrets; print(secrets.token_urlsafe(64))"
> ```

---

## 8. Mudanca no codigo antes do deploy

Antes de fazer deploy na Hetzner, atualizar o CORS no backend para incluir o novo dominio da API:

Arquivo `backend/main.py` — a whitelist de CORS ja inclui:
- `https://app.usinadotempo.com.br` (frontend)
- `https://usinadotempo.com.br`
- `https://www.usinadotempo.com.br`

O `FRONTEND_URL` no .env (`https://app.usinadotempo.com.br`) tambem e adicionado automaticamente.

**Nenhuma mudanca no codigo e necessaria** — ja esta preparado.

---

## 9. Verificacao pos-deploy

### 9.1 Testar endpoints

```bash
# Health check
curl https://api.usinadotempo.com.br/health
# Esperado: {"status":"ok","version":"0.3.0"}

# Testar login
curl -X POST https://api.usinadotempo.com.br/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"suporte@usinadotempo.com.br","password":"Usina@2026"}'
# Esperado: {"access_token":"...","refresh_token":"...","token_type":"bearer"}
```

### 9.2 Testar frontend

Acessar `https://app.usinadotempo.com.br` no navegador:
- [ ] Pagina de login carrega
- [ ] Login funciona (sem delay de cold start)
- [ ] Dashboard carrega com dados
- [ ] Negocios lista os negocios existentes
- [ ] SSL (cadeado verde) em ambos os dominios

### 9.3 Testar Celery

```bash
# Ver logs do worker
sudo journalctl -u usina-celery -f

# Disparar um pipeline pelo frontend e verificar se o worker processa
```

### 9.4 Testar Redis

```bash
redis-cli ping
# Esperado: PONG

redis-cli info clients
# Mostra conexoes ativas (uvicorn + celery)
```

---

## 10. Monitoramento

### 10.1 Logs dos servicos

```bash
# API (ultimas 50 linhas, ao vivo)
sudo journalctl -u usina-api -n 50 -f

# Celery worker
sudo journalctl -u usina-celery -n 50 -f

# Celery beat
sudo journalctl -u usina-beat -n 50 -f

# Caddy
sudo journalctl -u caddy -n 50 -f
```

### 10.2 Uso de recursos

```bash
# RAM e CPU
htop

# Disco
df -h

# Redis memoria
redis-cli info memory
```

### 10.3 UptimeRobot (monitoramento externo gratuito)

1. Criar conta em uptimerobot.com
2. Adicionar monitor HTTP:
   - URL: `https://api.usinadotempo.com.br/health`
   - Intervalo: 5 minutos
   - Alerta: email quando cair
3. Adicionar monitor para o frontend:
   - URL: `https://app.usinadotempo.com.br`

---

## 11. Seguranca adicional

### 11.1 Updates automaticos de seguranca

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# Selecionar "Yes"
```

### 11.2 Fail2ban (protecao contra brute-force SSH)

```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 11.3 Redis — bind apenas local

Verificar que Redis so aceita conexoes locais:

```bash
grep "^bind" /etc/redis/redis.conf
# Deve ser: bind 127.0.0.1 ::1
```

Se nao estiver, editar:
```bash
sudo nano /etc/redis/redis.conf
# Garantir: bind 127.0.0.1 ::1
sudo systemctl restart redis-server
```

---

## 12. Backups

### 12.1 Snapshots Hetzner (servidor inteiro)

- No painel Hetzner > Server > Snapshots
- Criar snapshot manual antes de grandes mudancas
- Custo: $0.01/GB/mes (~$0.40/mes para 40GB)

### 12.2 Supabase (banco de dados)

- Backups automaticos diarios (inclusos no free tier)
- Para backup manual: Supabase Dashboard > Settings > Database > Backups

### 12.3 Codigo

- Ja no GitHub (git push)
- O .env NAO esta no git (protegido pelo .gitignore)
- Fazer backup do .env separadamente (salvar em local seguro)

---

## 13. Troubleshooting

### Caddy nao emite SSL
```bash
# Verificar se DNS ja propagou
dig app.usinadotempo.com.br +short
# Deve retornar o IP do servidor

# Verificar logs do Caddy
sudo journalctl -u caddy -n 100
```

### API nao inicia
```bash
# Verificar logs
sudo journalctl -u usina-api -n 100

# Testar manualmente
cd /home/usina/video-automation/backend
source venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
# Ver erro no terminal
```

### Celery nao processa tarefas
```bash
# Verificar se Redis esta rodando
redis-cli ping

# Verificar logs do worker
sudo journalctl -u usina-celery -n 100

# Testar manualmente
cd /home/usina/video-automation/backend
source venv/bin/activate
celery -A core.tasks.celery_app worker --loglevel=debug
```

### Frontend mostra pagina em branco
```bash
# Verificar se os arquivos existem
ls -la /var/www/usina/

# Verificar permissoes
sudo chown -R caddy:caddy /var/www/usina

# Verificar Caddy
sudo systemctl status caddy
```

### Erro de CORS no login
```bash
# Verificar que FRONTEND_URL no .env esta correto
grep FRONTEND_URL /home/usina/video-automation/backend/.env
# Deve ser: https://app.usinadotempo.com.br

# Reiniciar API apos alterar .env
sudo systemctl restart usina-api
```

---

## Resumo da arquitetura final

```
Internet
   |
   v
Caddy (:80/:443) --- SSL automatico (Let's Encrypt)
   |         |
   |         +---> /var/www/usina/ (frontend static)
   |                app.usinadotempo.com.br
   |
   +---> localhost:8000 (Uvicorn/FastAPI, 2 workers)
            api.usinadotempo.com.br
            |
            +---> Redis localhost:6379 (fila + cache)
            |       |
            |       +---> Celery Worker (video,default)
            |       +---> Celery Beat (agendador)
            |
            +---> Supabase (externo, PostgreSQL + Storage)
```

**Custo total: $4.50/mes**

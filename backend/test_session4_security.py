"""
Testes de segurança — Sessão 4
Executa contra o servidor local (uvicorn rodando em localhost:8000).

Uso:
    python test_session4_security.py

Pré-requisitos:
    - Backend rodando: uvicorn main:app --reload
    - Migration 011 executada
    - Pelo menos um user cadastrado
"""

import sys
import time
import httpx

BASE = "http://localhost:8000"

# Credenciais de teste — criadas via signup durante o teste
import uuid
TEST_SUFFIX = uuid.uuid4().hex[:8]
TEST_EMAIL = f"test-{TEST_SUFFIX}@teste.com"
TEST_PASSWORD = "Senha@Forte123"
WRONG_PASSWORD = "senhaerrada123"

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} — {detail}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ============================================================
# Health check
# ============================================================
section("0. Health Check")
try:
    r = httpx.get(f"{BASE}/health", timeout=5)
    test("Servidor respondendo", r.status_code == 200, f"status={r.status_code}")
    test("Versão 0.2.0", r.json().get("version") == "0.2.0", f"got {r.json()}")
except httpx.ConnectError:
    print("  [ERRO] Servidor não está rodando em localhost:8000")
    print("         Execute: uvicorn main:app --reload")
    sys.exit(1)


# ============================================================
# 0.5 Criar user de teste via signup
# ============================================================
section("0.5 Criando user de teste")
r = httpx.post(f"{BASE}/auth/signup", json={
    "nome": "Teste Seguranca",
    "email": TEST_EMAIL,
    "senha": TEST_PASSWORD,
    "workspace_nome": f"WS Teste {TEST_SUFFIX}",
})
if r.status_code == 201:
    signup_tokens = r.json()
    test("Signup criou user", True)
    print(f"         Email: {TEST_EMAIL}")
else:
    test("Signup criou user", False, f"status={r.status_code} — {r.text[:200]}")
    print("         Testes de login/brute-force serão prejudicados")

time.sleep(1)


# ============================================================
# 1. Security Headers
# ============================================================
section("1. Security Headers")
r = httpx.get(f"{BASE}/health")
test("X-Content-Type-Options", r.headers.get("x-content-type-options") == "nosniff")
test("X-Frame-Options", r.headers.get("x-frame-options") == "DENY")
test("X-XSS-Protection", r.headers.get("x-xss-protection") == "1; mode=block")
test("Referrer-Policy", r.headers.get("referrer-policy") == "strict-origin-when-cross-origin")
test("Permissions-Policy", "camera=()" in (r.headers.get("permissions-policy") or ""))


# ============================================================
# 2. CORS Restritivo
# ============================================================
section("2. CORS")

# Origin permitida (localhost:5173 em dev)
r = httpx.options(
    f"{BASE}/health",
    headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
)
allowed = r.headers.get("access-control-allow-origin", "")
test("Origin permitida (localhost:5173)", allowed == "http://localhost:5173", f"got '{allowed}'")

# Origin não permitida
r = httpx.options(
    f"{BASE}/health",
    headers={"Origin": "http://evil-site.com", "Access-Control-Request-Method": "GET"},
)
allowed = r.headers.get("access-control-allow-origin", "")
test("Origin bloqueada (evil-site.com)", allowed != "http://evil-site.com", f"got '{allowed}'")


# ============================================================
# 3. Rate Limiting (Login: 5/min)
# ============================================================
section("3. Rate Limiting")

rate_limited = False
# Disparar muitas requests rápidas ao login (limite: 5/min por IP)
for i in range(10):
    r = httpx.post(f"{BASE}/auth/login", json={"email": TEST_EMAIL, "password": WRONG_PASSWORD})
    if r.status_code == 429:
        rate_limited = True
        test(f"Rate limit atingido na tentativa {i+1}", True)
        break

if not rate_limited:
    test("Rate limiting funcionando (login 5/min)", False, f"Último status: {r.status_code} após 10 tentativas")

# Aguardar rate limit resetar para não afetar próximos testes
print("         Aguardando 62s para rate limit resetar...")
time.sleep(62)


# ============================================================
# 4. Brute-force Protection
# ============================================================
section("4. Brute-force Protection")

# Primeiro, fazer login válido para resetar contadores
r = httpx.post(f"{BASE}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
if r.status_code == 200:
    test("Login válido funciona (reset contadores)", True)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
elif r.status_code == 429:
    test("Login válido (rate limited, aguardando)", False, "Rate limit ainda ativo — aumente o sleep")
    token = signup_tokens.get("access_token", "") if 'signup_tokens' in dir() else ""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
else:
    test("Login válido funciona", False, f"status={r.status_code} — {r.text[:200]}")
    token = signup_tokens.get("access_token", "") if 'signup_tokens' in dir() else ""
    headers = {"Authorization": f"Bearer {token}"} if token else {}

# Agora testar brute-force: 5 tentativas erradas
lockout_detected = False
for i in range(6):
    r = httpx.post(f"{BASE}/auth/login", json={"email": TEST_EMAIL, "password": WRONG_PASSWORD})
    if r.status_code == 423:
        lockout_detected = True
        test(f"Conta bloqueada (lockout) na tentativa {i+1}", True)
        break
    elif r.status_code == 429:
        test("Rate limit antes do lockout", True, "Rate limit e brute-force ambos funcionando")
        break

if not lockout_detected and r.status_code != 429:
    test("Brute-force lockout", False, f"Última resposta: status={r.status_code}")

# Verificar que a conta está realmente bloqueada
if lockout_detected:
    r = httpx.post(f"{BASE}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    test("Login bloqueado mesmo com senha correta", r.status_code == 423, f"status={r.status_code}")


# ============================================================
# 5. Billing Enforcement
# ============================================================
section("5. Billing Enforcement")

if headers:
    # Testar que o middleware está ativo (não necessariamente bloqueia — depende do plano)
    r = httpx.get(f"{BASE}/billing/subscription", headers=headers)
    if r.status_code == 200:
        sub = r.json()
        plan = sub.get("plans", {})
        test("Subscription carregada", True)
        print(f"         Plano: {plan.get('slug', '?')}, Status: {sub.get('status', '?')}")
        print(f"         max_videos_mes: {plan.get('max_videos_mes', 'N/A')}")
    else:
        test("Subscription carregada", r.status_code == 404, f"status={r.status_code} (404 = sem plano, ok)")

    # Testar uso
    r = httpx.get(f"{BASE}/billing/usage", headers=headers)
    if r.status_code == 200:
        usage = r.json()
        test("Usage carregado", True)
        print(f"         Videos gerados: {usage.get('videos_gerados', 0)}")
    else:
        test("Usage carregado", False, f"status={r.status_code}")
else:
    print(f"  [SKIP] Sem token válido")


# ============================================================
# 6. LGPD Endpoints
# ============================================================
section("6. LGPD Endpoints")

if headers:
    # Export de dados
    r = httpx.get(f"{BASE}/privacy/my-data", headers=headers)
    test("GET /privacy/my-data retorna dados", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        test("Export contém workspace", data.get("workspace") is not None)
        test("Export contém users", isinstance(data.get("users"), list))
        test("Export contém exported_at", data.get("exported_at") is not None)
else:
    print(f"  [SKIP] Sem token válido")


# ============================================================
# 7. Verificação de Email
# ============================================================
section("7. Verificação de Email")

if headers:
    # Testar endpoint com código errado
    r = httpx.post(f"{BASE}/auth/verify-email", json={"code": "000000"}, headers=headers)
    test("Código inválido retorna 400", r.status_code == 400, f"status={r.status_code}")
else:
    print(f"  [SKIP] Sem token válido")


# ============================================================
# 8. Audit Log (verificar se registrou ações)
# ============================================================
section("8. Audit Log")
print("  [INFO] Audit log registra automaticamente via middleware.")
print("         Verifique no Supabase: SELECT * FROM audit_log ORDER BY criado_em DESC LIMIT 10;")


# ============================================================
# Resultado
# ============================================================
print(f"\n{'='*60}")
print(f"  RESULTADO: {passed} passed, {failed} failed")
print(f"{'='*60}")

sys.exit(1 if failed > 0 else 0)

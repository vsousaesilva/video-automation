-- Migration 011: Segurança, Auditoria e Hardening (Sessão 4)
-- Adiciona campos para brute-force protection, verificação de email,
-- índices de audit_log e função de rotação de logs.

-- ============================================================
-- 1. Brute-force protection: campos na tabela users
-- ============================================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;

-- ============================================================
-- 2. Verificação de email
-- ============================================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_code VARCHAR(6);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_expires_at TIMESTAMPTZ;

-- ============================================================
-- 3. LGPD: soft-delete / anonimização
-- ============================================================
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS deletion_requested_at TIMESTAMPTZ;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS deletion_scheduled_for TIMESTAMPTZ;

-- ============================================================
-- 4. Índices adicionais para audit_log (já criada na 009)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_acao ON audit_log(acao);
CREATE INDEX IF NOT EXISTS idx_audit_log_recurso ON audit_log(recurso, recurso_id);

-- ============================================================
-- 5. Índice para brute-force lookup
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_users_email_ativo ON users(email, ativo);

-- ============================================================
-- 6. Função de rotação de logs (execution_logs > 90 dias)
-- ============================================================
CREATE OR REPLACE FUNCTION rotate_execution_logs(dias INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM execution_logs
    WHERE criado_em < NOW() - (dias || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 7. Função de rotação de audit_log (> 365 dias)
-- ============================================================
CREATE OR REPLACE FUNCTION rotate_audit_logs(dias INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_log
    WHERE criado_em < NOW() - (dias || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 8. RLS para audit_log (workspace_id isolamento)
-- ============================================================
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS audit_log_workspace_isolation ON audit_log;
CREATE POLICY audit_log_workspace_isolation ON audit_log
    FOR ALL
    USING (workspace_id = current_setting('app.workspace_id', true)::uuid);

-- ============================================================
-- 9. Marcar users existentes como email_verified (legado)
-- ============================================================
UPDATE users SET email_verified = true WHERE email_verified IS NULL OR email_verified = false;

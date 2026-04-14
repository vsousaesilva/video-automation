/**
 * Inicializacao opcional do Sentry no frontend.
 * Carregado dinamicamente para manter o bundle leve quando DSN nao esta
 * configurado. Em ambientes sem @sentry/react, falha silenciosamente.
 */

export async function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) return false

  try {
    const Sentry = await import('@sentry/react')
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE,
      release: import.meta.env.VITE_APP_VERSION || 'unknown',
      tracesSampleRate: import.meta.env.MODE === 'production' ? 0.1 : 0,
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 1.0,
    })
    window.Sentry = Sentry
    return true
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[sentry] SDK indisponivel — erros nao serao reportados:', err?.message)
    return false
  }
}

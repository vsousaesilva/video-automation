import { Component } from 'react'

/**
 * ErrorBoundary global — captura erros de render e reporta para Sentry
 * quando disponivel. Fallback visual amigavel com acao "tentar novamente".
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    if (window.Sentry?.captureException) {
      window.Sentry.captureException(error, { extra: errorInfo })
    }
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md w-full bg-white rounded-lg shadow-sm border border-slate-200 p-8 text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h1 className="text-xl font-semibold text-slate-800 mb-2">
            Algo deu errado
          </h1>
          <p className="text-sm text-slate-600 mb-6">
            Encontramos um erro inesperado. A equipe ja foi notificada automaticamente.
          </p>
          {import.meta.env.DEV && this.state.error && (
            <pre className="text-left bg-slate-100 text-xs text-slate-700 p-3 rounded mb-4 overflow-auto max-h-48">
              {String(this.state.error?.stack || this.state.error)}
            </pre>
          )}
          <div className="flex gap-2 justify-center">
            <button
              onClick={this.handleReset}
              className="px-4 py-2 text-sm bg-slate-200 hover:bg-slate-300 rounded"
            >
              Tentar novamente
            </button>
            <button
              onClick={this.handleReload}
              className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded"
            >
              Recarregar pagina
            </button>
          </div>
        </div>
      </div>
    )
  }
}

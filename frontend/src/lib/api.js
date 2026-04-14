import axios from 'axios'
import { toast } from '../stores/toastStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function genCorrelationId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID().replace(/-/g, '')
  return `${Date.now()}${Math.random().toString(36).slice(2, 10)}`
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor: injeta token em todas as requisições
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (!config.headers['X-Correlation-ID']) {
    config.headers['X-Correlation-ID'] = genCorrelationId()
  }
  return config
})

// Interceptor: trata 401 redirecionando para login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token')

      // Tenta refresh apenas uma vez
      if (refreshToken && !error.config._retry) {
        error.config._retry = true
        try {
          const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          const newToken = res.data.access_token
          localStorage.setItem('access_token', newToken)
          error.config.headers.Authorization = `Bearer ${newToken}`
          return api(error.config)
        } catch {
          // Refresh falhou — limpar e redirecionar
        }
      }

      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // Toasts para erros comuns — silencioso se a chamada optou por tratar
    // via { silent: true } no config.
    if (!error.config?.silent) {
      const status = error.response?.status
      const detail = error.response?.data?.detail
      if (!error.response) {
        toast.error('Sem conexao com o servidor. Verifique sua internet.')
      } else if (status === 429) {
        toast.warning(typeof detail === 'string' ? detail : 'Limite atingido. Tente novamente mais tarde.')
      } else if (status >= 500) {
        toast.error('Erro no servidor. Nossa equipe foi notificada.')
        if (window.Sentry?.captureException) {
          window.Sentry.captureException(error)
        }
      }
    }

    return Promise.reject(error)
  }
)

export default api

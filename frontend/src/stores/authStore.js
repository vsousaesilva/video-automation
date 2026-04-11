import { create } from 'zustand'
import api from '../lib/api'

function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(base64))
    return payload
  } catch {
    return null
  }
}

function loadUserFromStorage() {
  const token = localStorage.getItem('access_token')
  if (!token) return null
  const payload = parseJwt(token)
  if (!payload) return null
  // Verificar expiração
  if (payload.exp && payload.exp * 1000 < Date.now()) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    return null
  }
  return {
    id: payload.sub,
    workspace_id: payload.workspace_id,
    papel: payload.papel,
  }
}

const useAuthStore = create((set) => ({
  user: loadUserFromStorage(),
  isAuthenticated: !!loadUserFromStorage(),
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null })
    try {
      const res = await api.post('/auth/login', { email, password })
      const { access_token, refresh_token } = res.data
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      const payload = parseJwt(access_token)
      const user = {
        id: payload.sub,
        workspace_id: payload.workspace_id,
        papel: payload.papel,
      }

      set({ user, isAuthenticated: true, loading: false })
      return true
    } catch (err) {
      const message = err.response?.data?.detail || 'Erro ao fazer login'
      set({ error: message, loading: false })
      return false
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
  },
}))

export default useAuthStore

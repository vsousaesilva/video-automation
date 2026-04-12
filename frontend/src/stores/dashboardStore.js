import { create } from 'zustand'
import api from '../lib/api'

const useDashboardStore = create((set) => ({
  pendingVideos: [],
  pendingCount: 0,
  schedule: [],
  stats: { hoje: 0, semana: 0, mes: 0 },
  loading: false,

  fetchPendingVideos: async () => {
    try {
      const res = await api.get('/videos/pending')
      set({ pendingVideos: res.data, pendingCount: res.data.length })
    } catch (err) {
      console.error('Erro ao buscar vídeos pendentes:', err)
    }
  },

  fetchSchedule: async () => {
    try {
      const res = await api.get('/negocios/schedule/today')
      set({ schedule: res.data })
    } catch (err) {
      console.error('Erro ao buscar agenda do dia:', err)
    }
  },

  fetchStats: async () => {
    try {
      const res = await api.get('/videos/pending')
      const allVideos = res.data

      // Buscar negocios para obter historico
      const negociosRes = await api.get('/negocios')
      const negocios = negociosRes.data

      let hoje = 0, semana = 0, mes = 0
      const now = new Date()
      const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      const startOfWeek = new Date(startOfDay)
      startOfWeek.setDate(startOfDay.getDate() - startOfDay.getDay())
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

      // Buscar historico de cada negocio para contar publicados
      for (const negocio of negocios) {
        try {
          const histRes = await api.get(`/negocios/${negocio.id}/history`)
          const videos = histRes.data || []
          for (const v of videos) {
            if (v.status !== 'publicado' || !v.publicado_em) continue
            const pub = new Date(v.publicado_em)
            if (pub >= startOfMonth) mes++
            if (pub >= startOfWeek) semana++
            if (pub >= startOfDay) hoje++
          }
        } catch {
          // Negocio sem historico — ignorar
        }
      }

      set({ stats: { hoje, semana, mes } })
    } catch (err) {
      console.error('Erro ao buscar estatísticas:', err)
    }
  },

  fetchAll: async () => {
    set({ loading: true })
    const store = useDashboardStore.getState()
    await Promise.all([
      store.fetchPendingVideos(),
      store.fetchSchedule(),
      store.fetchStats(),
    ])
    set({ loading: false })
  },
}))

export default useDashboardStore

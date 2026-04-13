import { create } from 'zustand'
import api from '../lib/api'

const useDashboardStore = create((set, get) => ({
  // Overview KPIs
  overview: {
    total_negocios: 0,
    videos_gerados_mes: 0,
    videos_publicados_mes: 0,
    aprovacoes_pendentes: 0,
    taxa_aprovacao_30d: 0,
    plano_nome: 'Sem plano',
    plano_status: 'inactive',
  },

  // Video Engine metrics
  videoEngine: {
    por_status: {},
    evolucao_30d: [],
    top_negocios: [],
    total_30d: 0,
  },

  // Usage vs limits
  usage: {
    plano_nome: 'Sem plano',
    plano_status: 'inactive',
    trial_ends_at: null,
    metrics: [],
  },

  // Timeline
  timeline: [],

  // Pending videos (mantido para badge no Layout)
  pendingVideos: [],
  pendingCount: 0,

  loading: false,
  error: null,

  fetchOverview: async () => {
    try {
      const res = await api.get('/dashboard/overview')
      set({ overview: res.data })
    } catch (err) {
      console.error('Erro ao buscar overview:', err)
    }
  },

  fetchVideoEngine: async () => {
    try {
      const res = await api.get('/dashboard/video-engine')
      set({ videoEngine: res.data })
    } catch (err) {
      console.error('Erro ao buscar metricas video engine:', err)
    }
  },

  fetchUsage: async () => {
    try {
      const res = await api.get('/dashboard/usage')
      set({ usage: res.data })
    } catch (err) {
      console.error('Erro ao buscar uso do plano:', err)
    }
  },

  fetchTimeline: async () => {
    try {
      const res = await api.get('/dashboard/timeline?limit=15')
      set({ timeline: res.data })
    } catch (err) {
      console.error('Erro ao buscar timeline:', err)
    }
  },

  fetchPendingVideos: async () => {
    try {
      const res = await api.get('/videos/pending')
      set({ pendingVideos: res.data, pendingCount: res.data.length })
    } catch (err) {
      console.error('Erro ao buscar videos pendentes:', err)
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null })
    const store = useDashboardStore.getState()
    await Promise.all([
      store.fetchOverview(),
      store.fetchVideoEngine(),
      store.fetchUsage(),
      store.fetchTimeline(),
      store.fetchPendingVideos(),
    ])
    set({ loading: false })
  },
}))

export default useDashboardStore

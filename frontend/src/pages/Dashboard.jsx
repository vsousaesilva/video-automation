import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import useDashboardStore from '../stores/dashboardStore'
import PipelineTimeline from '../components/PipelineTimeline'

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`text-3xl font-bold mt-2 ${color}`}>{value}</p>
    </div>
  )
}

function StatusBadge({ status }) {
  const map = {
    aguardando_aprovacao: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Aguardando' },
    processando: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Processando' },
    aprovado: { bg: 'bg-green-100', text: 'text-green-700', label: 'Aprovado' },
    publicado: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Publicado' },
    erro_validacao: { bg: 'bg-red-100', text: 'text-red-700', label: 'Erro' },
    erro_publicacao: { bg: 'bg-red-100', text: 'text-red-700', label: 'Erro Pub.' },
  }
  const style = map[status] || { bg: 'bg-gray-100', text: 'text-gray-700', label: status }
  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  )
}

export default function Dashboard() {
  const { stats, schedule, pendingVideos, loading, fetchAll } = useDashboardStore()

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const displayVideos = pendingVideos.slice(0, 5)

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {loading && (
        <div className="flex items-center gap-2 mb-4 text-sm text-gray-500">
          <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Carregando dados...
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <StatCard label="Publicados hoje" value={stats.hoje} color="text-indigo-600" />
        <StatCard label="Publicados esta semana" value={stats.semana} color="text-blue-600" />
        <StatCard label="Publicados este mês" value={stats.mes} color="text-emerald-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline Timeline */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline do Dia</h2>
          <PipelineTimeline schedule={schedule} />
        </div>

        {/* Pending Approvals */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Aguardando Aprovação</h2>
            {pendingVideos.length > 5 && (
              <Link
                to="/approvals"
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                Ver todos ({pendingVideos.length})
              </Link>
            )}
          </div>

          {displayVideos.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              Nenhum vídeo aguardando aprovação.
            </div>
          ) : (
            <div className="space-y-3">
              {displayVideos.map((video) => (
                <div
                  key={video.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {video.negocio_id?.slice(0, 8)}...
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(video.criado_em).toLocaleString('pt-BR')}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={video.status} />
                    <Link
                      to="/approvals"
                      className="text-xs text-indigo-600 hover:underline"
                    >
                      Revisar
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

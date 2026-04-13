import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts'
import useDashboardStore from '../stores/dashboardStore'

// === Cores por status de video ===
const STATUS_COLORS = {
  publicado: '#10b981',
  aprovado: '#3b82f6',
  aguardando_aprovacao: '#f59e0b',
  processando: '#6366f1',
  erro_validacao: '#ef4444',
  erro_publicacao: '#dc2626',
  rejeitado: '#9ca3af',
}

const STATUS_LABELS = {
  publicado: 'Publicado',
  aprovado: 'Aprovado',
  aguardando_aprovacao: 'Aguardando',
  processando: 'Processando',
  erro_validacao: 'Erro',
  erro_publicacao: 'Erro Pub.',
  rejeitado: 'Rejeitado',
}

// === KPI Card ===
function KpiCard({ label, value, subtitle, icon, color = 'text-indigo-600', bgIcon = 'bg-indigo-100' }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4">
      <div className={`w-11 h-11 rounded-lg ${bgIcon} flex items-center justify-center shrink-0`}>
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">{label}</p>
        <p className={`text-2xl font-bold mt-0.5 ${color}`}>{value}</p>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}

// === Usage Bar ===
function UsageBar({ label, atual, limite, percentual }) {
  const barColor =
    percentual >= 100 ? 'bg-red-500' :
    percentual >= 80 ? 'bg-amber-500' :
    'bg-indigo-500'

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="text-gray-500 font-medium">
          {atual}{limite != null ? ` / ${limite}` : ''}
        </span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(percentual, 100)}%` }}
        />
      </div>
    </div>
  )
}

// === Status Badge ===
function StatusDot({ status, count }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="w-3 h-3 rounded-full"
        style={{ backgroundColor: STATUS_COLORS[status] || '#9ca3af' }}
      />
      <span className="text-sm text-gray-700">
        {STATUS_LABELS[status] || status}
      </span>
      <span className="text-sm font-semibold text-gray-900 ml-auto">{count}</span>
    </div>
  )
}

// === Timeline Item ===
function TimelineItem({ item }) {
  const date = new Date(item.criado_em)
  const timeStr = date.toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  })

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-gray-100 last:border-0">
      <div className="w-2 h-2 rounded-full bg-indigo-400 mt-1.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800">{item.descricao}</p>
        <p className="text-xs text-gray-400 mt-0.5">{timeStr}</p>
      </div>
    </div>
  )
}

// === Custom Tooltip ===
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-medium text-gray-700 mb-1">
        {new Date(label + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
      </p>
      {payload.map((entry) => (
        <p key={entry.dataKey} style={{ color: entry.color }}>
          {entry.dataKey === 'gerados' ? 'Gerados' : 'Publicados'}: {entry.value}
        </p>
      ))}
    </div>
  )
}

// === Main Dashboard ===
export default function Dashboard() {
  const { overview, videoEngine, usage, timeline, pendingVideos, loading, fetchAll } = useDashboardStore()

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const displayPending = pendingVideos.slice(0, 5)

  // Formatar dados do grafico (ultimos 14 dias para legibilidade)
  const chartData = (videoEngine.evolucao_30d || []).slice(-14).map((d) => ({
    ...d,
    label: new Date(d.data + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }),
  }))

  // Status badges ordenados por contagem
  const statusEntries = Object.entries(videoEngine.por_status || {})
    .sort((a, b) => b[1] - a[1])

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Visão geral do workspace &middot; Plano <span className="font-medium">{overview.plano_nome}</span>
          </p>
        </div>
        {loading && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Atualizando...
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Negócios ativos"
          value={overview.total_negocios}
          icon={<NegociosIcon />}
          color="text-indigo-600"
          bgIcon="bg-indigo-100"
        />
        <KpiCard
          label="Vídeos gerados (mês)"
          value={overview.videos_gerados_mes}
          icon={<VideoIcon />}
          color="text-blue-600"
          bgIcon="bg-blue-100"
        />
        <KpiCard
          label="Vídeos publicados (mês)"
          value={overview.videos_publicados_mes}
          icon={<PublishIcon />}
          color="text-emerald-600"
          bgIcon="bg-emerald-100"
        />
        <KpiCard
          label="Aguardando aprovação"
          value={overview.aprovacoes_pendentes}
          subtitle={`Taxa de aprovação: ${overview.taxa_aprovacao_30d}%`}
          icon={<ApprovalIcon />}
          color={overview.aprovacoes_pendentes > 0 ? 'text-amber-600' : 'text-gray-600'}
          bgIcon={overview.aprovacoes_pendentes > 0 ? 'bg-amber-100' : 'bg-gray-100'}
        />
      </div>

      {/* Row 2: Grafico de evolucao + Status breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Grafico */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Evolução — Últimos 14 dias</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gradGerados" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradPublicados" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#9ca3af' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#9ca3af' }} />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone" dataKey="gerados" stroke="#6366f1" strokeWidth={2}
                  fill="url(#gradGerados)" dot={false}
                />
                <Area
                  type="monotone" dataKey="publicados" stroke="#10b981" strokeWidth={2}
                  fill="url(#gradPublicados)" dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[260px] text-gray-400 text-sm">
              Sem dados de vídeo nos últimos 14 dias.
            </div>
          )}
          <div className="flex gap-6 mt-3 text-xs text-gray-500">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-indigo-500 rounded" /> Gerados
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-emerald-500 rounded" /> Publicados
            </span>
          </div>
        </div>

        {/* Status breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Vídeos por Status</h2>
          <p className="text-xs text-gray-400 mb-3">Últimos 30 dias &middot; {videoEngine.total_30d} vídeos</p>
          {statusEntries.length > 0 ? (
            <div className="space-y-3">
              {statusEntries.map(([status, count]) => (
                <StatusDot key={status} status={status} count={count} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">Nenhum vídeo no período.</p>
          )}
        </div>
      </div>

      {/* Row 3: Uso do plano + Timeline + Top negocios */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Uso do plano */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Uso do Plano</h2>
            <Link to="/settings/billing" className="text-xs text-indigo-600 hover:text-indigo-700 font-medium">
              Gerenciar
            </Link>
          </div>
          <div className="mb-4">
            <span className="text-sm font-medium text-gray-700">{usage.plano_nome}</span>
            <PlanBadge status={usage.plano_status} />
          </div>
          <div className="space-y-4">
            {(usage.metrics || []).map((m, i) => (
              <UsageBar
                key={i}
                label={m.label}
                atual={m.atual}
                limite={m.limite}
                percentual={m.percentual}
              />
            ))}
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Atividade Recente</h2>
          {timeline.length > 0 ? (
            <div className="max-h-80 overflow-y-auto">
              {timeline.map((item) => (
                <TimelineItem key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">Nenhuma atividade registrada.</p>
          )}
        </div>

        {/* Top negocios + Atalhos */}
        <div className="space-y-6">
          {/* Top negocios */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Negócios</h2>
            <p className="text-xs text-gray-400 mb-3">Por vídeos publicados (30d)</p>
            {(videoEngine.top_negocios || []).length > 0 ? (
              <div className="space-y-2.5">
                {videoEngine.top_negocios.map((n, i) => (
                  <div key={n.negocio_id} className="flex items-center gap-3">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="text-sm text-gray-700 flex-1 truncate">{n.nome}</span>
                    <span className="text-sm font-semibold text-gray-900">{n.publicados}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-4">Nenhuma publicação no período.</p>
            )}
          </div>

          {/* Atalhos rapidos */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Ações Rápidas</h2>
            <div className="space-y-2">
              <Link
                to="/negocios"
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
              >
                <PlusIcon /> Criar negócio
              </Link>
              <Link
                to="/approvals"
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
              >
                <CheckIcon /> Revisar aprovações
                {overview.aprovacoes_pendentes > 0 && (
                  <span className="ml-auto bg-amber-100 text-amber-700 text-xs font-bold px-2 py-0.5 rounded-full">
                    {overview.aprovacoes_pendentes}
                  </span>
                )}
              </Link>
              <Link
                to="/media"
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
              >
                <MediaIcon /> Banco de mídia
              </Link>
              <Link
                to="/history"
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
              >
                <HistoryIcon /> Ver histórico
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Row 4: Aprovacoes pendentes */}
      {displayPending.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Aprovações Pendentes</h2>
            <Link
              to="/approvals"
              className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Ver todos ({pendingVideos.length})
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
            {displayPending.map((video) => (
              <div
                key={video.id}
                className="p-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-colors"
              >
                <p className="text-sm font-medium text-gray-900 truncate">
                  {video.negocio_id?.slice(0, 8)}...
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(video.criado_em).toLocaleString('pt-BR', {
                    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
                  })}
                </p>
                <Link
                  to="/approvals"
                  className="text-xs text-indigo-600 hover:underline mt-2 inline-block"
                >
                  Revisar
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// === Plan badge ===
function PlanBadge({ status }) {
  const map = {
    active: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Ativo' },
    trial: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Trial' },
    past_due: { bg: 'bg-red-100', text: 'text-red-700', label: 'Pendente' },
    canceled: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Cancelado' },
    expired: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Expirado' },
    inactive: { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Inativo' },
  }
  const s = map[status] || map.inactive
  return (
    <span className={`ml-2 px-2 py-0.5 text-xs font-medium rounded-full ${s.bg} ${s.text}`}>
      {s.label}
    </span>
  )
}

// === Icons ===
function NegociosIcon() {
  return (
    <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  )
}

function VideoIcon() {
  return (
    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  )
}

function PublishIcon() {
  return (
    <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
  )
}

function ApprovalIcon() {
  return (
    <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  )
}

function MediaIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

function HistoryIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

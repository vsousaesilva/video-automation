import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'

const TABS = [
  { id: 'campanhas', label: 'Campanhas' },
  { id: 'metricas', label: 'Métricas' },
  { id: 'comparativo', label: 'Comparativo' },
  { id: 'contas', label: 'Contas' },
  { id: 'regras', label: 'Regras' },
]

const PLATAFORMAS = [
  { id: '', label: 'Todas', color: 'bg-gray-100 text-gray-700' },
  { id: 'meta', label: 'Meta', color: 'bg-blue-100 text-blue-700' },
  { id: 'google', label: 'Google', color: 'bg-yellow-100 text-yellow-800' },
  { id: 'tiktok', label: 'TikTok', color: 'bg-pink-100 text-pink-700' },
]

function PlatformBadge({ plataforma }) {
  const p = PLATAFORMAS.find((x) => x.id === plataforma) || PLATAFORMAS[0]
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${p.color}`}>
      {plataforma ? plataforma.toUpperCase() : '—'}
    </span>
  )
}

function formatBRL(cents) {
  const v = (cents || 0) / 100
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function StatusBadge({ status }) {
  const map = {
    active: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700',
    archived: 'bg-gray-100 text-gray-600',
    deleted: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${map[status] || 'bg-gray-100 text-gray-700'}`}>
      {status || '—'}
    </span>
  )
}

export default function Ads() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('campanhas')
  const [plataforma, setPlataforma] = useState('')
  const [accounts, setAccounts] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [crossPlatform, setCrossPlatform] = useState(null)
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAccounts = useCallback(async () => {
    try {
      const res = await api.get('/ads/accounts')
      setAccounts(res.data || [])
    } catch (e) {
      if (e.response?.status === 403) {
        setError('Ads Manager disponível apenas nos planos Pro e Enterprise.')
      }
    }
  }, [])

  const loadCampaigns = useCallback(async () => {
    try {
      const params = plataforma ? { plataforma } : {}
      const res = await api.get('/ads/campaigns', { params })
      setCampaigns(res.data || [])
    } catch {}
  }, [plataforma])

  const loadMetrics = useCallback(async () => {
    try {
      const params = plataforma ? { plataforma } : {}
      const res = await api.get('/ads/metrics', { params })
      setMetrics(res.data)
    } catch {}
  }, [plataforma])

  const loadCrossPlatform = useCallback(async () => {
    try {
      const res = await api.get('/ads/metrics/cross-platform')
      setCrossPlatform(res.data)
    } catch {}
  }, [])

  const loadRules = useCallback(async () => {
    try {
      const res = await api.get('/ads/rules')
      setRules(res.data || [])
    } catch {}
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.all([
      loadAccounts(),
      loadCampaigns(),
      loadMetrics(),
      loadCrossPlatform(),
      loadRules(),
    ]).finally(() => setLoading(false))
  }, [loadAccounts, loadCampaigns, loadMetrics, loadCrossPlatform, loadRules])

  async function handleSync(accountId) {
    try {
      await api.post(`/ads/accounts/${accountId}/sync`)
      await Promise.all([loadCampaigns(), loadMetrics(), loadAccounts()])
    } catch (e) {
      alert('Falha no sync: ' + (e.response?.data?.detail || e.message))
    }
  }

  async function handleAction(campaignId, action) {
    if (!confirm(`Confirma ${action === 'pause' ? 'pausar' : 'ativar'} esta campanha?`)) return
    try {
      await api.post(`/ads/campaigns/${campaignId}/action`, { action })
      await loadCampaigns()
    } catch (e) {
      alert('Falha: ' + (e.response?.data?.detail || e.message))
    }
  }

  async function handleDisconnect(accountId) {
    if (!confirm('Desvincular esta conta? As campanhas e métricas sincronizadas serão removidas.')) return
    try {
      await api.delete(`/ads/accounts/${accountId}`)
      await loadAccounts()
    } catch (e) {
      alert('Falha: ' + (e.response?.data?.detail || e.message))
    }
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded border border-amber-300 bg-amber-50 p-4 text-amber-900">
          {error}
          <button
            onClick={() => navigate('/settings/billing')}
            className="ml-4 underline font-medium"
          >
            Fazer upgrade
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Ads Manager</h1>
          <p className="text-sm text-gray-500">Meta · Google · TikTok Ads</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1 bg-gray-100 rounded p-1">
            {PLATAFORMAS.map((p) => (
              <button
                key={p.id || 'all'}
                onClick={() => setPlataforma(p.id)}
                className={`px-3 py-1 text-xs rounded transition ${
                  plataforma === p.id
                    ? 'bg-white shadow text-gray-900 font-medium'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          {accounts.length === 0 && !loading && (
            <button
              onClick={() => setTab('contas')}
              className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              Vincular primeira conta
            </button>
          )}
        </div>
      </header>

      <nav className="flex gap-6 border-b mb-6">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`pb-2 text-sm font-medium ${
              tab === t.id
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {loading && <p className="text-gray-500">Carregando...</p>}

      {!loading && tab === 'campanhas' && (
        <CampaignsTab campaigns={campaigns} onAction={handleAction} />
      )}
      {!loading && tab === 'metricas' && <MetricsTab metrics={metrics} />}
      {!loading && tab === 'comparativo' && <CrossPlatformTab data={crossPlatform} />}
      {!loading && tab === 'contas' && (
        <AccountsTab
          accounts={accounts}
          onConnect={loadAccounts}
          onSync={handleSync}
          onDisconnect={handleDisconnect}
        />
      )}
      {!loading && tab === 'regras' && (
        <RulesTab rules={rules} accounts={accounts} campaigns={campaigns} onChange={loadRules} />
      )}
    </div>
  )
}

// ============================================================
// Campanhas
// ============================================================
function CampaignsTab({ campaigns, onAction }) {
  if (campaigns.length === 0) {
    return <p className="text-gray-500">Nenhuma campanha sincronizada ainda.</p>
  }
  return (
    <div className="bg-white rounded shadow overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
          <tr>
            <th className="px-4 py-3">Campanha</th>
            <th className="px-4 py-3">Plataforma</th>
            <th className="px-4 py-3">Objetivo</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Orçamento diário</th>
            <th className="px-4 py-3">Conta</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((c) => (
            <tr key={c.id} className="border-t">
              <td className="px-4 py-3 font-medium">{c.nome}</td>
              <td className="px-4 py-3">
                <PlatformBadge plataforma={c.ad_accounts?.plataforma} />
              </td>
              <td className="px-4 py-3 text-gray-600">{c.objetivo || '—'}</td>
              <td className="px-4 py-3">
                <StatusBadge status={c.status} />
              </td>
              <td className="px-4 py-3">{formatBRL(c.orcamento_diario_centavos)}</td>
              <td className="px-4 py-3 text-gray-600">{c.ad_accounts?.nome || '—'}</td>
              <td className="px-4 py-3 text-right">
                {c.status === 'active' ? (
                  <button
                    onClick={() => onAction(c.id, 'pause')}
                    className="text-xs px-3 py-1 rounded bg-yellow-100 text-yellow-800 hover:bg-yellow-200"
                  >
                    Pausar
                  </button>
                ) : (
                  <button
                    onClick={() => onAction(c.id, 'activate')}
                    className="text-xs px-3 py-1 rounded bg-green-100 text-green-800 hover:bg-green-200"
                  >
                    Ativar
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ============================================================
// Metricas
// ============================================================
function MetricsTab({ metrics }) {
  if (!metrics) return <p className="text-gray-500">Sem dados de métricas.</p>
  const t = metrics.totais || {}
  const cards = [
    { label: 'Impressões', value: (t.impressoes || 0).toLocaleString('pt-BR') },
    { label: 'Cliques', value: (t.cliques || 0).toLocaleString('pt-BR') },
    { label: 'Conversões', value: (t.conversoes || 0).toLocaleString('pt-BR') },
    { label: 'Gasto', value: formatBRL(t.gasto_centavos) },
    { label: 'CPA', value: formatBRL(t.cpa_centavos) },
    { label: 'ROAS', value: (t.roas || 0).toFixed(2) + 'x' },
    { label: 'CTR', value: (t.ctr || 0).toFixed(2) + '%' },
  ]
  const max = Math.max(1, ...(metrics.serie || []).map((s) => s.gasto_centavos || 0))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded shadow p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{c.label}</p>
            <p className="mt-1 text-xl font-bold">{c.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded shadow p-4">
        <h3 className="text-sm font-medium mb-4">Gasto por dia</h3>
        <div className="flex items-end gap-1 h-40">
          {(metrics.serie || []).map((s) => (
            <div
              key={s.data}
              className="flex-1 bg-indigo-500 rounded-t relative group"
              style={{ height: `${((s.gasto_centavos || 0) / max) * 100}%`, minHeight: '2px' }}
              title={`${s.data}: ${formatBRL(s.gasto_centavos)}`}
            />
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {metrics.periodo?.desde} → {metrics.periodo?.ate}
        </p>
      </div>
    </div>
  )
}

// ============================================================
// Cross-platform (comparativo)
// ============================================================
function CrossPlatformTab({ data }) {
  if (!data || !data.plataformas?.length) {
    return <p className="text-gray-500">Sem dados para comparar. Vincule contas e aguarde o sync.</p>
  }
  const maxGasto = Math.max(1, ...data.plataformas.map((p) => p.gasto_centavos || 0))
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data.plataformas.map((p) => (
          <div key={p.plataforma} className="bg-white rounded shadow p-4">
            <div className="flex items-center justify-between mb-3">
              <PlatformBadge plataforma={p.plataforma} />
              <span className="text-xs text-gray-500">
                {((p.gasto_centavos / maxGasto) * 100).toFixed(0)}% do gasto
              </span>
            </div>
            <p className="text-2xl font-bold">{formatBRL(p.gasto_centavos)}</p>
            <p className="text-xs text-gray-500 mb-4">Gasto no período</p>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Impressões</span>
                <span>{(p.impressoes || 0).toLocaleString('pt-BR')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Cliques</span>
                <span>{(p.cliques || 0).toLocaleString('pt-BR')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Conversões</span>
                <span>{(p.conversoes || 0).toLocaleString('pt-BR')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">CPA</span>
                <span>{formatBRL(p.cpa_centavos)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">ROAS</span>
                <span>{(p.roas || 0).toFixed(2)}x</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">CTR</span>
                <span>{(p.ctr || 0).toFixed(2)}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded shadow p-4">
        <h3 className="text-sm font-medium mb-3">Gasto por plataforma</h3>
        <div className="space-y-2">
          {data.plataformas.map((p) => (
            <div key={p.plataforma} className="flex items-center gap-3">
              <div className="w-20 text-xs uppercase tracking-wide text-gray-500">{p.plataforma}</div>
              <div className="flex-1 h-6 bg-gray-100 rounded overflow-hidden">
                <div
                  className="h-full bg-indigo-500"
                  style={{ width: `${((p.gasto_centavos || 0) / maxGasto) * 100}%` }}
                />
              </div>
              <div className="w-28 text-right text-sm font-medium">{formatBRL(p.gasto_centavos)}</div>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-3">
          {data.periodo?.desde} → {data.periodo?.ate}
        </p>
      </div>
    </div>
  )
}

// ============================================================
// Contas
// ============================================================
function AccountsTab({ accounts, onConnect, onSync, onDisconnect }) {
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ plataforma: 'meta', external_id: '', nome: '', access_token: '' })
  const [submitting, setSubmitting] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/ads/accounts/connect', form)
      setShowModal(false)
      setForm({ plataforma: 'meta', external_id: '', nome: '', access_token: '' })
      await onConnect()
    } catch (e) {
      alert('Falha ao vincular: ' + (e.response?.data?.detail || e.message))
    } finally {
      setSubmitting(false)
    }
  }

  async function startOAuth(plataforma) {
    const redirect_uri = `${window.location.origin}/ads/oauth/callback`
    try {
      const res = await api.get(`/ads/oauth/${plataforma}/url`, { params: { redirect_uri } })
      if (res.data?.url) window.location.href = res.data.url
    } catch (e) {
      alert('Falha ao iniciar OAuth: ' + (e.response?.data?.detail || e.message))
    }
  }

  return (
    <div>
      <div className="flex justify-end mb-4 gap-2 flex-wrap">
        <button
          onClick={() => startOAuth('meta')}
          className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          Conectar Meta
        </button>
        <button
          onClick={() => startOAuth('google')}
          className="px-3 py-2 text-sm rounded bg-yellow-500 text-white hover:bg-yellow-600"
        >
          Conectar Google
        </button>
        <button
          onClick={() => startOAuth('tiktok')}
          className="px-3 py-2 text-sm rounded bg-pink-600 text-white hover:bg-pink-700"
        >
          Conectar TikTok
        </button>
        <button
          onClick={() => setShowModal(true)}
          className="px-3 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
        >
          + Vincular manualmente
        </button>
      </div>

      {accounts.length === 0 ? (
        <p className="text-gray-500">Nenhuma conta vinculada.</p>
      ) : (
        <div className="bg-white rounded shadow">
          {accounts.map((a) => (
            <div key={a.id} className="flex items-center justify-between px-4 py-3 border-b last:border-0">
              <div>
                <p className="font-medium">{a.nome || a.external_id}</p>
                <p className="text-xs text-gray-500">
                  {a.plataforma.toUpperCase()} · {a.external_id} · {a.moeda}
                  {a.ultimo_sync && ` · sync ${new Date(a.ultimo_sync).toLocaleString('pt-BR')}`}
                </p>
              </div>
              <div className="flex gap-2">
                <StatusBadge status={a.status} />
                <button
                  onClick={() => onSync(a.id)}
                  className="text-xs px-3 py-1 rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200"
                >
                  Sincronizar
                </button>
                <button
                  onClick={() => onDisconnect(a.id)}
                  className="text-xs px-3 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
                >
                  Desvincular
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <form
            onSubmit={submit}
            className="bg-white rounded shadow-xl p-6 w-full max-w-md space-y-4"
          >
            <h3 className="text-lg font-bold">Vincular conta de anúncios</h3>
            <p className="text-xs text-gray-500">
              Selecione a plataforma e informe o ID da conta + access token.
            </p>
            <select
              value={form.plataforma}
              onChange={(e) => setForm({ ...form, plataforma: e.target.value })}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="meta">Meta Ads (act_12345)</option>
              <option value="google">Google Ads (customer_id)</option>
              <option value="tiktok">TikTok Ads (advertiser_id)</option>
            </select>
            <input
              required
              placeholder={
                form.plataforma === 'meta'
                  ? 'act_1234567890'
                  : form.plataforma === 'google'
                  ? '1234567890 (customer_id)'
                  : '7012345678900 (advertiser_id)'
              }
              value={form.external_id}
              onChange={(e) => setForm({ ...form, external_id: e.target.value })}
              className="w-full border rounded px-3 py-2 text-sm"
            />
            <input
              placeholder="Nome (opcional)"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              className="w-full border rounded px-3 py-2 text-sm"
            />
            <textarea
              required
              placeholder="Access token"
              value={form.access_token}
              onChange={(e) => setForm({ ...form, access_token: e.target.value })}
              rows={3}
              className="w-full border rounded px-3 py-2 text-sm font-mono"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? 'Vinculando...' : 'Vincular'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

// ============================================================
// Regras de automacao
// ============================================================
function RulesTab({ rules, accounts, campaigns, onChange }) {
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({
    nome: '',
    ad_account_id: '',
    escopo: 'campaign',
    escopo_ids: [],
    metrica: 'cpa',
    operador: '>',
    valor: 0,
    periodo_dias: 3,
    acao: 'pause',
    ajuste_pct: 0,
  })

  async function submit(e) {
    e.preventDefault()
    try {
      await api.post('/ads/rules', {
        nome: form.nome,
        ad_account_id: form.ad_account_id || null,
        escopo: form.escopo,
        escopo_ids: form.escopo_ids,
        condicao: {
          metrica: form.metrica,
          operador: form.operador,
          valor: Number(form.valor),
          periodo_dias: Number(form.periodo_dias),
        },
        acao: form.acao,
        acao_params: form.acao === 'adjust_budget' ? { ajuste_pct: Number(form.ajuste_pct) } : {},
      })
      setShowModal(false)
      onChange()
    } catch (e) {
      alert('Falha: ' + (e.response?.data?.detail || e.message))
    }
  }

  async function toggle(rule) {
    await api.put(`/ads/rules/${rule.id}`, { ativa: !rule.ativa })
    onChange()
  }

  async function runNow(rule) {
    const res = await api.post(`/ads/rules/${rule.id}/run`)
    alert(`Regra executada. ${res.data?.acoes?.length || 0} ação(ões) aplicada(s).`)
    onChange()
  }

  async function remove(rule) {
    if (!confirm('Remover esta regra?')) return
    await api.delete(`/ads/rules/${rule.id}`)
    onChange()
  }

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
        >
          + Nova regra
        </button>
      </div>

      {rules.length === 0 ? (
        <p className="text-gray-500">Nenhuma regra configurada.</p>
      ) : (
        <div className="space-y-3">
          {rules.map((r) => (
            <div key={r.id} className="bg-white rounded shadow p-4 flex items-center justify-between">
              <div>
                <p className="font-medium">{r.nome}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Se <b>{r.condicao?.metrica}</b> {r.condicao?.operador} {r.condicao?.valor} em{' '}
                  {r.condicao?.periodo_dias}d → <b>{r.acao}</b>
                </p>
                {r.ultima_execucao && (
                  <p className="text-xs text-gray-400 mt-1">
                    Última execução: {new Date(r.ultima_execucao).toLocaleString('pt-BR')}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded ${r.ativa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                  {r.ativa ? 'ativa' : 'pausada'}
                </span>
                <button onClick={() => runNow(r)} className="text-xs px-3 py-1 rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200">
                  Executar
                </button>
                <button onClick={() => toggle(r)} className="text-xs px-3 py-1 rounded bg-gray-100 text-gray-700 hover:bg-gray-200">
                  {r.ativa ? 'Pausar' : 'Ativar'}
                </button>
                <button onClick={() => remove(r)} className="text-xs px-3 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200">
                  Remover
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <form onSubmit={submit} className="bg-white rounded shadow-xl p-6 w-full max-w-lg space-y-4">
            <h3 className="text-lg font-bold">Nova regra de automação</h3>
            <input
              required
              placeholder="Nome da regra"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              className="w-full border rounded px-3 py-2 text-sm"
            />
            <select
              value={form.ad_account_id}
              onChange={(e) => setForm({ ...form, ad_account_id: e.target.value })}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">Todas as contas</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nome || a.external_id}
                </option>
              ))}
            </select>

            <div className="border rounded p-3 space-y-2">
              <p className="text-xs text-gray-600 font-medium">SE</p>
              <div className="grid grid-cols-4 gap-2">
                <select
                  value={form.metrica}
                  onChange={(e) => setForm({ ...form, metrica: e.target.value })}
                  className="border rounded px-2 py-1 text-sm col-span-2"
                >
                  <option value="cpa">CPA</option>
                  <option value="roas">ROAS</option>
                  <option value="ctr">CTR</option>
                  <option value="gasto">Gasto</option>
                  <option value="cliques">Cliques</option>
                  <option value="impressoes">Impressões</option>
                </select>
                <select
                  value={form.operador}
                  onChange={(e) => setForm({ ...form, operador: e.target.value })}
                  className="border rounded px-2 py-1 text-sm"
                >
                  <option>&gt;</option>
                  <option>&lt;</option>
                  <option>&gt;=</option>
                  <option>&lt;=</option>
                  <option>==</option>
                </select>
                <input
                  type="number"
                  value={form.valor}
                  onChange={(e) => setForm({ ...form, valor: e.target.value })}
                  className="border rounded px-2 py-1 text-sm"
                  placeholder="Valor"
                />
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-600">Período:</span>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={form.periodo_dias}
                  onChange={(e) => setForm({ ...form, periodo_dias: e.target.value })}
                  className="border rounded px-2 py-1 text-sm w-20"
                />
                <span className="text-gray-600">dias</span>
              </div>
            </div>

            <div className="border rounded p-3 space-y-2">
              <p className="text-xs text-gray-600 font-medium">ENTÃO</p>
              <select
                value={form.acao}
                onChange={(e) => setForm({ ...form, acao: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="pause">Pausar campanha</option>
                <option value="activate">Ativar campanha</option>
                <option value="adjust_budget">Ajustar orçamento (%)</option>
                <option value="notify">Apenas notificar</option>
              </select>
              {form.acao === 'adjust_budget' && (
                <input
                  type="number"
                  value={form.ajuste_pct}
                  onChange={(e) => setForm({ ...form, ajuste_pct: e.target.value })}
                  placeholder="Ajuste % (ex: -20 ou 15)"
                  className="w-full border rounded px-3 py-2 text-sm"
                />
              )}
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
              >
                Criar regra
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

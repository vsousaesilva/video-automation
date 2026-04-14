import { useEffect, useState, useCallback } from 'react'
import api from '../lib/api'

const TABS = [
  { id: 'concorrentes', label: 'Concorrentes' },
  { id: 'analise', label: 'Nova Análise' },
  { id: 'relatorios', label: 'Relatórios' },
]

const REDES = [
  { id: 'instagram', label: 'Instagram' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'tiktok', label: 'TikTok' },
  { id: 'website', label: 'Website' },
]

const IMPACTO_COLOR = {
  alto: 'bg-red-100 text-red-700',
  medio: 'bg-yellow-100 text-yellow-700',
  baixo: 'bg-gray-100 text-gray-600',
}

const STATUS_COLOR = {
  pendente: 'bg-gray-100 text-gray-700',
  processando: 'bg-blue-100 text-blue-700',
  concluido: 'bg-green-100 text-green-700',
  erro: 'bg-red-100 text-red-700',
}

function StatusBadge({ status }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${STATUS_COLOR[status] || 'bg-gray-100 text-gray-700'}`}>
      {status || '—'}
    </span>
  )
}

export default function Benchmark() {
  const [tab, setTab] = useState('concorrentes')
  const [negocios, setNegocios] = useState([])
  const [negocioId, setNegocioId] = useState('')
  const [competitors, setCompetitors] = useState([])
  const [reports, setReports] = useState([])
  const [selectedReport, setSelectedReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadNegocios = useCallback(async () => {
    try {
      const res = await api.get('/negocios')
      const list = res.data || []
      setNegocios(list)
      if (!negocioId && list.length > 0) {
        setNegocioId(list[0].id)
      }
    } catch {}
  }, [negocioId])

  const loadCompetitors = useCallback(async () => {
    if (!negocioId) {
      setCompetitors([])
      return
    }
    try {
      const res = await api.get('/benchmark/competitors', { params: { negocio_id: negocioId } })
      setCompetitors(res.data || [])
    } catch (e) {
      if (e.response?.status === 403) {
        setError(e.response?.data?.detail || 'Benchmark indisponível no seu plano.')
      }
    }
  }, [negocioId])

  const loadReports = useCallback(async () => {
    if (!negocioId) {
      setReports([])
      return
    }
    try {
      const res = await api.get('/benchmark/reports', { params: { negocio_id: negocioId } })
      setReports(res.data || [])
    } catch {}
  }, [negocioId])

  useEffect(() => {
    loadNegocios()
  }, [loadNegocios])

  useEffect(() => {
    ;(async () => {
      setLoading(true)
      await Promise.all([loadCompetitors(), loadReports()])
      setLoading(false)
    })()
  }, [loadCompetitors, loadReports])

  if (loading) {
    return <div className="p-8 text-gray-500">Carregando…</div>
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Benchmark</h1>
          <p className="text-sm text-gray-500">
            Pesquise e monitore concorrentes por negócio. Insights com IA.
          </p>
        </div>
        {negocios.length > 0 && (
          <div>
            <label className="block text-xs text-gray-600 mb-1">Negócio</label>
            <select
              value={negocioId}
              onChange={(e) => {
                setNegocioId(e.target.value)
                setSelectedReport(null)
              }}
              className="border border-gray-300 rounded px-3 py-2 text-sm bg-white min-w-[220px]"
            >
              {negocios.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.nome}
                </option>
              ))}
            </select>
          </div>
        )}
      </header>

      {negocios.length === 0 && !loading && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
          Cadastre um negócio em <strong>Negócios</strong> antes de usar o Benchmark.
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      <nav className="flex gap-2 mb-6 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === 'concorrentes' && (
        <CompetitorsTab
          competitors={competitors}
          negocioId={negocioId}
          reload={loadCompetitors}
        />
      )}
      {tab === 'analise' && (
        <AnalyzeTab
          competitors={competitors}
          negocioId={negocioId}
          onDone={async () => {
            await loadReports()
            setTab('relatorios')
          }}
        />
      )}
      {tab === 'relatorios' && !selectedReport && (
        <ReportsTab
          reports={reports}
          onOpen={async (id) => {
            try {
              const res = await api.get(`/benchmark/reports/${id}`)
              setSelectedReport(res.data)
            } catch {}
          }}
          reload={loadReports}
        />
      )}
      {tab === 'relatorios' && selectedReport && (
        <ReportDetail report={selectedReport} onBack={() => setSelectedReport(null)} />
      )}
    </div>
  )
}


function CompetitorsTab({ competitors, negocioId, reload }) {
  const [form, setForm] = useState(null)

  const openNew = () => {
    if (!negocioId) {
      alert('Selecione um negócio antes de cadastrar concorrentes.')
      return
    }
    setForm({
      nome: '',
      segmento: '',
      website: '',
      descricao: '',
      instagram_handle: '',
      youtube_handle: '',
      tiktok_handle: '',
      palavras_chave: '',
    })
  }

  const submit = async () => {
    const { negocios: _n, ...rest } = form
    const payload = {
      ...rest,
      negocio_id: form.negocio_id || negocioId,
      palavras_chave: form.palavras_chave
        ? form.palavras_chave.split(',').map((s) => s.trim()).filter(Boolean)
        : [],
    }
    try {
      if (form.id) {
        delete payload.negocio_id // PUT nao suporta trocar de negocio
        await api.put(`/benchmark/competitors/${form.id}`, payload)
      } else {
        await api.post('/benchmark/competitors', payload)
      }
      setForm(null)
      reload()
    } catch (e) {
      alert(e.response?.data?.detail || 'Erro ao salvar')
    }
  }

  const remove = async (id) => {
    if (!confirm('Remover concorrente?')) return
    try {
      await api.delete(`/benchmark/competitors/${id}`)
      reload()
    } catch {}
  }

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button
          onClick={openNew}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
        >
          + Novo concorrente
        </button>
      </div>

      {competitors.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-12">
          Nenhum concorrente cadastrado. Adicione o primeiro para começar a analisar.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competitors.map((c) => (
            <div key={c.id} className="bg-white border border-gray-200 rounded p-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-gray-900">{c.nome}</h3>
                  <p className="text-xs text-gray-500">{c.segmento || '—'}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() =>
                      setForm({
                        ...c,
                        palavras_chave: (c.palavras_chave || []).join(', '),
                      })
                    }
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => remove(c.id)}
                    className="text-xs text-red-600 hover:underline"
                  >
                    Remover
                  </button>
                </div>
              </div>
              <div className="mt-2 text-xs text-gray-600 space-y-1">
                {c.website && <div>🔗 {c.website}</div>}
                {c.instagram_handle && <div>📷 @{c.instagram_handle}</div>}
                {c.youtube_handle && <div>▶️ {c.youtube_handle}</div>}
                {c.tiktok_handle && <div>🎵 @{c.tiktok_handle}</div>}
              </div>
              {c.palavras_chave?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {c.palavras_chave.map((k) => (
                    <span
                      key={k}
                      className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                    >
                      {k}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {form && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">
              {form.id ? 'Editar concorrente' : 'Novo concorrente'}
            </h2>
            <div className="space-y-3">
              {[
                ['nome', 'Nome *'],
                ['segmento', 'Segmento'],
                ['website', 'Website'],
                ['instagram_handle', 'Instagram (handle sem @)'],
                ['youtube_handle', 'YouTube (@canal ou ID)'],
                ['tiktok_handle', 'TikTok (handle sem @)'],
              ].map(([field, label]) => (
                <div key={field}>
                  <label className="block text-xs text-gray-600 mb-1">{label}</label>
                  <input
                    type="text"
                    value={form[field] || ''}
                    onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs text-gray-600 mb-1">Descrição</label>
                <textarea
                  value={form.descricao || ''}
                  onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                  rows={3}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">
                  Palavras-chave (separadas por vírgula)
                </label>
                <input
                  type="text"
                  value={form.palavras_chave || ''}
                  onChange={(e) => setForm({ ...form, palavras_chave: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setForm(null)}
                className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
              >
                Cancelar
              </button>
              <button
                onClick={submit}
                disabled={!form.nome}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


function AnalyzeTab({ competitors, negocioId, onDone }) {
  const [nome, setNome] = useState('')
  const [selected, setSelected] = useState([])
  const [redes, setRedes] = useState(['instagram', 'youtube', 'tiktok'])
  const [incluirKeywords, setIncluirKeywords] = useState(true)
  const [incluirInsights, setIncluirInsights] = useState(true)
  const [contexto, setContexto] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const toggle = (id, list, setList) =>
    setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id])

  const submit = async () => {
    if (!nome.trim() || selected.length === 0 || !negocioId) return
    setSubmitting(true)
    try {
      await api.post('/benchmark/analyze', {
        negocio_id: negocioId,
        nome: nome.trim(),
        competitor_ids: selected,
        redes,
        incluir_keywords: incluirKeywords,
        incluir_insights: incluirInsights,
        contexto_negocio: contexto || null,
      })
      await onDone()
    } catch (e) {
      alert(e.response?.data?.detail || 'Erro ao iniciar análise')
    } finally {
      setSubmitting(false)
    }
  }

  if (competitors.length === 0) {
    return (
      <p className="text-sm text-gray-500 text-center py-12">
        Cadastre concorrentes antes de rodar uma análise.
      </p>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded p-6 max-w-2xl">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nome do relatório
          </label>
          <input
            type="text"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Ex.: Análise Q2 — top 3 do setor"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Concorrentes a analisar ({selected.length})
          </label>
          <div className="max-h-40 overflow-y-auto border border-gray-200 rounded p-2 space-y-1">
            {competitors.map((c) => (
              <label key={c.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected.includes(c.id)}
                  onChange={() => toggle(c.id, selected, setSelected)}
                />
                <span>{c.nome}</span>
                <span className="text-xs text-gray-500">{c.segmento || ''}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Redes</label>
          <div className="flex flex-wrap gap-3">
            {REDES.map((r) => (
              <label key={r.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={redes.includes(r.id)}
                  onChange={() => toggle(r.id, redes, setRedes)}
                />
                {r.label}
              </label>
            ))}
          </div>
        </div>

        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={incluirKeywords}
              onChange={(e) => setIncluirKeywords(e.target.checked)}
            />
            Analisar palavras-chave (IA)
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={incluirInsights}
              onChange={(e) => setIncluirInsights(e.target.checked)}
            />
            Gerar insights (IA)
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Contexto do seu negócio (opcional)
          </label>
          <textarea
            value={contexto}
            onChange={(e) => setContexto(e.target.value)}
            rows={3}
            placeholder="Ex.: Somos uma clínica odontológica premium em Fortaleza focada em estética."
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
        </div>

        <button
          onClick={submit}
          disabled={submitting || !nome.trim() || selected.length === 0}
          className="w-full py-2 bg-indigo-600 text-white text-sm font-medium rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          {submitting ? 'Iniciando…' : 'Iniciar análise'}
        </button>
      </div>
    </div>
  )
}


function ReportsTab({ reports, onOpen, reload }) {
  const remove = async (id) => {
    if (!confirm('Remover relatório?')) return
    try {
      await api.delete(`/benchmark/reports/${id}`)
      reload()
    } catch {}
  }

  if (reports.length === 0) {
    return (
      <p className="text-sm text-gray-500 text-center py-12">
        Nenhum relatório ainda.
      </p>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr className="text-left text-xs uppercase text-gray-500">
            <th className="px-4 py-2">Nome</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Concorrentes</th>
            <th className="px-4 py-2">Criado</th>
            <th className="px-4 py-2" />
          </tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-2 font-medium">{r.nome}</td>
              <td className="px-4 py-2"><StatusBadge status={r.status} /></td>
              <td className="px-4 py-2 text-gray-600">
                {(r.competitor_ids || []).length}
              </td>
              <td className="px-4 py-2 text-gray-500 text-xs">
                {r.criado_em ? new Date(r.criado_em).toLocaleString('pt-BR') : '—'}
              </td>
              <td className="px-4 py-2 text-right space-x-2">
                <button
                  onClick={() => onOpen(r.id)}
                  className="text-indigo-600 text-xs hover:underline"
                >
                  Abrir
                </button>
                <button
                  onClick={() => remove(r.id)}
                  className="text-red-600 text-xs hover:underline"
                >
                  Remover
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


function ReportDetail({ report, onBack }) {
  const metricasPorConcorrente = {}
  for (const m of report.metricas || []) {
    const nome = m.competitors?.nome || m.competitor_id
    if (!metricasPorConcorrente[nome]) metricasPorConcorrente[nome] = []
    metricasPorConcorrente[nome].push(m)
  }

  return (
    <div>
      <button
        onClick={onBack}
        className="mb-4 text-sm text-gray-600 hover:text-gray-900"
      >
        ← Voltar
      </button>

      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold">{report.nome}</h2>
          <StatusBadge status={report.status} />
        </div>
        {report.erro_msg && (
          <p className="text-sm text-red-600 mt-1">Erro: {report.erro_msg}</p>
        )}
      </div>

      {report.resumo && (
        <section className="bg-indigo-50 border border-indigo-100 rounded p-4 mb-6">
          <h3 className="text-sm font-semibold text-indigo-900 mb-2">Resumo executivo</h3>
          <p className="text-sm text-indigo-900 whitespace-pre-wrap">{report.resumo}</p>
        </section>
      )}

      {(report.insights || []).length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Insights acionáveis</h3>
          <div className="space-y-2">
            {report.insights.map((ins, i) => (
              <div
                key={i}
                className="bg-white border border-gray-200 rounded p-3 flex gap-3"
              >
                <span
                  className={`text-xs px-2 py-0.5 rounded font-medium h-fit ${
                    IMPACTO_COLOR[ins.impacto] || 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {ins.impacto || 'médio'}
                </span>
                <div>
                  <h4 className="font-medium text-gray-900 text-sm">{ins.titulo}</h4>
                  <p className="text-xs text-gray-600 mt-0.5">{ins.descricao}</p>
                  {ins.categoria && (
                    <span className="text-[10px] uppercase text-gray-400 mt-1 inline-block">
                      {ins.categoria}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {Object.keys(metricasPorConcorrente).length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Métricas por concorrente</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(metricasPorConcorrente).map(([nome, rows]) => (
              <div key={nome} className="bg-white border border-gray-200 rounded p-4">
                <h4 className="font-semibold text-gray-900 mb-2">{nome}</h4>
                <table className="w-full text-xs">
                  <tbody>
                    {rows.map((m, i) => (
                      <tr key={i} className="border-b border-gray-100 last:border-0">
                        <td className="py-1 text-gray-500 capitalize">{m.rede}</td>
                        <td className="py-1 text-right">
                          {m.seguidores != null
                            ? `${m.seguidores.toLocaleString('pt-BR')} seg.`
                            : 'handle: ' + (m.dados_extras?.handle || m.dados_extras?.url || '—')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </section>
      )}

      {(report.keywords || []).length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Palavras-chave</h3>
          <div className="bg-white border border-gray-200 rounded overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr className="text-left text-xs uppercase text-gray-500">
                  <th className="px-4 py-2">Palavra</th>
                  <th className="px-4 py-2">Intenção</th>
                  <th className="px-4 py-2">Relevância</th>
                  <th className="px-4 py-2">Volume est.</th>
                  <th className="px-4 py-2">Associada a</th>
                </tr>
              </thead>
              <tbody>
                {report.keywords.map((k) => (
                  <tr key={k.id} className="border-b border-gray-100">
                    <td className="px-4 py-2 font-medium">{k.palavra}</td>
                    <td className="px-4 py-2 text-gray-600">{k.intencao || '—'}</td>
                    <td className="px-4 py-2">
                      {k.relevancia != null ? `${(k.relevancia * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td className="px-4 py-2 text-gray-600">
                      {k.volume_estimado
                        ? k.volume_estimado.toLocaleString('pt-BR')
                        : '—'}
                    </td>
                    <td className="px-4 py-2 text-gray-600">
                      {k.competitors?.nome || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

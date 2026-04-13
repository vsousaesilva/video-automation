import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'

const TIPOS = [
  { value: 'copy_ads', label: 'Copy para Anuncios', desc: 'Meta Ads, Google Ads, TikTok Ads' },
  { value: 'legenda', label: 'Legenda Social', desc: 'Instagram, LinkedIn, Facebook' },
  { value: 'roteiro', label: 'Roteiro de Video', desc: 'Videos curtos de marketing' },
  { value: 'artigo', label: 'Artigo para Blog', desc: 'Conteudo SEO otimizado' },
  { value: 'resposta_comentario', label: 'Resposta a Comentario', desc: 'Atendimento em redes sociais' },
  { value: 'email_marketing', label: 'Email Marketing', desc: 'Campanhas de email' },
]

const TONS = [
  { value: 'profissional', label: 'Profissional' },
  { value: 'casual', label: 'Casual' },
  { value: 'divertido', label: 'Divertido' },
  { value: 'formal', label: 'Formal' },
  { value: 'inspirador', label: 'Inspirador' },
  { value: 'educativo', label: 'Educativo' },
  { value: 'persuasivo', label: 'Persuasivo' },
  { value: 'tecnico', label: 'Tecnico' },
]

const PLATAFORMAS = [
  { value: 'meta', label: 'Meta (Facebook/Instagram)' },
  { value: 'google', label: 'Google Ads' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'linkedin', label: 'LinkedIn' },
]

const TABS = ['gerar', 'historico', 'templates']

export default function ContentAI() {
  const [tab, setTab] = useState('gerar')
  const [negocios, setNegocios] = useState([])

  // Gerar
  const [tipo, setTipo] = useState('copy_ads')
  const [tomVoz, setTomVoz] = useState('profissional')
  const [negocioId, setNegocioId] = useState('')
  const [plataforma, setPlataforma] = useState('')
  const [promptUsuario, setPromptUsuario] = useState('')
  const [quantidade, setQuantidade] = useState(1)
  const [templateId, setTemplateId] = useState('')
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  // Historico
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyFilter, setHistoryFilter] = useState('')

  // Templates
  const [templates, setTemplates] = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [showTemplateForm, setShowTemplateForm] = useState(false)
  const [tplForm, setTplForm] = useState({ nome: '', tipo: 'copy_ads', tom_voz: '', prompt_template: '' })

  // Detalhe expandido
  const [expandedId, setExpandedId] = useState(null)

  // Sucesso ao enviar para Video Engine
  const [videoSuccess, setVideoSuccess] = useState(null) // { contentId, conteudoId }
  const [sentToVideo, setSentToVideo] = useState(new Set())
  const navigate = useNavigate()

  useEffect(() => {
    fetchNegocios()
  }, [])

  useEffect(() => {
    if (tab === 'historico') fetchHistory()
    if (tab === 'templates') fetchTemplates()
  }, [tab])

  async function fetchNegocios() {
    try {
      const res = await api.get('/negocios')
      setNegocios(res.data || [])
    } catch {}
  }

  async function fetchHistory() {
    setHistoryLoading(true)
    try {
      const params = {}
      if (historyFilter) params.tipo = historyFilter
      const res = await api.get('/content-ai/history', { params })
      setHistory(res.data.items || [])
    } catch {} finally {
      setHistoryLoading(false)
    }
  }

  async function fetchTemplates() {
    setTemplatesLoading(true)
    try {
      const res = await api.get('/content-ai/templates')
      setTemplates(res.data.items || [])
    } catch {} finally {
      setTemplatesLoading(false)
    }
  }

  async function handleGenerate(e) {
    e.preventDefault()
    setGenerating(true)
    setError('')
    setResult(null)
    try {
      const body = {
        tipo,
        tom_voz: tomVoz,
        idioma: 'pt-BR',
        quantidade,
      }
      if (negocioId) body.negocio_id = negocioId
      if (plataforma) body.plataforma = plataforma
      if (promptUsuario.trim()) body.prompt_usuario = promptUsuario.trim()
      if (templateId) body.template_id = templateId
      const res = await api.post('/content-ai/generate', body)
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao gerar conteudo')
    } finally {
      setGenerating(false)
    }
  }

  async function handleCopy(text) {
    try {
      await navigator.clipboard.writeText(text)
    } catch {}
  }

  async function handleRate(contentId, avaliacao) {
    try {
      await api.post(`/content-ai/rate/${contentId}`, { avaliacao })
    } catch {}
  }

  async function handleUseInVideo(contentId) {
    if (!negocioId) {
      setError('Selecione um negocio para enviar ao Video Engine')
      return
    }
    try {
      const res = await api.post('/content-ai/use-in-video', {
        generated_content_id: contentId,
        negocio_id: negocioId,
      })
      setError('')
      setSentToVideo((prev) => new Set([...prev, contentId]))
      const isBuilding = res.data.status === 'building'
      setVideoSuccess({
        contentId,
        conteudoId: res.data.conteudo_id,
        negocioNome: negocios.find((n) => n.id === negocioId)?.nome || 'Negocio',
        isBuilding,
        message: res.data.message,
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao enviar para Video Engine')
    }
  }

  async function handleCreateTemplate(e) {
    e.preventDefault()
    try {
      await api.post('/content-ai/templates', tplForm)
      setShowTemplateForm(false)
      setTplForm({ nome: '', tipo: 'copy_ads', tom_voz: '', prompt_template: '' })
      fetchTemplates()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao criar template')
    }
  }

  async function handleDeleteTemplate(id) {
    if (!confirm('Remover este template?')) return
    try {
      await api.delete(`/content-ai/templates/${id}`)
      fetchTemplates()
    } catch {}
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Content AI</h1>
      <p className="text-gray-500 mb-6">Gere conteudo com inteligencia artificial para multiplos formatos</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'gerar' ? 'Gerar Conteudo' : t === 'historico' ? 'Historico' : 'Templates'}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {/* TAB: Gerar */}
      {tab === 'gerar' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Formulario */}
          <form onSubmit={handleGenerate} className="space-y-4">
            {/* Tipo de conteudo */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Tipo de Conteudo</label>
              <div className="grid grid-cols-2 gap-2">
                {TIPOS.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setTipo(t.value)}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      tipo === t.value
                        ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <span className="text-sm font-medium">{t.label}</span>
                    <span className="block text-xs text-gray-400 mt-0.5">{t.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Tom de voz */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tom de Voz</label>
              <select
                value={tomVoz}
                onChange={(e) => setTomVoz(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                {TONS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Negocio */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Negocio (opcional)</label>
              <select
                value={negocioId}
                onChange={(e) => setNegocioId(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Nenhum (generico)</option>
                {negocios.map((n) => (
                  <option key={n.id} value={n.id}>{n.nome}</option>
                ))}
              </select>
            </div>

            {/* Plataforma */}
            {(tipo === 'copy_ads' || tipo === 'legenda') && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Plataforma</label>
                <select
                  value={plataforma}
                  onChange={(e) => setPlataforma(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Geral</option>
                  {PLATAFORMAS.map((p) => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Template */}
            {templates.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Template (opcional)</label>
                <select
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Nenhum</option>
                  {templates.filter((t) => t.tipo === tipo).map((t) => (
                    <option key={t.id} value={t.id}>{t.nome}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Instrucoes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Instrucoes adicionais</label>
              <textarea
                value={promptUsuario}
                onChange={(e) => setPromptUsuario(e.target.value)}
                rows={3}
                placeholder="Ex: Foque em urgencia, mencione desconto de 30%, use linguagem jovem..."
                className="w-full border rounded-lg px-3 py-2 text-sm"
                maxLength={2000}
              />
            </div>

            {/* Quantidade */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Variacoes: {quantidade}
              </label>
              <input
                type="range"
                min={1}
                max={5}
                value={quantidade}
                onChange={(e) => setQuantidade(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400">
                <span>1</span><span>5</span>
              </div>
            </div>

            <button
              type="submit"
              disabled={generating}
              className="w-full bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generating ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Gerando...
                </span>
              ) : (
                'Gerar Conteudo'
              )}
            </button>
          </form>

          {/* Preview / Resultado */}
          <div>
            {!result && !generating && (
              <div className="flex items-center justify-center h-64 border-2 border-dashed border-gray-200 rounded-lg">
                <p className="text-gray-400 text-sm">O conteudo gerado aparecera aqui</p>
              </div>
            )}

            {generating && (
              <div className="flex items-center justify-center h-64 border-2 border-dashed border-indigo-200 rounded-lg bg-indigo-50">
                <div className="text-center">
                  <svg className="animate-spin h-8 w-8 text-indigo-500 mx-auto mb-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <p className="text-indigo-600 text-sm font-medium">Gerando conteudo com IA...</p>
                  <p className="text-indigo-400 text-xs mt-1">Isso pode levar alguns segundos</p>
                </div>
              </div>
            )}

            {result && result.contents && result.contents.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-900">
                    {result.contents.length} conteudo{result.contents.length > 1 ? 's' : ''} gerado{result.contents.length > 1 ? 's' : ''}
                  </h3>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
                    {result.status}
                  </span>
                </div>

                {result.contents.map((content, i) => (
                  <div key={content.id} className="border rounded-lg overflow-hidden">
                    <div className="p-4">
                      {content.titulo && (
                        <h4 className="font-medium text-gray-900 mb-2">{content.titulo}</h4>
                      )}
                      <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-60 overflow-auto">
                        {content.conteudo}
                      </div>

                      {/* Metadata (hashtags, cta, etc.) */}
                      {content.metadata && Object.keys(content.metadata).length > 0 && (
                        <div className="mt-3 pt-3 border-t">
                          {content.metadata.hashtags && (
                            <p className="text-xs text-indigo-500">
                              {content.metadata.hashtags.map((h) => `#${h}`).join(' ')}
                            </p>
                          )}
                          {content.metadata.cta && (
                            <p className="text-xs text-gray-500 mt-1">CTA: {content.metadata.cta}</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="bg-gray-50 px-4 py-2 flex items-center gap-2 border-t">
                      <button
                        onClick={() => handleCopy(content.conteudo)}
                        className="text-xs text-gray-600 hover:text-gray-900 px-2 py-1 rounded hover:bg-gray-200 transition-colors"
                      >
                        Copiar
                      </button>
                      {negocioId && !sentToVideo.has(content.id) && (
                        <button
                          onClick={() => handleUseInVideo(content.id)}
                          className="text-xs text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded hover:bg-indigo-50 transition-colors"
                        >
                          Usar no Video Engine
                        </button>
                      )}
                      {sentToVideo.has(content.id) && (
                        <span className="text-xs text-green-600 px-2 py-1">
                          Enviado ao Video Engine
                        </span>
                      )}
                      <div className="ml-auto flex gap-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            onClick={() => handleRate(content.id, star)}
                            className={`text-sm ${
                              content.avaliacao && star <= content.avaliacao
                                ? 'text-yellow-500'
                                : 'text-gray-300 hover:text-yellow-400'
                            }`}
                          >
                            ★
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Sucesso: proximos passos */}
                    {videoSuccess && videoSuccess.contentId === content.id && (
                      <div className="bg-green-50 border-t border-green-200 px-4 py-3">
                        <div className="flex items-start gap-2">
                          <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <div className="flex-1">
                            <p className="text-sm font-medium text-green-800">
                              {videoSuccess.isBuilding
                                ? `Video sendo construido para "${videoSuccess.negocioNome}"`
                                : `Conteudo enviado para "${videoSuccess.negocioNome}"`
                              }
                            </p>
                            <p className="text-xs text-green-600 mt-1">
                              {videoSuccess.isBuilding
                                ? 'O video esta sendo gerado agora (TTS, midia, renderizacao). Quando pronto, aparecera em Aprovacoes Pendentes. Isso pode levar alguns minutos.'
                                : videoSuccess.message || 'O conteudo foi adicionado ao pipeline do negocio.'
                              }
                            </p>
                            <div className="flex gap-3 mt-2">
                              <button
                                onClick={() => navigate('/history')}
                                className="text-xs font-medium text-green-700 hover:text-green-900 underline"
                              >
                                Historico de Videos
                              </button>
                              <button
                                onClick={() => navigate('/approvals')}
                                className="text-xs font-medium text-green-700 hover:text-green-900 underline"
                              >
                                Aprovacoes Pendentes
                              </button>
                              <button
                                onClick={() => setVideoSuccess(null)}
                                className="text-xs text-green-500 hover:text-green-700 ml-auto"
                              >
                                Fechar
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB: Historico */}
      {tab === 'historico' && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <select
              value={historyFilter}
              onChange={(e) => { setHistoryFilter(e.target.value); setTimeout(fetchHistory, 0) }}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">Todos os tipos</option>
              {TIPOS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {historyLoading ? (
            <div className="text-center py-12 text-gray-400">Carregando...</div>
          ) : history.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400">Nenhuma geracao encontrada</p>
              <button onClick={() => setTab('gerar')} className="text-indigo-600 text-sm mt-2 hover:underline">
                Gerar primeiro conteudo
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((req) => (
                <div key={req.id} className="border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedId(expandedId === req.id ? null : req.id)}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors text-left"
                  >
                    <div>
                      <span className="text-sm font-medium text-gray-900">
                        {TIPOS.find((t) => t.value === req.tipo)?.label || req.tipo}
                      </span>
                      <span className="text-xs text-gray-400 ml-3">
                        {new Date(req.criado_em).toLocaleString('pt-BR')}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        req.status === 'completed' ? 'bg-green-100 text-green-700' :
                        req.status === 'failed' ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {req.status}
                      </span>
                      <span className="text-xs text-gray-400">
                        {req.generated_contents?.length || 0} resultado{(req.generated_contents?.length || 0) !== 1 ? 's' : ''}
                      </span>
                      <svg className={`w-4 h-4 text-gray-400 transition-transform ${expandedId === req.id ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </button>

                  {expandedId === req.id && req.generated_contents && (
                    <div className="border-t px-4 py-3 space-y-3 bg-gray-50">
                      {req.prompt_usuario && (
                        <p className="text-xs text-gray-500 italic">"{req.prompt_usuario}"</p>
                      )}
                      {req.generated_contents.map((gc) => (
                        <div key={gc.id} className="bg-white p-3 rounded border">
                          {gc.titulo && <p className="text-sm font-medium mb-1">{gc.titulo}</p>}
                          <p className="text-sm text-gray-700 whitespace-pre-wrap max-h-40 overflow-auto">
                            {gc.conteudo}
                          </p>
                          <div className="mt-2 flex items-center gap-2">
                            <button
                              onClick={() => handleCopy(gc.conteudo)}
                              className="text-xs text-gray-500 hover:text-gray-700"
                            >
                              Copiar
                            </button>
                            {gc.avaliacao && (
                              <span className="text-xs text-yellow-500">{'★'.repeat(gc.avaliacao)}</span>
                            )}
                            {gc.usado_em && (
                              <span className="text-xs text-indigo-500">Usado: {gc.usado_em}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB: Templates */}
      {tab === 'templates' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-500">Templates de prompts reutilizaveis</p>
            <button
              onClick={() => setShowTemplateForm(true)}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 transition-colors"
            >
              Novo Template
            </button>
          </div>

          {/* Form novo template */}
          {showTemplateForm && (
            <form onSubmit={handleCreateTemplate} className="border rounded-lg p-4 mb-4 bg-gray-50 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Nome</label>
                  <input
                    type="text"
                    value={tplForm.nome}
                    onChange={(e) => setTplForm({ ...tplForm, nome: e.target.value })}
                    required
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder="Ex: Copy urgencia Black Friday"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Tipo</label>
                  <select
                    value={tplForm.tipo}
                    onChange={(e) => setTplForm({ ...tplForm, tipo: e.target.value })}
                    className="w-full border rounded px-3 py-2 text-sm"
                  >
                    {TIPOS.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Prompt Template <span className="text-gray-400">(use {'{{variavel}}'} para placeholders)</span>
                </label>
                <textarea
                  value={tplForm.prompt_template}
                  onChange={(e) => setTplForm({ ...tplForm, prompt_template: e.target.value })}
                  required
                  rows={4}
                  className="w-full border rounded px-3 py-2 text-sm font-mono"
                  placeholder={'Crie uma copy de {{produto}} focada em {{beneficio}} para {{plataforma}}'}
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded text-sm hover:bg-indigo-700">
                  Salvar
                </button>
                <button type="button" onClick={() => setShowTemplateForm(false)} className="text-gray-500 px-4 py-2 rounded text-sm hover:bg-gray-200">
                  Cancelar
                </button>
              </div>
            </form>
          )}

          {templatesLoading ? (
            <div className="text-center py-12 text-gray-400">Carregando...</div>
          ) : templates.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400">Nenhum template criado</p>
              <p className="text-gray-300 text-sm mt-1">Crie templates para padronizar seus prompts</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {templates.map((tpl) => (
                <div key={tpl.id} className="border rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 text-sm">{tpl.nome}</h4>
                      <span className="text-xs text-indigo-500">
                        {TIPOS.find((t) => t.value === tpl.tipo)?.label || tpl.tipo}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteTemplate(tpl.id)}
                      className="text-gray-400 hover:text-red-500 text-sm"
                      title="Remover"
                    >
                      ✕
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-2 font-mono line-clamp-3">
                    {tpl.prompt_template}
                  </p>
                  <button
                    onClick={() => { setTab('gerar'); setTemplateId(tpl.id); setTipo(tpl.tipo) }}
                    className="text-xs text-indigo-600 hover:underline mt-2"
                  >
                    Usar este template
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

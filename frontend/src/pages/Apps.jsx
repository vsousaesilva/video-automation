import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import MediaUploader from '../components/MediaUploader'

const STATUS_COLORS = {
  ativo: 'bg-green-100 text-green-700',
  pausado: 'bg-yellow-100 text-yellow-700',
  arquivado: 'bg-gray-100 text-gray-700',
}

const PLATAFORMA_LABELS = { instagram: 'Instagram', youtube: 'YouTube' }

const CATEGORIAS = [
  'saude', 'financas', 'produtividade', 'educacao', 'entretenimento',
  'negocios', 'tecnologia', 'utilidades', 'lifestyle', 'esportes',
]

const FREQUENCIAS = [
  { value: 'diaria', label: 'Diária' },
  { value: '3x_semana', label: '3x por semana' },
  { value: 'semanal', label: 'Semanal' },
]

const DIAS_SEMANA = [
  { value: 0, label: 'Dom' }, { value: 1, label: 'Seg' },
  { value: 2, label: 'Ter' }, { value: 3, label: 'Qua' },
  { value: 4, label: 'Qui' }, { value: 5, label: 'Sex' },
  { value: 6, label: 'Sáb' },
]

const EMPTY_FORM = {
  nome: '', categoria: '', descricao: '', publico_alvo: '',
  funcionalidades: '', diferenciais: '', cta: '', link_download: '',
  plataformas: ['instagram'], formato_instagram: '9_16', formato_youtube: 'ambos',
  frequencia: 'diaria', horario_disparo: 8, dias_semana: [],
  tom_voz: '', keywords: '',
}

export default function Apps() {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingApp, setEditingApp] = useState(null)
  const [selectedApp, setSelectedApp] = useState(null)
  const [activeTab, setActiveTab] = useState('detalhes')
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [existingHours, setExistingHours] = useState([])

  const fetchApps = () => {
    setLoading(true)
    api.get('/apps').then((res) => {
      setApps(res.data)
      setExistingHours(
        res.data.filter(a => a.status !== 'arquivado').map(a => ({
          hour: a.horario_disparo, id: a.id, nome: a.nome,
        }))
      )
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => { fetchApps() }, [])

  const openCreate = () => {
    setEditingApp(null)
    setForm(EMPTY_FORM)
    setError(null)
    setShowForm(true)
  }

  const openEdit = (app) => {
    setEditingApp(app)
    setForm({
      nome: app.nome || '',
      categoria: app.categoria || '',
      descricao: app.descricao || '',
      publico_alvo: app.publico_alvo || '',
      funcionalidades: (app.funcionalidades || []).join(', '),
      diferenciais: (app.diferenciais || []).join(', '),
      cta: app.cta || '',
      link_download: app.link_download || '',
      plataformas: app.plataformas || ['instagram'],
      formato_instagram: app.formato_instagram || '9_16',
      formato_youtube: app.formato_youtube || 'ambos',
      frequencia: app.frequencia || 'diaria',
      horario_disparo: app.horario_disparo ?? 8,
      dias_semana: app.dias_semana || [],
      tom_voz: app.tom_voz || '',
      keywords: (app.keywords || []).join(', '),
    })
    setError(null)
    setShowForm(true)
  }

  const hourConflict = existingHours.find(
    h => h.hour === Number(form.horario_disparo) && h.id !== editingApp?.id
  )

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)

    const payload = {
      nome: form.nome,
      categoria: form.categoria || null,
      descricao: form.descricao || null,
      publico_alvo: form.publico_alvo || null,
      funcionalidades: form.funcionalidades ? form.funcionalidades.split(',').map(s => s.trim()).filter(Boolean) : null,
      diferenciais: form.diferenciais ? form.diferenciais.split(',').map(s => s.trim()).filter(Boolean) : null,
      cta: form.cta || null,
      link_download: form.link_download || null,
      plataformas: form.plataformas,
      formato_instagram: form.formato_instagram,
      formato_youtube: form.plataformas.includes('youtube') ? form.formato_youtube : null,
      frequencia: form.frequencia,
      horario_disparo: Number(form.horario_disparo),
      dias_semana: form.frequencia !== 'diaria' ? form.dias_semana : null,
      tom_voz: form.tom_voz || null,
      keywords: form.keywords ? form.keywords.split(',').map(s => s.trim()).filter(Boolean) : null,
    }

    try {
      if (editingApp) {
        await api.put(`/apps/${editingApp.id}`, payload)
      } else {
        await api.post('/apps', payload)
      }
      setShowForm(false)
      fetchApps()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar app')
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (app, newStatus) => {
    try {
      if (newStatus === 'arquivado') {
        await api.delete(`/apps/${app.id}`)
      } else {
        await api.put(`/apps/${app.id}`, { status: newStatus })
      }
      fetchApps()
      if (selectedApp?.id === app.id) setSelectedApp(null)
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao alterar status')
    }
  }

  const updateField = (field, value) => setForm(prev => ({ ...prev, [field]: value }))

  const togglePlataforma = (plat) => {
    setForm(prev => {
      const has = prev.plataformas.includes(plat)
      const updated = has
        ? prev.plataformas.filter(p => p !== plat)
        : [...prev.plataformas, plat]
      return { ...prev, plataformas: updated.length ? updated : prev.plataformas }
    })
  }

  const toggleDia = (dia) => {
    setForm(prev => {
      const has = prev.dias_semana.includes(dia)
      return { ...prev, dias_semana: has ? prev.dias_semana.filter(d => d !== dia) : [...prev.dias_semana, dia] }
    })
  }

  // --- Detail / Media tab view ---
  if (selectedApp) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <button onClick={() => setSelectedApp(null)} className="text-sm text-indigo-600 hover:underline mb-4 flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          Voltar para lista
        </button>

        <div className="flex items-center gap-4 mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{selectedApp.nome}</h1>
          <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[selectedApp.status]}`}>
            {selectedApp.status}
          </span>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <div className="flex gap-6">
            {[{ key: 'detalhes', label: 'Detalhes' }, { key: 'media', label: 'Banco de Imagens' }].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === 'detalhes' ? (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
              <Detail label="Categoria" value={selectedApp.categoria} />
              <Detail label="Descrição" value={selectedApp.descricao} span />
              <Detail label="Público-alvo" value={selectedApp.publico_alvo} span />
              <Detail label="Funcionalidades" value={(selectedApp.funcionalidades || []).join(', ')} span />
              <Detail label="Diferenciais" value={(selectedApp.diferenciais || []).join(', ')} span />
              <Detail label="CTA" value={selectedApp.cta} />
              <Detail label="Link download" value={selectedApp.link_download} />
              <Detail label="Plataformas" value={(selectedApp.plataformas || []).map(p => PLATAFORMA_LABELS[p] || p).join(', ')} />
              <Detail label="Formato YouTube" value={selectedApp.formato_youtube} />
              <Detail label="Frequência" value={selectedApp.frequencia} />
              <Detail label="Horário de disparo" value={selectedApp.horario_disparo != null ? `${String(selectedApp.horario_disparo).padStart(2, '0')}:00` : '-'} />
              <Detail label="Dias da semana" value={(selectedApp.dias_semana || []).map(d => DIAS_SEMANA.find(ds => ds.value === d)?.label).filter(Boolean).join(', ') || 'Todos (diária)'} />
              <Detail label="Tom de voz" value={selectedApp.tom_voz} />
              <Detail label="Keywords" value={(selectedApp.keywords || []).join(', ')} span />
            </dl>
            <div className="mt-6 flex gap-3">
              <button onClick={() => openEdit(selectedApp)} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Editar</button>
              {selectedApp.status === 'ativo' && (
                <button onClick={() => handleStatusChange(selectedApp, 'pausado')} className="px-4 py-2 text-sm bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200">Pausar</button>
              )}
              {selectedApp.status === 'pausado' && (
                <button onClick={() => handleStatusChange(selectedApp, 'ativo')} className="px-4 py-2 text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200">Ativar</button>
              )}
              {selectedApp.status !== 'arquivado' && (
                <button onClick={() => { if (confirm('Tem certeza que deseja arquivar este app?')) handleStatusChange(selectedApp, 'arquivado') }} className="px-4 py-2 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200">Arquivar</button>
              )}
            </div>
          </div>
        ) : (
          <MediaUploader appId={selectedApp.id} />
        )}
      </div>
    )
  }

  // --- Form modal ---
  if (showForm) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <button onClick={() => setShowForm(false)} className="text-sm text-indigo-600 hover:underline mb-4 flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          Voltar
        </button>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">{editingApp ? 'Editar App' : 'Novo App'}</h1>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
          {/* Nome e Categoria */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Nome do app *" value={form.nome} onChange={v => updateField('nome', v)} required minLength={2} />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoria</label>
              <select value={form.categoria} onChange={e => updateField('categoria', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
                <option value="">Selecionar...</option>
                {CATEGORIAS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          {/* Descrição */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrição completa</label>
            <textarea value={form.descricao} onChange={e => updateField('descricao', e.target.value)}
              rows={3} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>

          {/* Público-alvo */}
          <Field label="Público-alvo" value={form.publico_alvo} onChange={v => updateField('publico_alvo', v)} placeholder='Ex: "mulheres 25-40 interessadas em bem-estar"' />

          {/* Funcionalidades e Diferenciais */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Funcionalidades (separadas por vírgula)" value={form.funcionalidades} onChange={v => updateField('funcionalidades', v)} />
            <Field label="Diferenciais (separados por vírgula)" value={form.diferenciais} onChange={v => updateField('diferenciais', v)} />
          </div>

          {/* CTA e Link */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Call to Action" value={form.cta} onChange={v => updateField('cta', v)} placeholder="Ex: Baixe grátis na App Store" />
            <Field label="Link de download" value={form.link_download} onChange={v => updateField('link_download', v)} placeholder="https://..." />
          </div>

          {/* Plataformas */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Plataformas *</label>
            <div className="flex gap-3">
              {Object.entries(PLATAFORMA_LABELS).map(([key, label]) => (
                <button key={key} type="button" onClick={() => togglePlataforma(key)}
                  className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                    form.plataformas.includes(key) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Formato YouTube */}
          {form.plataformas.includes('youtube') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Formato YouTube</label>
              <select value={form.formato_youtube} onChange={e => updateField('formato_youtube', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
                <option value="16_9">Horizontal (16:9)</option>
                <option value="9_16">Vertical (9:16 — Shorts)</option>
                <option value="ambos">Ambos</option>
              </select>
            </div>
          )}

          {/* Frequência e Horário */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequência</label>
              <select value={form.frequencia} onChange={e => updateField('frequencia', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
                {FREQUENCIAS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Horário de disparo *</label>
              <select value={form.horario_disparo} onChange={e => updateField('horario_disparo', Number(e.target.value))}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                  hourConflict ? 'border-red-400 bg-red-50' : 'border-gray-300'
                }`}>
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                ))}
              </select>
              {hourConflict && (
                <p className="text-xs text-red-600 mt-1">
                  Horário já em uso pelo app "{hourConflict.nome}"
                </p>
              )}
            </div>
          </div>

          {/* Dias da semana */}
          {form.frequencia !== 'diaria' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Dias da semana</label>
              <div className="flex gap-2">
                {DIAS_SEMANA.map(d => (
                  <button key={d.value} type="button" onClick={() => toggleDia(d.value)}
                    className={`w-10 h-10 text-xs rounded-lg border transition-colors ${
                      form.dias_semana.includes(d.value) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}>
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Tom e Keywords */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Tom de voz" value={form.tom_voz} onChange={v => updateField('tom_voz', v)} placeholder="Ex: profissional, descontraído" />
            <Field label="Keywords SEO (separadas por vírgula)" value={form.keywords} onChange={v => updateField('keywords', v)} />
          </div>

          {/* Botões */}
          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button type="submit" disabled={saving || !!hourConflict}
              className="px-6 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed transition-colors">
              {saving ? 'Salvando...' : editingApp ? 'Salvar alterações' : 'Criar app'}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="px-6 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors">
              Cancelar
            </button>
          </div>
        </form>
      </div>
    )
  }

  // --- App list ---
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Aplicativos</h1>
        <button onClick={openCreate}
          className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">
          + Novo App
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Carregando...</p>
      ) : apps.length === 0 ? (
        <div className="text-center py-12 text-gray-400">Nenhum aplicativo cadastrado.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {apps.map((app) => (
            <div key={app.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedApp(app)}>
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-gray-900">{app.nome}</h3>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[app.status] || 'bg-gray-100 text-gray-700'}`}>
                  {app.status}
                </span>
              </div>
              {app.categoria && <p className="text-xs text-gray-500 mb-2">{app.categoria}</p>}
              {app.descricao && <p className="text-sm text-gray-600 line-clamp-2 mb-3">{app.descricao}</p>}

              {/* Plataformas */}
              <div className="flex gap-1.5 mb-3">
                {(app.plataformas || []).map(p => (
                  <span key={p} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{PLATAFORMA_LABELS[p] || p}</span>
                ))}
              </div>

              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>{app.horario_disparo != null ? `Disparo: ${String(app.horario_disparo).padStart(2, '0')}:00` : ''}</span>
                <span>{app.frequencia}</span>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100" onClick={e => e.stopPropagation()}>
                <button onClick={() => openEdit(app)} className="text-xs text-indigo-600 hover:underline">Editar</button>
                {app.status === 'ativo' && (
                  <button onClick={() => handleStatusChange(app, 'pausado')} className="text-xs text-yellow-600 hover:underline">Pausar</button>
                )}
                {app.status === 'pausado' && (
                  <button onClick={() => handleStatusChange(app, 'ativo')} className="text-xs text-green-600 hover:underline">Ativar</button>
                )}
                {app.status !== 'arquivado' && (
                  <button onClick={() => { if (confirm('Arquivar este app?')) handleStatusChange(app, 'arquivado') }} className="text-xs text-red-600 hover:underline">Arquivar</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Field({ label, value, onChange, required, minLength, placeholder, type = 'text' }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)}
        required={required} minLength={minLength} placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
    </div>
  )
}

function Detail({ label, value, span }) {
  return (
    <div className={span ? 'md:col-span-2' : ''}>
      <dt className="text-sm font-medium text-gray-500">{label}</dt>
      <dd className="mt-1 text-sm text-gray-900">{value || '—'}</dd>
    </div>
  )
}

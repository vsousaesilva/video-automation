import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/authStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TIPO_LABELS = {
  nota: 'Nota',
  email: 'Email',
  ligacao: 'Ligacao',
  reuniao: 'Reuniao',
  tarefa: 'Tarefa',
}

const TIPO_ICONS = {
  nota: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
  email: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  ligacao: 'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z',
  reuniao: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  tarefa: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
}

const TIPO_COLORS = {
  nota: 'bg-gray-100 text-gray-600',
  email: 'bg-blue-100 text-blue-600',
  ligacao: 'bg-green-100 text-green-600',
  reuniao: 'bg-purple-100 text-purple-600',
  tarefa: 'bg-amber-100 text-amber-600',
}

export default function ContactDetail() {
  const { id } = useParams()
  const token = localStorage.getItem('access_token')
  const navigate = useNavigate()

  const [contact, setContact] = useState(null)
  const [activities, setActivities] = useState([])
  const [deals, setDeals] = useState([])
  const [loading, setLoading] = useState(true)

  // Activity modal
  const [showActivityModal, setShowActivityModal] = useState(false)
  const [activityForm, setActivityForm] = useState({ tipo: 'nota', titulo: '', descricao: '', contact_id: id })

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const fetchContact = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/crm/contacts/${id}`, { headers })
      if (!res.ok) { navigate('/crm'); return }
      const data = await res.json()
      setContact(data?.contact || null)
      setActivities(Array.isArray(data?.activities) ? data.activities : [])
      setDeals(Array.isArray(data?.deals) ? data.deals : [])
    } catch (err) {
      console.error('Erro ao carregar contato:', err)
    } finally {
      setLoading(false)
    }
  }, [id, token])

  useEffect(() => { fetchContact() }, [fetchContact])

  const handleCreateActivity = async () => {
    try {
      await fetch(`${API}/crm/activities`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...activityForm, contact_id: id }),
      })
      setShowActivityModal(false)
      setActivityForm({ tipo: 'nota', titulo: '', descricao: '', contact_id: id })
      fetchContact()
    } catch (err) {
      console.error('Erro ao criar atividade:', err)
    }
  }

  const handleDeleteActivity = async (activityId) => {
    if (!window.confirm('Remover esta atividade?')) return
    await fetch(`${API}/crm/activities/${activityId}`, { method: 'DELETE', headers })
    fetchContact()
  }

  const handleToggleActivity = async (activity) => {
    await fetch(`${API}/crm/activities/${activity.id}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ concluida: !activity.concluida }),
    })
    fetchContact()
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  const formatCurrency = (centavos) => {
    return (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }

  if (loading) return <div className="p-6 text-center text-gray-400">Carregando...</div>
  if (!contact) return <div className="p-6 text-center text-gray-400">Contato nao encontrado</div>

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Back button */}
      <button onClick={() => navigate('/crm')} className="text-sm text-indigo-600 hover:text-indigo-800 mb-4 flex items-center gap-1">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
        Voltar para contatos
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Contact info */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-full bg-indigo-100 flex items-center justify-center text-xl font-bold text-indigo-600">
                {contact.nome[0]?.toUpperCase()}
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">{contact.nome}</h1>
                {contact.cargo && <p className="text-sm text-gray-500">{contact.cargo}</p>}
              </div>
            </div>

            <div className="space-y-3 text-sm">
              {contact.email && (
                <div className="flex items-center gap-2 text-gray-600">
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                  {contact.email}
                </div>
              )}
              {contact.telefone && (
                <div className="flex items-center gap-2 text-gray-600">
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg>
                  {contact.telefone}
                </div>
              )}
              {contact.empresa && (
                <div className="flex items-center gap-2 text-gray-600">
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
                  {contact.empresa}
                </div>
              )}
              <div className="flex items-center gap-2 text-gray-500">
                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                Criado em {formatDate(contact.criado_em)}
              </div>
            </div>

            {/* Tags */}
            {contact.tags?.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1">
                {contact.tags.map(t => (
                  <span key={t.id} className="px-2 py-0.5 rounded-full text-xs font-medium text-white" style={{ backgroundColor: t.cor }}>
                    {t.nome}
                  </span>
                ))}
              </div>
            )}

            {/* Notes */}
            {contact.notas && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <p className="text-xs font-medium text-gray-500 mb-1">Notas</p>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{contact.notas}</p>
              </div>
            )}
          </div>

          {/* Deals do contato */}
          {deals.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6 mt-4">
              <h3 className="font-semibold text-gray-900 mb-3">Oportunidades</h3>
              <div className="space-y-2">
                {deals.map(d => (
                  <div key={d.id} className="p-3 rounded-lg border border-gray-100 hover:border-gray-200">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900">{d.titulo}</span>
                      <span className="text-sm font-semibold text-green-600">{formatCurrency(d.valor_centavos)}</span>
                    </div>
                    {d.deal_stages && (
                      <div className="flex items-center gap-1 mt-1">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: d.deal_stages.cor }} />
                        <span className="text-xs text-gray-500">{d.deal_stages.nome}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Timeline de Atividades</h2>
              <button
                onClick={() => setShowActivityModal(true)}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                + Nova Atividade
              </button>
            </div>

            {activities.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">Nenhuma atividade registrada</p>
            ) : (
              <div className="space-y-4">
                {activities.map((a) => (
                  <div key={a.id} className="flex gap-3 group">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${TIPO_COLORS[a.tipo] || 'bg-gray-100 text-gray-600'}`}>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={TIPO_ICONS[a.tipo] || TIPO_ICONS.nota} />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-gray-500 uppercase">{TIPO_LABELS[a.tipo] || a.tipo}</span>
                          {a.tipo === 'tarefa' && (
                            <button onClick={() => handleToggleActivity(a)} className={`text-xs px-2 py-0.5 rounded ${a.concluida ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                              {a.concluida ? 'Concluida' : 'Pendente'}
                            </button>
                          )}
                        </div>
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <span className="text-xs text-gray-400">{formatDate(a.criado_em)}</span>
                          <button onClick={() => handleDeleteActivity(a.id)} className="text-red-400 hover:text-red-600">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        </div>
                      </div>
                      {a.titulo && <p className="text-sm font-medium text-gray-900 mt-0.5">{a.titulo}</p>}
                      {a.descricao && <p className="text-sm text-gray-600 mt-1 whitespace-pre-wrap">{a.descricao}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Activity Modal */}
      {showActivityModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold mb-4">Nova Atividade</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(TIPO_LABELS).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setActivityForm({ ...activityForm, tipo: key })}
                      className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${activityForm.tipo === key ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Titulo</label>
                <input type="text" value={activityForm.titulo} onChange={e => setActivityForm({ ...activityForm, titulo: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Resumo da atividade" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Descricao</label>
                <textarea value={activityForm.descricao} onChange={e => setActivityForm({ ...activityForm, descricao: e.target.value })} rows={4} className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Detalhes..." />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setShowActivityModal(false)} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">Cancelar</button>
              <button onClick={handleCreateActivity} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Salvar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

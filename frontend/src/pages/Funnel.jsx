import { useState, useEffect, useCallback, useRef } from 'react'
import useAuthStore from '../stores/authStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Funnel() {
  const token = useAuthStore((s) => s.token)

  const [stages, setStages] = useState([])
  const [deals, setDeals] = useState([])
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('aberto')

  // Deal modal
  const [showDealModal, setShowDealModal] = useState(false)
  const [editingDeal, setEditingDeal] = useState(null)
  const [dealForm, setDealForm] = useState({ titulo: '', contact_id: '', stage_id: '', valor_centavos: 0, notas: '' })

  // Drag state
  const dragItem = useRef(null)
  const dragOverStage = useRef(null)

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const fetchStages = useCallback(async () => {
    const res = await fetch(`${API}/crm/stages`, { headers })
    const data = await res.json()
    setStages(data || [])
  }, [token])

  const fetchDeals = useCallback(async () => {
    const res = await fetch(`${API}/crm/deals?status=${statusFilter}`, { headers })
    const data = await res.json()
    setDeals(data || [])
  }, [token, statusFilter])

  const fetchContacts = useCallback(async () => {
    const res = await fetch(`${API}/crm/contacts?per_page=100`, { headers })
    const data = await res.json()
    setContacts(data.data || [])
  }, [token])

  useEffect(() => {
    Promise.all([fetchStages(), fetchDeals(), fetchContacts()]).finally(() => setLoading(false))
  }, [fetchStages, fetchDeals, fetchContacts])

  useEffect(() => { fetchDeals() }, [statusFilter])

  const dealsByStage = (stageId) => deals.filter(d => d.stage_id === stageId).sort((a, b) => a.posicao_kanban - b.posicao_kanban)

  const stageTotal = (stageId) => {
    const stageDeals = dealsByStage(stageId)
    return stageDeals.reduce((sum, d) => sum + (d.valor_centavos || 0), 0)
  }

  const formatCurrency = (centavos) => (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

  // Drag handlers
  const handleDragStart = (e, deal) => {
    dragItem.current = deal
    e.dataTransfer.effectAllowed = 'move'
    e.target.style.opacity = '0.5'
  }

  const handleDragEnd = (e) => {
    e.target.style.opacity = '1'
    dragItem.current = null
    dragOverStage.current = null
  }

  const handleDragOver = (e, stageId) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    dragOverStage.current = stageId
  }

  const handleDrop = async (e, stageId) => {
    e.preventDefault()
    const deal = dragItem.current
    if (!deal || deal.stage_id === stageId) return

    // Optimistic update
    setDeals(prev => prev.map(d => d.id === deal.id ? { ...d, stage_id: stageId } : d))

    try {
      await fetch(`${API}/crm/deals/${deal.id}/move`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({ stage_id: stageId, posicao_kanban: 0 }),
      })
      fetchDeals()
    } catch (err) {
      console.error('Erro ao mover deal:', err)
      fetchDeals()
    }
  }

  const handleSaveDeal = async () => {
    try {
      const body = {
        ...dealForm,
        valor_centavos: Math.round(parseFloat(dealForm.valor_centavos || 0) * 100),
        contact_id: dealForm.contact_id || null,
      }

      if (editingDeal) {
        await fetch(`${API}/crm/deals/${editingDeal.id}`, { method: 'PUT', headers, body: JSON.stringify(body) })
      } else {
        await fetch(`${API}/crm/deals`, { method: 'POST', headers, body: JSON.stringify(body) })
      }

      setShowDealModal(false)
      setEditingDeal(null)
      setDealForm({ titulo: '', contact_id: '', stage_id: '', valor_centavos: 0, notas: '' })
      fetchDeals()
    } catch (err) {
      console.error('Erro ao salvar deal:', err)
    }
  }

  const handleDeleteDeal = async (id) => {
    if (!window.confirm('Remover esta oportunidade?')) return
    await fetch(`${API}/crm/deals/${id}`, { method: 'DELETE', headers })
    fetchDeals()
  }

  const handleMarkDeal = async (deal, status) => {
    await fetch(`${API}/crm/deals/${deal.id}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ status }),
    })
    fetchDeals()
  }

  const openNewDeal = (stageId) => {
    setEditingDeal(null)
    setDealForm({ titulo: '', contact_id: '', stage_id: stageId || stages[0]?.id || '', valor_centavos: 0, notas: '' })
    setShowDealModal(true)
  }

  const openEditDeal = (deal) => {
    setEditingDeal(deal)
    setDealForm({
      titulo: deal.titulo,
      contact_id: deal.contact_id || '',
      stage_id: deal.stage_id,
      valor_centavos: (deal.valor_centavos || 0) / 100,
      notas: deal.notas || '',
    })
    setShowDealModal(true)
  }

  const totalPipeline = deals.reduce((sum, d) => sum + (d.valor_centavos || 0), 0)

  if (loading) return <div className="p-6 text-center text-gray-400">Carregando funil...</div>

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Funil de Vendas</h1>
          <p className="text-sm text-gray-500 mt-1">
            {deals.length} oportunidade{deals.length !== 1 ? 's' : ''} — Total: {formatCurrency(totalPipeline)}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="aberto">Abertos</option>
            <option value="ganho">Ganhos</option>
            <option value="perdido">Perdidos</option>
          </select>
          <button
            onClick={() => openNewDeal()}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            + Nova Oportunidade
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex gap-4 flex-1 overflow-x-auto pb-4">
        {stages.map((stage) => {
          const stageDeals = dealsByStage(stage.id)
          const total = stageTotal(stage.id)

          return (
            <div
              key={stage.id}
              className="flex-shrink-0 w-72 bg-gray-50 rounded-lg flex flex-col max-h-full"
              onDragOver={(e) => handleDragOver(e, stage.id)}
              onDrop={(e) => handleDrop(e, stage.id)}
            >
              {/* Stage header */}
              <div className="p-3 border-b border-gray-200 flex-shrink-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: stage.cor }} />
                    <h3 className="font-semibold text-sm text-gray-800">{stage.nome}</h3>
                    <span className="text-xs text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded-full">{stageDeals.length}</span>
                  </div>
                  <button onClick={() => openNewDeal(stage.id)} className="text-gray-400 hover:text-gray-600">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                  </button>
                </div>
                {total > 0 && <p className="text-xs text-gray-500 mt-1">{formatCurrency(total)}</p>}
              </div>

              {/* Cards */}
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {stageDeals.map((deal) => (
                  <div
                    key={deal.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, deal)}
                    onDragEnd={handleDragEnd}
                    className="bg-white rounded-lg border border-gray-200 p-3 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow group"
                  >
                    <div className="flex items-start justify-between">
                      <h4 className="text-sm font-medium text-gray-900 leading-snug">{deal.titulo}</h4>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 flex-shrink-0">
                        <button onClick={() => openEditDeal(deal)} className="text-gray-400 hover:text-indigo-600">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                        </button>
                      </div>
                    </div>

                    {deal.contacts && (
                      <div className="flex items-center gap-1.5 mt-2">
                        <div className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center text-xs font-bold text-indigo-600">
                          {deal.contacts.nome[0]?.toUpperCase()}
                        </div>
                        <span className="text-xs text-gray-500 truncate">{deal.contacts.nome}</span>
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-2">
                      <span className="text-sm font-semibold text-green-600">{formatCurrency(deal.valor_centavos)}</span>
                      {statusFilter === 'aberto' && (
                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => handleMarkDeal(deal, 'ganho')} title="Marcar como Ganho" className="text-green-500 hover:text-green-700">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                          </button>
                          <button onClick={() => handleMarkDeal(deal, 'perdido')} title="Marcar como Perdido" className="text-red-500 hover:text-red-700">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {stageDeals.length === 0 && (
                  <div className="text-center py-6 text-gray-300 text-xs">
                    Arraste deals aqui
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Deal Modal */}
      {showDealModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <h2 className="text-lg font-bold mb-4">{editingDeal ? 'Editar Oportunidade' : 'Nova Oportunidade'}</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Titulo *</label>
                <input type="text" value={dealForm.titulo} onChange={e => setDealForm({ ...dealForm, titulo: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Valor (R$)</label>
                  <input type="number" step="0.01" min="0" value={dealForm.valor_centavos} onChange={e => setDealForm({ ...dealForm, valor_centavos: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Etapa</label>
                  <select value={dealForm.stage_id} onChange={e => setDealForm({ ...dealForm, stage_id: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm">
                    <option value="">Selecione...</option>
                    {stages.map(s => <option key={s.id} value={s.id}>{s.nome}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contato</label>
                <select value={dealForm.contact_id} onChange={e => setDealForm({ ...dealForm, contact_id: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm">
                  <option value="">Nenhum</option>
                  {contacts.map(c => <option key={c.id} value={c.id}>{c.nome}{c.empresa ? ` — ${c.empresa}` : ''}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notas</label>
                <textarea value={dealForm.notas} onChange={e => setDealForm({ ...dealForm, notas: e.target.value })} rows={3} className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
            </div>
            <div className="flex justify-between mt-5">
              <div>
                {editingDeal && (
                  <button onClick={() => { handleDeleteDeal(editingDeal.id); setShowDealModal(false) }} className="px-4 py-2 text-sm text-red-600 hover:text-red-800">Remover</button>
                )}
              </div>
              <div className="flex gap-2">
                <button onClick={() => { setShowDealModal(false); setEditingDeal(null) }} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">Cancelar</button>
                <button onClick={handleSaveDeal} disabled={!dealForm.titulo.trim() || !dealForm.stage_id} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40">Salvar</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

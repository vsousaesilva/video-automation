import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/authStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Contacts() {
  const token = useAuthStore((s) => s.token)
  const navigate = useNavigate()

  const [contacts, setContacts] = useState([])
  const [tags, setTags] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedTag, setSelectedTag] = useState('')
  const [loading, setLoading] = useState(true)

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editingContact, setEditingContact] = useState(null)
  const [form, setForm] = useState({ nome: '', email: '', telefone: '', empresa: '', cargo: '', origem: 'manual', notas: '', tag_ids: [] })

  // Import state
  const [showImport, setShowImport] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [importing, setImporting] = useState(false)

  // Tag management
  const [showTagModal, setShowTagModal] = useState(false)
  const [tagForm, setTagForm] = useState({ nome: '', cor: '#6366f1' })

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const fetchContacts = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: page.toString(), per_page: '25' })
      if (search) params.set('search', search)
      if (selectedTag) params.set('tag_id', selectedTag)

      const res = await fetch(`${API}/crm/contacts?${params}`, { headers })
      const data = await res.json()
      setContacts(data.data || [])
      setTotal(data.total || 0)
    } catch (err) {
      console.error('Erro ao carregar contatos:', err)
    } finally {
      setLoading(false)
    }
  }, [page, search, selectedTag, token])

  const fetchTags = useCallback(async () => {
    try {
      const res = await fetch(`${API}/crm/tags`, { headers })
      const data = await res.json()
      setTags(data || [])
    } catch (err) {
      console.error('Erro ao carregar tags:', err)
    }
  }, [token])

  useEffect(() => { fetchContacts() }, [fetchContacts])
  useEffect(() => { fetchTags() }, [fetchTags])

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => { setPage(1); fetchContacts() }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const handleSave = async () => {
    try {
      const url = editingContact
        ? `${API}/crm/contacts/${editingContact.id}`
        : `${API}/crm/contacts`
      const method = editingContact ? 'PUT' : 'POST'

      await fetch(url, { method, headers, body: JSON.stringify(form) })
      setShowModal(false)
      setEditingContact(null)
      setForm({ nome: '', email: '', telefone: '', empresa: '', cargo: '', origem: 'manual', notas: '', tag_ids: [] })
      fetchContacts()
    } catch (err) {
      console.error('Erro ao salvar contato:', err)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Desativar este contato?')) return
    await fetch(`${API}/crm/contacts/${id}`, { method: 'DELETE', headers })
    fetchContacts()
  }

  const handleImport = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setImporting(true)
    setImportResult(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(`${API}/crm/contacts/import`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const result = await res.json()
      setImportResult(result)
      fetchContacts()
    } catch (err) {
      console.error('Erro na importacao:', err)
    } finally {
      setImporting(false)
    }
  }

  const handleCreateTag = async () => {
    try {
      await fetch(`${API}/crm/tags`, { method: 'POST', headers, body: JSON.stringify(tagForm) })
      setShowTagModal(false)
      setTagForm({ nome: '', cor: '#6366f1' })
      fetchTags()
    } catch (err) {
      console.error('Erro ao criar tag:', err)
    }
  }

  const handleDeleteTag = async (id) => {
    if (!window.confirm('Remover esta tag?')) return
    await fetch(`${API}/crm/tags/${id}`, { method: 'DELETE', headers })
    fetchTags()
    fetchContacts()
  }

  const openEdit = (contact) => {
    setEditingContact(contact)
    setForm({
      nome: contact.nome,
      email: contact.email || '',
      telefone: contact.telefone || '',
      empresa: contact.empresa || '',
      cargo: contact.cargo || '',
      origem: contact.origem || 'manual',
      notas: contact.notas || '',
      tag_ids: (contact.tags || []).map(t => t.id),
    })
    setShowModal(true)
  }

  const totalPages = Math.ceil(total / 25)

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contatos</h1>
          <p className="text-sm text-gray-500 mt-1">{total} contato{total !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImport(!showImport)}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Importar CSV
          </button>
          <button
            onClick={() => setShowTagModal(true)}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Gerenciar Tags
          </button>
          <button
            onClick={() => { setEditingContact(null); setForm({ nome: '', email: '', telefone: '', empresa: '', cargo: '', origem: 'manual', notas: '', tag_ids: [] }); setShowModal(true) }}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            + Novo Contato
          </button>
        </div>
      </div>

      {/* Import section */}
      {showImport && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-sm text-blue-800 mb-2">Selecione um arquivo CSV com colunas: nome, email, telefone, empresa, cargo, notas</p>
          <input type="file" accept=".csv,.xlsx,.xls" onChange={handleImport} disabled={importing} className="text-sm" />
          {importing && <p className="text-sm text-blue-600 mt-2">Importando...</p>}
          {importResult && (
            <div className="mt-3 text-sm">
              <p className="text-green-700">Criados: {importResult.criados} de {importResult.total}</p>
              {importResult.erros > 0 && <p className="text-red-600">Erros: {importResult.erros}</p>}
              {importResult.detalhes_erros?.map((e, i) => <p key={i} className="text-red-500 text-xs">{e}</p>)}
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          placeholder="Buscar por nome, email, empresa..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
        <select
          value={selectedTag}
          onChange={(e) => { setSelectedTag(e.target.value); setPage(1) }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">Todas as tags</option>
          {tags.map(t => <option key={t.id} value={t.id}>{t.nome}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Carregando...</div>
        ) : contacts.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nenhum contato encontrado</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Empresa</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tags</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Origem</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Acoes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {contacts.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/crm/contacts/${c.id}`)}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 text-sm">{c.nome}</div>
                    {c.cargo && <div className="text-xs text-gray-500">{c.cargo}</div>}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.email || '-'}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.empresa || '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {(c.tags || []).map(t => (
                        <span key={t.id} className="px-2 py-0.5 rounded-full text-xs font-medium text-white" style={{ backgroundColor: t.cor }}>
                          {t.nome}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.origem}</td>
                  <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => openEdit(c)} className="text-indigo-600 hover:text-indigo-800 text-sm mr-3">Editar</button>
                    <button onClick={() => handleDelete(c.id)} className="text-red-500 hover:text-red-700 text-sm">Desativar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 text-sm border rounded disabled:opacity-40">Anterior</button>
          <span className="text-sm text-gray-600">Pagina {page} de {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-3 py-1 text-sm border rounded disabled:opacity-40">Proxima</button>
        </div>
      )}

      {/* Contact Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">{editingContact ? 'Editar Contato' : 'Novo Contato'}</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                <input type="text" value={form.nome} onChange={e => setForm({ ...form, nome: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Telefone</label>
                  <input type="text" value={form.telefone} onChange={e => setForm({ ...form, telefone: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
                  <input type="text" value={form.empresa} onChange={e => setForm({ ...form, empresa: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Cargo</label>
                  <input type="text" value={form.cargo} onChange={e => setForm({ ...form, cargo: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Origem</label>
                <select value={form.origem} onChange={e => setForm({ ...form, origem: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-sm">
                  <option value="manual">Manual</option>
                  <option value="site">Site</option>
                  <option value="indicacao">Indicacao</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="importacao">Importacao</option>
                  <option value="outro">Outro</option>
                </select>
              </div>
              {tags.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
                  <div className="flex flex-wrap gap-2">
                    {tags.map(t => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => {
                          const ids = form.tag_ids.includes(t.id) ? form.tag_ids.filter(x => x !== t.id) : [...form.tag_ids, t.id]
                          setForm({ ...form, tag_ids: ids })
                        }}
                        className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${form.tag_ids.includes(t.id) ? 'text-white' : 'text-gray-600 bg-white'}`}
                        style={form.tag_ids.includes(t.id) ? { backgroundColor: t.cor, borderColor: t.cor } : {}}
                      >
                        {t.nome}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notas</label>
                <textarea value={form.notas} onChange={e => setForm({ ...form, notas: e.target.value })} rows={3} className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => { setShowModal(false); setEditingContact(null) }} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">Cancelar</button>
              <button onClick={handleSave} disabled={!form.nome.trim()} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40">Salvar</button>
            </div>
          </div>
        </div>
      )}

      {/* Tag Management Modal */}
      {showTagModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold mb-4">Gerenciar Tags</h2>
            <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
              {tags.length === 0 && <p className="text-sm text-gray-400">Nenhuma tag criada</p>}
              {tags.map(t => (
                <div key={t.id} className="flex items-center justify-between p-2 rounded border">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: t.cor }} />
                    <span className="text-sm">{t.nome}</span>
                  </div>
                  <button onClick={() => handleDeleteTag(t.id)} className="text-red-500 hover:text-red-700 text-xs">Remover</button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input type="text" placeholder="Nome da tag" value={tagForm.nome} onChange={e => setTagForm({ ...tagForm, nome: e.target.value })} className="flex-1 px-3 py-2 border rounded-lg text-sm" />
              <input type="color" value={tagForm.cor} onChange={e => setTagForm({ ...tagForm, cor: e.target.value })} className="w-10 h-10 rounded cursor-pointer" />
              <button onClick={handleCreateTag} disabled={!tagForm.nome.trim()} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40">Criar</button>
            </div>
            <div className="flex justify-end mt-4">
              <button onClick={() => setShowTagModal(false)} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">Fechar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

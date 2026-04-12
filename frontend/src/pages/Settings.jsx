import { useEffect, useState } from 'react'
import api from '../lib/api'
import useAuthStore from '../stores/authStore'
import MediaUploader from '../components/MediaUploader'

const TABS = [
  { key: 'account', label: 'Minha Conta' },
  { key: 'workspace', label: 'Workspace' },
  { key: 'users', label: 'Usuários' },
  { key: 'media', label: 'Banco Global' },
]

const PAPEIS = [
  { value: 'admin', label: 'Admin' },
  { value: 'editor', label: 'Editor' },
  { value: 'viewer', label: 'Viewer' },
]

export default function Settings() {
  const [tab, setTab] = useState('account')
  const user = useAuthStore(s => s.user)
  const isAdmin = user?.papel === 'admin'

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Configurações</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-6">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === 'account' && <AccountSettings />}
      {tab === 'workspace' && <WorkspaceSettings isAdmin={isAdmin} />}
      {tab === 'users' && <UsersSettings isAdmin={isAdmin} />}
      {tab === 'media' && <MediaUploader appId={null} />}
    </div>
  )
}

function AccountSettings() {
  const [profile, setProfile] = useState(null)
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [form, setForm] = useState({ senha_atual: '', nova_senha: '', confirmar_senha: '' })
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)

  useEffect(() => {
    api.get('/users/me').then(res => {
      setProfile(res.data)
      setLoadingProfile(false)
    }).catch(() => setLoadingProfile(false))
  }, [])

  const handleChangePassword = async (e) => {
    e.preventDefault()
    setFeedback(null)

    if (form.nova_senha !== form.confirmar_senha) {
      setFeedback({ type: 'error', msg: 'A nova senha e a confirmação não coincidem.' })
      return
    }

    setSaving(true)
    try {
      await api.put('/auth/change-password', {
        senha_atual: form.senha_atual,
        nova_senha: form.nova_senha,
      })
      setFeedback({ type: 'success', msg: 'Senha alterada com sucesso.' })
      setForm({ senha_atual: '', nova_senha: '', confirmar_senha: '' })
    } catch (err) {
      setFeedback({ type: 'error', msg: err.response?.data?.detail || 'Erro ao alterar senha' })
    }
    setSaving(false)
  }

  if (loadingProfile) return <p className="text-gray-500">Carregando...</p>

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Informações da conta</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">Nome</label>
            <p className="text-sm text-gray-900">{profile?.nome || '—'}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">E-mail</label>
            <p className="text-sm text-gray-900">{profile?.email || '—'}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">Papel</label>
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
              profile?.papel === 'admin' ? 'bg-indigo-100 text-indigo-700' :
              profile?.papel === 'editor' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
            }`}>{profile?.papel}</span>
          </div>
        </div>
      </div>

      <form onSubmit={handleChangePassword} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <h3 className="text-lg font-semibold text-gray-900">Alterar senha</h3>

        {feedback && (
          <div className={`p-3 rounded-lg text-sm ${
            feedback.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'
          }`}>{feedback.msg}</div>
        )}

        <div className="max-w-md space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Senha atual</label>
            <input type="password" value={form.senha_atual} onChange={e => setForm(p => ({ ...p, senha_atual: e.target.value }))}
              required minLength={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nova senha</label>
            <input type="password" value={form.nova_senha} onChange={e => setForm(p => ({ ...p, nova_senha: e.target.value }))}
              required minLength={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar nova senha</label>
            <input type="password" value={form.confirmar_senha} onChange={e => setForm(p => ({ ...p, confirmar_senha: e.target.value }))}
              required minLength={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
        </div>

        <div className="pt-4 border-t border-gray-200">
          <button type="submit" disabled={saving}
            className="px-6 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:bg-indigo-300 transition-colors">
            {saving ? 'Salvando...' : 'Alterar senha'}
          </button>
        </div>
      </form>
    </div>
  )
}

function WorkspaceSettings({ isAdmin }) {
  const [ws, setWs] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [form, setForm] = useState({
    nome: '', segmento: '', tom_voz: '', idioma: 'pt-BR',
    cor_primaria: '', cor_secundaria: '',
  })

  useEffect(() => {
    api.get('/workspaces/me').then(res => {
      setWs(res.data)
      setForm({
        nome: res.data.nome || '',
        segmento: res.data.segmento || '',
        tom_voz: res.data.tom_voz || '',
        idioma: res.data.idioma || 'pt-BR',
        cor_primaria: res.data.cor_primaria || '',
        cor_secundaria: res.data.cor_secundaria || '',
      })
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      const payload = {}
      Object.entries(form).forEach(([k, v]) => { if (v) payload[k] = v })
      const res = await api.put('/workspaces/me', payload)
      setWs(res.data)
      setFeedback({ type: 'success', msg: 'Workspace atualizado com sucesso.' })
    } catch (err) {
      setFeedback({ type: 'error', msg: err.response?.data?.detail || 'Erro ao salvar' })
    }
    setSaving(false)
  }

  if (loading) return <p className="text-gray-500">Carregando...</p>

  return (
    <form onSubmit={handleSave} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      {feedback && (
        <div className={`p-3 rounded-lg text-sm ${
          feedback.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'
        }`}>{feedback.msg}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nome do workspace</label>
          <input type="text" value={form.nome} onChange={e => setForm(p => ({ ...p, nome: e.target.value }))}
            disabled={!isAdmin} required minLength={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Segmento</label>
          <input type="text" value={form.segmento} onChange={e => setForm(p => ({ ...p, segmento: e.target.value }))}
            disabled={!isAdmin}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tom de voz padrão</label>
          <input type="text" value={form.tom_voz} onChange={e => setForm(p => ({ ...p, tom_voz: e.target.value }))}
            disabled={!isAdmin} placeholder="Ex: profissional, descontraído"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Idioma</label>
          <select value={form.idioma} onChange={e => setForm(p => ({ ...p, idioma: e.target.value }))}
            disabled={!isAdmin}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
            <option value="pt-BR">Português (Brasil)</option>
            <option value="en-US">English (US)</option>
            <option value="es-ES">Español</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cor primária</label>
          <div className="flex gap-2 items-center">
            <input type="color" value={form.cor_primaria || '#6366f1'}
              onChange={e => setForm(p => ({ ...p, cor_primaria: e.target.value }))}
              disabled={!isAdmin} className="w-10 h-10 rounded border border-gray-300 cursor-pointer" />
            <input type="text" value={form.cor_primaria} onChange={e => setForm(p => ({ ...p, cor_primaria: e.target.value }))}
              disabled={!isAdmin} placeholder="#6366f1"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cor secundária</label>
          <div className="flex gap-2 items-center">
            <input type="color" value={form.cor_secundaria || '#8b5cf6'}
              onChange={e => setForm(p => ({ ...p, cor_secundaria: e.target.value }))}
              disabled={!isAdmin} className="w-10 h-10 rounded border border-gray-300 cursor-pointer" />
            <input type="text" value={form.cor_secundaria} onChange={e => setForm(p => ({ ...p, cor_secundaria: e.target.value }))}
              disabled={!isAdmin} placeholder="#8b5cf6"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
        </div>
      </div>

      {isAdmin && (
        <div className="pt-4 border-t border-gray-200">
          <button type="submit" disabled={saving}
            className="px-6 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:bg-indigo-300 transition-colors">
            {saving ? 'Salvando...' : 'Salvar alterações'}
          </button>
        </div>
      )}

      {ws && (
        <div className="pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-400">ID: {ws.id}</p>
          <p className="text-xs text-gray-400">Criado em: {new Date(ws.criado_em).toLocaleDateString('pt-BR')}</p>
        </div>
      )}
    </form>
  )
}

function UsersSettings({ isAdmin }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showInvite, setShowInvite] = useState(false)
  const [inviteForm, setInviteForm] = useState({ nome: '', email: '', papel: 'editor' })
  const [inviting, setInviting] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const currentUser = useAuthStore(s => s.user)

  const fetchUsers = () => {
    setLoading(true)
    api.get('/users').then(res => {
      setUsers(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => { fetchUsers() }, [])

  const handleInvite = async (e) => {
    e.preventDefault()
    setInviting(true)
    setFeedback(null)
    try {
      const res = await api.post('/users/invite', inviteForm)
      setFeedback({ type: 'success', msg: `Convite criado. Link: ${res.data.invite_link}` })
      setShowInvite(false)
      setInviteForm({ nome: '', email: '', papel: 'editor' })
      fetchUsers()
    } catch (err) {
      setFeedback({ type: 'error', msg: err.response?.data?.detail || 'Erro ao convidar' })
    }
    setInviting(false)
  }

  const handleDelete = async (userId) => {
    if (!confirm('Remover este usuário?')) return
    try {
      await api.delete(`/users/${userId}`)
      fetchUsers()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao remover')
    }
  }

  const handleToggleActive = async (userId, currentlyActive) => {
    try {
      await api.put(`/users/${userId}`, { ativo: !currentlyActive })
      fetchUsers()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao alterar status')
    }
  }

  if (loading) return <p className="text-gray-500">Carregando...</p>

  return (
    <div className="space-y-4">
      {feedback && (
        <div className={`p-3 rounded-lg text-sm break-all ${
          feedback.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'
        }`}>{feedback.msg}</div>
      )}

      {isAdmin && (
        <div className="flex justify-end">
          <button onClick={() => setShowInvite(!showInvite)}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">
            + Convidar usuário
          </button>
        </div>
      )}

      {showInvite && (
        <form onSubmit={handleInvite} className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
              <input type="text" value={inviteForm.nome} onChange={e => setInviteForm(p => ({ ...p, nome: e.target.value }))}
                required minLength={2} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
              <input type="email" value={inviteForm.email} onChange={e => setInviteForm(p => ({ ...p, email: e.target.value }))}
                required className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Papel</label>
              <select value={inviteForm.papel} onChange={e => setInviteForm(p => ({ ...p, papel: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
                {PAPEIS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <button type="submit" disabled={inviting}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:bg-indigo-300 transition-colors">
              {inviting ? 'Enviando...' : 'Enviar convite'}
            </button>
            <button type="button" onClick={() => setShowInvite(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 transition-colors">
              Cancelar
            </button>
          </div>
        </form>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Nome</th>
              <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">E-mail</th>
              <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Papel</th>
              <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Status</th>
              {isAdmin && <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Ações</th>}
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-b border-gray-100">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{u.nome}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    u.papel === 'admin' ? 'bg-indigo-100 text-indigo-700' :
                    u.papel === 'editor' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                  }`}>{u.papel}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    u.ativo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}>{u.ativo ? 'Ativo' : 'Inativo'}</span>
                </td>
                {isAdmin && (
                  <td className="px-4 py-3">
                    {u.id !== currentUser?.id && (
                      <div className="flex gap-2">
                        <button onClick={() => handleToggleActive(u.id, u.ativo)}
                          className="text-xs text-indigo-600 hover:underline">
                          {u.ativo ? 'Desativar' : 'Ativar'}
                        </button>
                        <button onClick={() => handleDelete(u.id)}
                          className="text-xs text-red-600 hover:underline">Remover</button>
                      </div>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

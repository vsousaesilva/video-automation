import { useEffect, useState } from 'react'
import api from '../lib/api'

const STATUS_STYLES = {
  publicado: { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  aprovado: { bg: 'bg-green-100', text: 'text-green-700' },
  aguardando_aprovacao: { bg: 'bg-amber-100', text: 'text-amber-700' },
  rejeitado: { bg: 'bg-red-100', text: 'text-red-700' },
  erro_publicacao: { bg: 'bg-red-100', text: 'text-red-700' },
  erro_validacao: { bg: 'bg-red-100', text: 'text-red-700' },
  processando: { bg: 'bg-blue-100', text: 'text-blue-700' },
}

export default function History() {
  const [apps, setApps] = useState([])
  const [selectedAppId, setSelectedAppId] = useState('all')
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingVideos, setLoadingVideos] = useState(false)

  useEffect(() => {
    api.get('/apps').then(res => {
      setApps(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (apps.length === 0) return
    setLoadingVideos(true)

    const fetchHistory = async () => {
      const targetApps = selectedAppId === 'all' ? apps : apps.filter(a => a.id === selectedAppId)
      let allVideos = []

      for (const app of targetApps) {
        try {
          const res = await api.get(`/apps/${app.id}/history`)
          const vids = (res.data || []).map(v => ({
            ...v,
            app_nome: app.nome,
            titulo: v.conteudos?.titulo || null,
            tipo_conteudo: v.conteudos?.tipo_conteudo || null,
          }))
          allVideos = [...allVideos, ...vids]
        } catch {
          // App sem histórico
        }
      }

      allVideos.sort((a, b) => new Date(b.criado_em) - new Date(a.criado_em))
      setVideos(allVideos)
      setLoadingVideos(false)
    }

    fetchHistory()
  }, [apps, selectedAppId])

  const style = (status) => STATUS_STYLES[status] || { bg: 'bg-gray-100', text: 'text-gray-700' }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Histórico</h1>
        <select value={selectedAppId} onChange={e => setSelectedAppId(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
          <option value="all">Todos os apps</option>
          {apps.map(app => (
            <option key={app.id} value={app.id}>{app.nome}</option>
          ))}
        </select>
      </div>

      {loading || loadingVideos ? (
        <p className="text-gray-500">Carregando...</p>
      ) : videos.length === 0 ? (
        <div className="text-center py-12 text-gray-400">Nenhum vídeo no histórico.</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">App</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Título</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Tipo</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Status</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Formatos</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Links</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Data</th>
              </tr>
            </thead>
            <tbody>
              {videos.map(video => {
                const s = style(video.status)
                return (
                  <tr key={video.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{video.app_nome}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 max-w-[200px] truncate">
                      {video.titulo || '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{video.tipo_conteudo || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${s.bg} ${s.text}`}>
                        {video.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        {video.url_storage_vertical && (
                          <span className="px-1.5 py-0.5 text-[10px] bg-purple-100 text-purple-600 rounded">9:16</span>
                        )}
                        {video.url_storage_horizontal && (
                          <span className="px-1.5 py-0.5 text-[10px] bg-blue-100 text-blue-600 rounded">16:9</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        {video.url_youtube && (
                          <a href={video.url_youtube} target="_blank" rel="noopener noreferrer"
                            className="text-xs text-red-600 hover:underline">YouTube</a>
                        )}
                        {video.url_instagram && (
                          <a href={video.url_instagram} target="_blank" rel="noopener noreferrer"
                            className="text-xs text-pink-600 hover:underline">Instagram</a>
                        )}
                        {!video.url_youtube && !video.url_instagram && (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(video.criado_em).toLocaleDateString('pt-BR')}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

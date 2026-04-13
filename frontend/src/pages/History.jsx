import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'

const STATUS_STYLES = {
  publicado: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Publicado' },
  aprovado: { bg: 'bg-green-100', text: 'text-green-700', label: 'Aprovado' },
  aguardando_aprovacao: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Aguardando Aprovação' },
  rejeitado: { bg: 'bg-red-100', text: 'text-red-700', label: 'Rejeitado' },
  erro_publicacao: { bg: 'bg-red-100', text: 'text-red-700', label: 'Erro Publicação' },
  erro_validacao: { bg: 'bg-red-100', text: 'text-red-700', label: 'Erro Validação' },
  processando: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Processando' },
  erro: { bg: 'bg-red-100', text: 'text-red-700', label: 'Erro' },
}

const PIPELINE_STYLES = {
  gerado: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Conteúdo Gerado', icon: '1' },
  em_producao: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Construindo Vídeo', icon: '2' },
  erro: { bg: 'bg-red-100', text: 'text-red-700', label: 'Erro', icon: '!' },
}

export default function History() {
  const [negocios, setNegocios] = useState([])
  const [selectedNegocioId, setSelectedNegocioId] = useState('all')
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingVideos, setLoadingVideos] = useState(false)

  // Pipeline: conteudos em andamento
  const [pipeline, setPipeline] = useState([])
  const [loadingPipeline, setLoadingPipeline] = useState(true)

  const navigate = useNavigate()

  useEffect(() => {
    api.get('/negocios').then(res => {
      setNegocios(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  // Buscar conteudos em pipeline (gerado, em_producao, erro)
  useEffect(() => {
    setLoadingPipeline(true)
    api.get('/conteudos', { params: { limit: 50 } })
      .then(res => {
        const inPipeline = (res.data || []).filter(c =>
          ['gerado', 'em_producao', 'erro'].includes(c.status)
        )
        setPipeline(inPipeline)
      })
      .catch(() => setPipeline([]))
      .finally(() => setLoadingPipeline(false))
  }, [])

  // Buscar historico de videos
  useEffect(() => {
    if (negocios.length === 0) return
    setLoadingVideos(true)

    const fetchHistory = async () => {
      const targetNegocios = selectedNegocioId === 'all' ? negocios : negocios.filter(n => n.id === selectedNegocioId)
      let allVideos = []

      for (const negocio of targetNegocios) {
        try {
          const res = await api.get(`/negocios/${negocio.id}/history`)
          const vids = (res.data || []).map(v => ({
            ...v,
            negocio_nome: negocio.nome,
            titulo: v.conteudos?.titulo || null,
            tipo_conteudo: v.conteudos?.tipo_conteudo || null,
          }))
          allVideos = [...allVideos, ...vids]
        } catch {
          // Negocio sem historico
        }
      }

      allVideos.sort((a, b) => new Date(b.criado_em) - new Date(a.criado_em))
      setVideos(allVideos)
      setLoadingVideos(false)
    }

    fetchHistory()
  }, [negocios, selectedNegocioId])

  const style = (status) => STATUS_STYLES[status] || { bg: 'bg-gray-100', text: 'text-gray-700', label: status }
  const getNegocioNome = (negocioId) => negocios.find(n => n.id === negocioId)?.nome || negocioId?.slice(0, 8) + '...'

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Histórico</h1>
        <select value={selectedNegocioId} onChange={e => setSelectedNegocioId(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
          <option value="all">Todos os negócios</option>
          {negocios.map(n => (
            <option key={n.id} value={n.id}>{n.nome}</option>
          ))}
        </select>
      </div>

      {/* Pipeline em andamento */}
      {!loadingPipeline && pipeline.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-500 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" />
            </svg>
            Pipeline em Andamento ({pipeline.length})
          </h2>
          <div className="space-y-2">
            {pipeline.map(conteudo => {
              const ps = PIPELINE_STYLES[conteudo.status] || PIPELINE_STYLES.gerado
              return (
                <div key={conteudo.id} className="bg-white rounded-lg border border-gray-200 p-4 flex items-center gap-4">
                  {/* Step indicator */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${ps.bg} ${ps.text}`}>
                    {conteudo.status === 'em_producao' ? (
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    ) : ps.icon}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">
                        {conteudo.titulo || 'Conteúdo ' + conteudo.id.slice(0, 8)}
                      </span>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${ps.bg} ${ps.text}`}>
                        {ps.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{getNegocioNome(conteudo.negocio_id)}</span>
                      <span>{conteudo.tipo_conteudo || '—'}</span>
                      <span>{new Date(conteudo.criado_em).toLocaleString('pt-BR')}</span>
                    </div>
                    {conteudo.status === 'erro' && conteudo.erro_msg && (
                      <p className="text-xs text-red-500 mt-1 truncate">{conteudo.erro_msg}</p>
                    )}
                  </div>

                  {/* Action */}
                  {conteudo.status === 'em_producao' && (
                    <span className="text-xs text-blue-500">Gerando TTS, mídia e vídeo...</span>
                  )}
                  {conteudo.status === 'gerado' && (
                    <span className="text-xs text-gray-400">Aguardando construção do vídeo</span>
                  )}
                  {conteudo.status === 'aguardando_aprovacao' && (
                    <button
                      onClick={() => navigate('/approvals')}
                      className="text-xs text-amber-600 hover:text-amber-800 font-medium"
                    >
                      Revisar
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Historico de videos */}
      {loading || loadingVideos ? (
        <p className="text-gray-500">Carregando...</p>
      ) : videos.length === 0 && pipeline.length === 0 ? (
        <div className="text-center py-12 text-gray-400">Nenhum vídeo no histórico.</div>
      ) : videos.length === 0 ? null : (
        <>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Vídeos Concluídos</h2>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Negócio</th>
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
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{video.negocio_nome}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 max-w-[200px] truncate">
                        {video.titulo || '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{video.tipo_conteudo || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${s.bg} ${s.text}`}>
                          {s.label}
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
        </>
      )}
    </div>
  )
}

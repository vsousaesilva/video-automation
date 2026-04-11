import { useEffect, useState } from 'react'
import api from '../lib/api'
import DualVideoPreview from '../components/DualVideoPreview'
import useDashboardStore from '../stores/dashboardStore'

export default function Approvals() {
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedVideo, setSelectedVideo] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [actionLoading, setActionLoading] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [rejectMotivo, setRejectMotivo] = useState('')
  const [showRejectModal, setShowRejectModal] = useState(false)

  // Campos editáveis de metadados
  const [editTitle, setEditTitle] = useState('')
  const [editDescYt, setEditDescYt] = useState('')
  const [editDescIg, setEditDescIg] = useState('')
  const [editHashtagsYt, setEditHashtagsYt] = useState('')
  const [editHashtagsIg, setEditHashtagsIg] = useState('')

  const fetchPendingVideos = useDashboardStore((s) => s.fetchPendingVideos)

  const fetchVideos = () => {
    setLoading(true)
    api.get('/videos/pending').then(res => {
      setVideos(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => { fetchVideos() }, [])

  const openDetail = async (video) => {
    setSelectedVideo(video)
    setLoadingDetail(true)
    setFeedback(null)
    try {
      const res = await api.get(`/videos/${video.id}`)
      setDetail(res.data)
      const c = res.data.conteudo
      if (c) {
        setEditTitle(c.titulo || '')
        setEditDescYt(c.descricao_youtube || '')
        setEditDescIg(c.descricao_instagram || '')
        setEditHashtagsYt((c.hashtags_youtube || []).join(', '))
        setEditHashtagsIg((c.hashtags_instagram || []).join(', '))
      }
    } catch {
      setDetail(null)
    }
    setLoadingDetail(false)
  }

  const handleApprove = async () => {
    setActionLoading('approve')
    try {
      const res = await api.post(`/approvals/${selectedVideo.id}/approve`)
      setFeedback({ type: 'success', message: res.data.message })
      fetchVideos()
      fetchPendingVideos()
    } catch (err) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Erro ao aprovar' })
    }
    setActionLoading(null)
  }

  const handleReject = async () => {
    if (!rejectMotivo.trim()) return
    setActionLoading('reject')
    try {
      const res = await api.post(`/approvals/${selectedVideo.id}/reject`, { motivo: rejectMotivo })
      setFeedback({ type: 'success', message: res.data.message })
      setShowRejectModal(false)
      setRejectMotivo('')
      fetchVideos()
      fetchPendingVideos()
    } catch (err) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Erro ao rejeitar' })
    }
    setActionLoading(null)
  }

  const handleRegenerate = async () => {
    if (!confirm('Descartar este vídeo e gerar novo conteúdo?')) return
    setActionLoading('regenerate')
    try {
      const res = await api.post(`/approvals/${selectedVideo.id}/regenerate`)
      setFeedback({ type: 'success', message: res.data.message })
      fetchVideos()
      fetchPendingVideos()
    } catch (err) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Erro ao regenerar' })
    }
    setActionLoading(null)
  }

  // --- Detail view ---
  if (selectedVideo) {
    const isActioned = feedback?.type === 'success'

    return (
      <div className="p-6 max-w-7xl mx-auto">
        <button onClick={() => { setSelectedVideo(null); setDetail(null); setFeedback(null) }}
          className="text-sm text-indigo-600 hover:underline mb-4 flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          Voltar para fila
        </button>

        {/* Feedback */}
        {feedback && (
          <div className={`mb-4 p-4 rounded-lg text-sm ${
            feedback.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'
          }`}>
            {feedback.message}
          </div>
        )}

        {loadingDetail ? (
          <p className="text-gray-500">Carregando detalhes...</p>
        ) : !detail ? (
          <p className="text-gray-500">Erro ao carregar detalhes do vídeo.</p>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900">
                {detail.app_nome || 'Vídeo'} — Aprovação
              </h1>
              <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-700">
                {detail.status === 'aguardando_aprovacao' ? 'Aguardando' : detail.status}
              </span>
            </div>

            {/* Video preview */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-700 mb-4">Preview dos Vídeos</h2>
              <DualVideoPreview
                verticalUrl={detail.url_storage_vertical}
                horizontalUrl={detail.url_storage_horizontal}
              />
            </div>

            {/* Content details */}
            {detail.conteudo && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Roteiro */}
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h2 className="text-sm font-semibold text-gray-700 mb-3">Roteiro</h2>
                  <div className="text-sm text-gray-600 whitespace-pre-wrap max-h-80 overflow-y-auto">
                    {detail.conteudo.roteiro || 'Sem roteiro disponível.'}
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <span className="text-xs text-gray-400">
                      Tipo: {detail.conteudo.tipo_conteudo || '—'}
                    </span>
                  </div>
                </div>

                {/* Metadados editáveis */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
                  <h2 className="text-sm font-semibold text-gray-700 mb-1">Metadados</h2>

                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Título</label>
                    <input type="text" value={editTitle} onChange={e => setEditTitle(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Descrição YouTube</label>
                    <textarea value={editDescYt} onChange={e => setEditDescYt(e.target.value)}
                      rows={3} className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Descrição Instagram</label>
                    <textarea value={editDescIg} onChange={e => setEditDescIg(e.target.value)}
                      rows={3} className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Hashtags YouTube (separadas por vírgula)</label>
                    <input type="text" value={editHashtagsYt} onChange={e => setEditHashtagsYt(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Hashtags Instagram (separadas por vírgula)</label>
                    <input type="text" value={editHashtagsIg} onChange={e => setEditHashtagsIg(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
                  </div>
                </div>
              </div>
            )}

            {/* Action buttons */}
            {!isActioned && detail.status === 'aguardando_aprovacao' && (
              <div className="flex gap-3">
                <button onClick={handleApprove} disabled={!!actionLoading}
                  className="px-6 py-2.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:bg-green-300 disabled:cursor-not-allowed transition-colors">
                  {actionLoading === 'approve' ? 'Aprovando...' : 'Aprovar e Publicar'}
                </button>
                <button onClick={() => setShowRejectModal(true)} disabled={!!actionLoading}
                  className="px-6 py-2.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:bg-red-300 disabled:cursor-not-allowed transition-colors">
                  Rejeitar
                </button>
                <button onClick={handleRegenerate} disabled={!!actionLoading}
                  className="px-6 py-2.5 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 disabled:bg-amber-300 disabled:cursor-not-allowed transition-colors">
                  {actionLoading === 'regenerate' ? 'Regenerando...' : 'Regenerar'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Reject modal */}
        {showRejectModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Rejeitar Vídeo</h3>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo da rejeição *</label>
                <textarea value={rejectMotivo} onChange={e => setRejectMotivo(e.target.value)}
                  rows={3} placeholder="Descreva o motivo..."
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
              </div>
              <div className="flex gap-3">
                <button onClick={handleReject} disabled={!rejectMotivo.trim() || actionLoading === 'reject'}
                  className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:bg-red-300 disabled:cursor-not-allowed">
                  {actionLoading === 'reject' ? 'Rejeitando...' : 'Confirmar Rejeição'}
                </button>
                <button onClick={() => { setShowRejectModal(false); setRejectMotivo('') }}
                  className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  // --- Video list ---
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Fila de Aprovação</h1>

      {loading ? (
        <p className="text-gray-500">Carregando...</p>
      ) : videos.length === 0 ? (
        <div className="text-center py-12 text-gray-400">Nenhum vídeo aguardando aprovação.</div>
      ) : (
        <div className="space-y-3">
          {videos.map(video => (
            <div key={video.id}
              onClick={() => openDetail(video)}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow cursor-pointer">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900">Vídeo {video.id.slice(0, 8)}...</p>
                  <div className="flex gap-4 mt-1 text-sm text-gray-500">
                    <span>App: {video.app_id.slice(0, 8)}...</span>
                    <span>Criado: {new Date(video.criado_em).toLocaleString('pt-BR')}</span>
                  </div>
                  <div className="flex gap-3 mt-2">
                    {video.url_storage_vertical && (
                      <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">Vertical</span>
                    )}
                    {video.url_storage_horizontal && (
                      <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">Horizontal</span>
                    )}
                    {video.duracao_vertical_segundos && (
                      <span className="text-xs text-gray-400">{video.duracao_vertical_segundos}s</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1 text-sm font-medium rounded-full bg-amber-100 text-amber-700">Aguardando</span>
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

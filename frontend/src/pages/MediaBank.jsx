import { useEffect, useState, useRef } from 'react'
import api from '../lib/api'

export default function MediaBank() {
  const [negocios, setNegocios] = useState([])
  const [selectedNegocioId, setSelectedNegocioId] = useState('all')
  const [media, setMedia] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [tags, setTags] = useState('')
  const fileInputRef = useRef(null)

  useEffect(() => {
    api.get('/negocios').then(res => {
      setNegocios(res.data)
    })
  }, [])

  const fetchMedia = () => {
    setLoading(true)
    const params = {}
    if (selectedNegocioId !== 'all') params.negocio_id = selectedNegocioId
    api.get('/media', { params })
      .then(res => setMedia(res.data))
      .catch(() => setMedia([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchMedia() }, [selectedNegocioId])

  const handleUpload = async (e) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    setFeedback(null)
    let successCount = 0
    let errorCount = 0

    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      if (selectedNegocioId !== 'all') {
        formData.append('negocio_id', selectedNegocioId)
      }
      if (tags.trim()) {
        const tagArray = tags.split(',').map(t => t.trim()).filter(Boolean)
        formData.append('tags', JSON.stringify(tagArray))
      }

      try {
        await api.post('/media/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        successCount++
      } catch {
        errorCount++
      }
    }

    setUploading(false)
    if (fileInputRef.current) fileInputRef.current.value = ''

    if (errorCount > 0) {
      setFeedback({ type: 'error', message: `${successCount} enviado(s), ${errorCount} erro(s)` })
    } else {
      setFeedback({ type: 'success', message: `${successCount} arquivo(s) enviado(s) com sucesso` })
    }
    fetchMedia()
  }

  const handleDelete = async (id) => {
    if (!confirm('Remover este arquivo?')) return
    try {
      await api.delete(`/media/${id}`)
      setMedia(prev => prev.filter(m => m.id !== id))
    } catch {
      setFeedback({ type: 'error', message: 'Erro ao remover' })
    }
  }

  const getNegocioNome = (id) => negocios.find(n => n.id === id)?.nome || 'Workspace'

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Banco de Midia</h1>
        <select value={selectedNegocioId} onChange={e => setSelectedNegocioId(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
          <option value="all">Todos os negocios</option>
          {negocios.map(n => (
            <option key={n.id} value={n.id}>{n.nome}</option>
          ))}
        </select>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className={`mb-4 p-3 rounded-lg text-sm ${
          feedback.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          {feedback.message}
        </div>
      )}

      {/* Upload area */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Enviar Arquivos</h2>
        {selectedNegocioId === 'all' && (
          <p className="text-xs text-amber-600 mb-3">Selecione um negocio acima para associar os arquivos a ele.</p>
        )}
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">Tags (separadas por virgula, opcional)</label>
            <input type="text" value={tags} onChange={e => setTags(e.target.value)}
              placeholder="produto, logo, cenario..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,video/*"
              onChange={handleUpload}
              className="hidden"
              id="media-upload"
            />
            <label htmlFor="media-upload"
              className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg cursor-pointer transition-colors ${
                uploading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              {uploading ? 'Enviando...' : 'Selecionar Arquivos'}
            </label>
          </div>
        </div>
      </div>

      {/* Media grid */}
      {loading ? (
        <p className="text-gray-500">Carregando...</p>
      ) : media.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p>Nenhuma midia cadastrada.</p>
          <p className="text-sm mt-1">Envie imagens ou videos usando o botao acima.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {media.map(item => (
            <div key={item.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden group relative">
              {/* Thumbnail */}
              <div className="aspect-square bg-gray-100 flex items-center justify-center overflow-hidden">
                {item.tipo === 'imagem' ? (
                  <img src={item.url_storage} alt={item.nome} className="w-full h-full object-cover" />
                ) : (
                  <div className="flex flex-col items-center text-gray-400">
                    <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs mt-1">Video</span>
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="p-2">
                <p className="text-xs font-medium text-gray-700 truncate">{item.nome}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-gray-400">
                    {item.negocio_id ? getNegocioNome(item.negocio_id) : 'Workspace'}
                  </span>
                  <span className={`px-1.5 py-0.5 text-[10px] rounded ${
                    item.tipo === 'imagem' ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'
                  }`}>
                    {item.tipo}
                  </span>
                </div>
                {item.tags && item.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {item.tags.slice(0, 3).map((tag, i) => (
                      <span key={i} className="px-1 py-0.5 text-[10px] bg-gray-100 text-gray-500 rounded">{tag}</span>
                    ))}
                    {item.tags.length > 3 && (
                      <span className="text-[10px] text-gray-400">+{item.tags.length - 3}</span>
                    )}
                  </div>
                )}
              </div>

              {/* Delete button */}
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(item.id) }}
                className="absolute top-2 right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-xs"
                title="Remover"
              >
                X
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      {!loading && media.length > 0 && (
        <div className="mt-4 text-xs text-gray-400 text-right">
          {media.length} arquivo(s) &middot; {media.filter(m => m.tipo === 'imagem').length} imagens &middot; {media.filter(m => m.tipo === 'video').length} videos
        </div>
      )}
    </div>
  )
}

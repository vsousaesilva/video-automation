import { useCallback, useEffect, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import api from '../lib/api'

const TAG_SUGGESTIONS = ['produto', 'screenshot', 'lifestyle', 'resultado', 'icone', 'banner', 'marketing', 'tutorial']

export default function MediaUploader({ negocioId }) {
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [selectedTags, setSelectedTags] = useState([])
  const [customTag, setCustomTag] = useState('')

  const fetchAssets = useCallback(() => {
    setLoading(true)
    const url = negocioId ? `/media/negocio/${negocioId}` : '/media?apenas_workspace=true'
    api.get(url).then(res => {
      setAssets(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [negocioId])

  useEffect(() => { fetchAssets() }, [fetchAssets])

  const onDrop = useCallback(async (acceptedFiles) => {
    for (const file of acceptedFiles) {
      setUploading(true)
      setUploadProgress(0)

      const formData = new FormData()
      formData.append('file', file)
      if (negocioId) formData.append('negocio_id', negocioId)
      if (selectedTags.length) formData.append('tags', JSON.stringify(selectedTags))

      try {
        await api.post('/media/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (e) => {
            if (e.total) setUploadProgress(Math.round((e.loaded / e.total) * 100))
          },
        })
        fetchAssets()
      } catch (err) {
        alert(err.response?.data?.detail || 'Erro ao fazer upload')
      } finally {
        setUploading(false)
        setUploadProgress(0)
      }
    }
  }, [negocioId, selectedTags, fetchAssets])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
      'video/mp4': ['.mp4'],
    },
    maxSize: 100 * 1024 * 1024,
    disabled: uploading,
  })

  const toggleTag = (tag) => {
    setSelectedTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag])
  }

  const addCustomTag = () => {
    const tag = customTag.trim().toLowerCase()
    if (tag && !selectedTags.includes(tag)) {
      setSelectedTags(prev => [...prev, tag])
    }
    setCustomTag('')
  }

  const handleDelete = async (assetId) => {
    if (!confirm('Remover este arquivo?')) return
    try {
      await api.delete(`/media/${assetId}`)
      fetchAssets()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao remover')
    }
  }

  return (
    <div className="space-y-6">
      {/* Tags selection */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Tags para novos uploads</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {TAG_SUGGESTIONS.map(tag => (
            <button key={tag} type="button" onClick={() => toggleTag(tag)}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                selectedTags.includes(tag) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
              }`}>
              {tag}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input type="text" value={customTag} onChange={e => setCustomTag(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCustomTag() } }}
            placeholder="Adicionar tag personalizada..."
            className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          <button type="button" onClick={addCustomTag} className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
            Adicionar
          </button>
        </div>
        {selectedTags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {selectedTags.map(tag => (
              <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-indigo-100 text-indigo-700 rounded-full">
                {tag}
                <button onClick={() => toggleTag(tag)} className="hover:text-indigo-900">&times;</button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Dropzone */}
      <div {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-indigo-400 bg-indigo-50' : uploading ? 'border-gray-200 bg-gray-50 cursor-not-allowed' : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
        }`}>
        <input {...getInputProps()} />
        {uploading ? (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Enviando arquivo...</p>
            <div className="w-full max-w-xs mx-auto bg-gray-200 rounded-full h-2.5">
              <div className="bg-indigo-600 h-2.5 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
            </div>
            <p className="text-xs text-gray-500">{uploadProgress}%</p>
          </div>
        ) : (
          <div>
            <svg className="w-10 h-10 mx-auto text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm text-gray-600">
              {isDragActive ? 'Solte os arquivos aqui...' : 'Arraste imagens ou vídeos ou clique para selecionar'}
            </p>
            <p className="text-xs text-gray-400 mt-1">JPG, PNG, WebP, MP4 — máximo 100MB</p>
          </div>
        )}
      </div>

      {/* Assets grid */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-3">
          Arquivos {loading ? '...' : `(${assets.length})`}
        </h3>
        {!loading && assets.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">Nenhum arquivo no banco de imagens.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {assets.map(asset => (
              <div key={asset.id} className="group relative bg-white rounded-lg border border-gray-200 overflow-hidden">
                {/* Thumbnail */}
                <div className="aspect-square bg-gray-100 flex items-center justify-center">
                  {asset.tipo === 'imagem' ? (
                    <img src={asset.url_storage} alt={asset.nome} className="w-full h-full object-cover" />
                  ) : (
                    <div className="text-center p-2">
                      <svg className="w-8 h-8 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-xs text-gray-400 mt-1">Vídeo</p>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-2">
                  <p className="text-xs text-gray-700 truncate">{asset.nome}</p>
                  {asset.tags && asset.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {asset.tags.map(tag => (
                        <span key={tag} className="px-1.5 py-0.5 text-[10px] bg-gray-100 text-gray-500 rounded">{tag}</span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Delete button */}
                <button onClick={() => handleDelete(asset.id)}
                  className="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  &times;
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

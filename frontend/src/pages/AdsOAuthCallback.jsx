import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import api from '../lib/api'

export default function AdsOAuthCallback() {
  const { plataforma } = useParams()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState('Processando autorização...')
  const [error, setError] = useState('')
  const [externalId, setExternalId] = useState('')

  const code = params.get('code')
  const redirect_uri = `${window.location.origin}/ads/oauth/${plataforma || ''}/callback`

  useEffect(() => {
    if (!code) {
      setError('Código de autorização não encontrado na URL.')
      return
    }
  }, [code])

  async function finalize(e) {
    e?.preventDefault()
    setStatus('Finalizando vinculação...')
    try {
      await api.post(`/ads/oauth/${plataforma}/callback`, null, {
        params: { code, redirect_uri, external_id: externalId || undefined },
      })
      setStatus('Conta vinculada com sucesso. Redirecionando...')
      setTimeout(() => navigate('/ads'), 1200)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
      setStatus('')
    }
  }

  const needsExternal = plataforma !== 'tiktok'

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="bg-white rounded shadow p-6 max-w-md w-full">
        <h1 className="text-xl font-bold mb-2">OAuth {plataforma?.toUpperCase()}</h1>
        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
        {!error && status && <p className="text-gray-600 text-sm mb-4">{status}</p>}
        {code && needsExternal && !error && (
          <form onSubmit={finalize} className="space-y-3">
            <label className="block text-sm">
              ID da conta {plataforma === 'meta' ? '(act_...)' : '(customer_id)'}
              <input
                required
                value={externalId}
                onChange={(e) => setExternalId(e.target.value)}
                className="mt-1 w-full border rounded px-3 py-2 text-sm"
                placeholder={plataforma === 'meta' ? 'act_1234567890' : '1234567890'}
              />
            </label>
            <button
              type="submit"
              className="w-full px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm"
            >
              Vincular conta
            </button>
          </form>
        )}
        {code && !needsExternal && !error && (
          <button
            onClick={finalize}
            className="w-full px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm"
          >
            Finalizar vinculação
          </button>
        )}
      </div>
    </div>
  )
}

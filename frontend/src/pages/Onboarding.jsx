import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import useAuthStore from '../stores/authStore'

const STEPS = [
  { title: 'Dados do Workspace', description: 'Configure seu espaço de trabalho' },
  { title: 'Integrações', description: 'Conecte suas plataformas' },
  { title: 'Primeiro Negócio', description: 'Crie seu primeiro negócio' },
]

export default function Onboarding() {
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  // Step 1: Workspace data
  const [workspace, setWorkspace] = useState({
    nome: '',
    telefone: '',
    segmento: '',
  })

  // Step 2: Integrations (optional)
  const [integrations, setIntegrations] = useState({
    youtube_refresh_token: '',
    meta_access_token: '',
    meta_instagram_account_id: '',
    telegram_chat_id: '',
  })

  // Step 3: First negocio
  const [negocio, setNegocio] = useState({
    nome: '',
    descricao: '',
    tom_de_voz: 'profissional',
    plataformas: ['youtube'],
    formato_youtube: '9_16',
    idioma: 'pt-BR',
    horario_postagem: '10:00',
    frequencia_semanal: 3,
  })

  const handleWorkspaceChange = (e) => {
    setWorkspace((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleIntegrationChange = (e) => {
    setIntegrations((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleNegocioChange = (e) => {
    const { name, value, type } = e.target
    setNegocio((prev) => ({
      ...prev,
      [name]: type === 'number' ? parseInt(value) || 0 : value,
    }))
  }

  const togglePlataforma = (plat) => {
    setNegocio((prev) => ({
      ...prev,
      plataformas: prev.plataformas.includes(plat)
        ? prev.plataformas.filter((p) => p !== plat)
        : [...prev.plataformas, plat],
    }))
  }

  const handleNext = () => {
    setError(null)
    setStep((s) => s + 1)
  }

  const handleBack = () => {
    setError(null)
    setStep((s) => s - 1)
  }

  const handleFinish = async () => {
    setLoading(true)
    setError(null)

    try {
      // 1. Update workspace
      const wsPayload = { ...workspace }
      // Add integrations that have values
      Object.entries(integrations).forEach(([key, value]) => {
        if (value.trim()) wsPayload[key] = value.trim()
      })
      await api.put('/workspaces/me', wsPayload)

      // 2. Create first negocio
      await api.post('/negocios', negocio)

      // 3. Mark onboarding as complete
      await api.put('/workspaces/me', { onboarding_completed: true })

      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao finalizar onboarding')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 px-4 py-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Bem-vindo à Usina do Tempo</h1>
          <p className="text-gray-400 mt-2">Vamos configurar tudo em 3 passos rápidos</p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  i < step
                    ? 'bg-green-600 text-white'
                    : i === step
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {i < step ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <span className={`text-sm hidden sm:inline ${i === step ? 'text-white' : 'text-gray-500'}`}>
                {s.title}
              </span>
              {i < STEPS.length - 1 && <div className="w-8 h-px bg-gray-700" />}
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Step Content */}
        <div className="bg-gray-800 rounded-xl p-8 shadow-xl">
          {step === 0 && (
            <StepWorkspace values={workspace} onChange={handleWorkspaceChange} />
          )}
          {step === 1 && (
            <StepIntegrations values={integrations} onChange={handleIntegrationChange} />
          )}
          {step === 2 && (
            <StepNegocio
              values={negocio}
              onChange={handleNegocioChange}
              togglePlataforma={togglePlataforma}
            />
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between mt-6">
          <button
            onClick={handleBack}
            disabled={step === 0}
            className="px-6 py-2 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Voltar
          </button>

          {step < STEPS.length - 1 ? (
            <button
              onClick={handleNext}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
            >
              Próximo
            </button>
          ) : (
            <button
              onClick={handleFinish}
              disabled={loading}
              className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
            >
              {loading ? 'Finalizando...' : 'Finalizar e começar'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/* --- Step Components --- */

function StepWorkspace({ values, onChange }) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white mb-2">Dados do Workspace</h2>
      <p className="text-gray-400 text-sm mb-4">
        Essas informações ajudam a personalizar sua experiência.
      </p>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">Nome do workspace</label>
        <input
          name="nome"
          type="text"
          value={values.nome}
          onChange={onChange}
          placeholder="Minha Empresa"
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">Telefone (opcional)</label>
        <input
          name="telefone"
          type="text"
          value={values.telefone}
          onChange={onChange}
          placeholder="(85) 99999-9999"
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">Segmento</label>
        <select
          name="segmento"
          value={values.segmento}
          onChange={onChange}
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
        >
          <option value="">Selecione...</option>
          <option value="saude">Saúde e Bem-estar</option>
          <option value="educacao">Educação</option>
          <option value="tecnologia">Tecnologia</option>
          <option value="ecommerce">E-commerce</option>
          <option value="servicos">Serviços</option>
          <option value="alimentacao">Alimentação</option>
          <option value="moda">Moda</option>
          <option value="imobiliario">Imobiliário</option>
          <option value="financeiro">Financeiro</option>
          <option value="outro">Outro</option>
        </select>
      </div>
    </div>
  )
}

function StepIntegrations({ values, onChange }) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white mb-2">Integrações</h2>
      <p className="text-gray-400 text-sm mb-4">
        Configure suas integrações agora ou pule e faça depois em Configurações.
        Todos os campos são opcionais.
      </p>

      <div className="p-4 bg-gray-700/50 rounded-lg border border-gray-600">
        <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <YoutubeIcon /> YouTube
        </h3>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Refresh Token</label>
          <input
            name="youtube_refresh_token"
            type="text"
            value={values.youtube_refresh_token}
            onChange={onChange}
            placeholder="Cole aqui o refresh token do YouTube"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
        </div>
      </div>

      <div className="p-4 bg-gray-700/50 rounded-lg border border-gray-600">
        <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <InstagramIcon /> Instagram
        </h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Access Token (Meta)</label>
            <input
              name="meta_access_token"
              type="text"
              value={values.meta_access_token}
              onChange={onChange}
              placeholder="Access token da Meta Graph API"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Instagram Account ID</label>
            <input
              name="meta_instagram_account_id"
              type="text"
              value={values.meta_instagram_account_id}
              onChange={onChange}
              placeholder="ID da conta do Instagram"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            />
          </div>
        </div>
      </div>

      <div className="p-4 bg-gray-700/50 rounded-lg border border-gray-600">
        <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <TelegramIcon /> Telegram
        </h3>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Chat ID</label>
          <input
            name="telegram_chat_id"
            type="text"
            value={values.telegram_chat_id}
            onChange={onChange}
            placeholder="ID do chat do Telegram"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
        </div>
      </div>
    </div>
  )
}

function StepNegocio({ values, onChange, togglePlataforma }) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white mb-2">Primeiro Negócio</h2>
      <p className="text-gray-400 text-sm mb-4">
        Configure o negócio que terá vídeos gerados automaticamente.
      </p>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">Nome do negócio</label>
        <input
          name="nome"
          type="text"
          value={values.nome}
          onChange={onChange}
          required
          placeholder="Ex: Minha Clínica, Minha Loja..."
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">Descrição breve</label>
        <textarea
          name="descricao"
          value={values.descricao}
          onChange={onChange}
          rows={2}
          placeholder="Sobre o que é o negócio, público-alvo, diferenciais..."
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition resize-none"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Tom de voz</label>
          <select
            name="tom_de_voz"
            value={values.tom_de_voz}
            onChange={onChange}
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          >
            <option value="profissional">Profissional</option>
            <option value="casual">Casual</option>
            <option value="humoristico">Humorístico</option>
            <option value="tecnico">Técnico</option>
            <option value="inspirador">Inspirador</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Idioma</label>
          <select
            name="idioma"
            value={values.idioma}
            onChange={onChange}
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          >
            <option value="pt-BR">Português (BR)</option>
            <option value="en-US">Inglês (US)</option>
            <option value="es-ES">Espanhol</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Plataformas</label>
        <div className="flex gap-3">
          {['youtube', 'instagram'].map((plat) => (
            <button
              key={plat}
              type="button"
              onClick={() => togglePlataforma(plat)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition ${
                values.plataformas.includes(plat)
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-gray-700 border-gray-600 text-gray-400 hover:border-gray-500'
              }`}
            >
              {plat === 'youtube' ? <YoutubeIcon /> : <InstagramIcon />}
              <span className="capitalize">{plat}</span>
            </button>
          ))}
        </div>
      </div>

      {values.plataformas.includes('youtube') && (
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Formato YouTube</label>
          <select
            name="formato_youtube"
            value={values.formato_youtube}
            onChange={onChange}
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          >
            <option value="9_16">Vertical (9:16 - Shorts)</option>
            <option value="16_9">Horizontal (16:9)</option>
            <option value="ambos">Ambos</option>
          </select>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Horário de postagem</label>
          <input
            name="horario_postagem"
            type="time"
            value={values.horario_postagem}
            onChange={onChange}
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Vídeos por semana</label>
          <input
            name="frequencia_semanal"
            type="number"
            min={1}
            max={7}
            value={values.frequencia_semanal}
            onChange={onChange}
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
        </div>
      </div>
    </div>
  )
}

/* --- Icons --- */

function YoutubeIcon() {
  return (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
      <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  )
}

function InstagramIcon() {
  return (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
    </svg>
  )
}

function TelegramIcon() {
  return (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
      <path d="M11.944 0A12 12 0 000 12a12 12 0 0012 12 12 12 0 0012-12A12 12 0 0012 0a12 12 0 00-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 01.171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.479.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
    </svg>
  )
}

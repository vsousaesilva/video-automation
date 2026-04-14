import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/authStore'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, loading, error } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    const success = await login(email, password)
    if (success) {
      navigate('/')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <img
            src="/logo.png"
            alt="Usina do Tempo"
            className="mx-auto w-20 h-20 rounded-2xl object-contain bg-white/5 p-2 mb-4 shadow-lg shadow-indigo-900/40"
          />
          <h1 className="text-2xl font-bold text-white">Usina do Tempo</h1>
          <p className="text-gray-400 mt-2">Acesse sua plataforma de marketing</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-800 rounded-xl p-8 shadow-xl">
          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="mb-5">
            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
              E-mail
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="seu@email.com"
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
            />
          </div>

          <div className="mb-6">
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
              Senha
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              placeholder="Mínimo 6 caracteres"
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>

          <div className="flex items-center justify-between mt-4">
            <Link to="/forgot-password" className="text-sm text-indigo-400 hover:text-indigo-300">
              Esqueceu a senha?
            </Link>
            <Link to="/signup" className="text-sm text-indigo-400 hover:text-indigo-300">
              Criar conta
            </Link>
          </div>
        </form>

        <p className="text-center text-gray-500 text-xs mt-6">
          <Link to="/termos" className="hover:text-gray-400">Termos de Uso</Link>
          {' | '}
          <Link to="/privacidade" className="hover:text-gray-400">Privacidade</Link>
        </p>
      </div>
    </div>
  )
}

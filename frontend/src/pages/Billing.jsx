import { useState, useEffect } from 'react'
import api from '../lib/api'

const PLAN_COLORS = {
  free: 'gray',
  starter: 'blue',
  pro: 'indigo',
  enterprise: 'purple',
}

export default function Billing() {
  const [plans, setPlans] = useState([])
  const [subscription, setSubscription] = useState(null)
  const [usage, setUsage] = useState(null)
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [checkoutLoading, setCheckoutLoading] = useState(null)
  const [cancelLoading, setCancelLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [plansRes, subRes, usageRes, invoicesRes] = await Promise.all([
        api.get('/billing/plans'),
        api.get('/billing/subscription'),
        api.get('/billing/usage'),
        api.get('/billing/invoices'),
      ])
      setPlans(plansRes.data)
      setSubscription(subRes.data)
      setUsage(usageRes.data)
      setInvoices(invoicesRes.data)
    } catch (err) {
      console.error('Erro ao carregar dados de billing:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCheckout = async (planSlug) => {
    setCheckoutLoading(planSlug)
    try {
      const res = await api.post('/billing/checkout', { plan_slug: planSlug })
      if (res.data.checkout_url) {
        window.open(res.data.checkout_url, '_blank')
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao gerar checkout')
    } finally {
      setCheckoutLoading(null)
    }
  }

  const handleCancel = async () => {
    if (!confirm('Tem certeza que deseja cancelar sua assinatura? Você perderá acesso ao final do período atual.')) {
      return
    }
    setCancelLoading(true)
    try {
      await api.post('/billing/cancel')
      await loadData()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao cancelar assinatura')
    } finally {
      setCancelLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="h-40 bg-gray-200 rounded" />
          <div className="h-60 bg-gray-200 rounded" />
        </div>
      </div>
    )
  }

  const currentPlan = plans.find((p) => p.slug === subscription?.plan_slug) || {}

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Plano e Cobrança</h1>

      {/* Current Plan Card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-lg font-semibold text-gray-900">
                Plano {currentPlan.nome || 'Desconhecido'}
              </h2>
              <PlanBadge status={subscription?.status} />
            </div>
            <p className="text-gray-500 text-sm">
              {subscription?.status === 'trial'
                ? `Trial gratuito até ${formatDate(subscription?.trial_end)}`
                : subscription?.status === 'ativa'
                ? 'Assinatura ativa'
                : subscription?.status === 'cancelada'
                ? 'Cancelada — acesso até o fim do período'
                : 'Sem assinatura ativa'}
            </p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-gray-900">
              {currentPlan.preco_mensal
                ? `R$ ${currentPlan.preco_mensal}`
                : 'Grátis'}
            </p>
            {currentPlan.preco_mensal > 0 && (
              <p className="text-gray-400 text-sm">/mês</p>
            )}
          </div>
        </div>

        {subscription?.status === 'ativa' && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <button
              onClick={handleCancel}
              disabled={cancelLoading}
              className="text-sm text-red-500 hover:text-red-600 disabled:text-red-300"
            >
              {cancelLoading ? 'Cancelando...' : 'Cancelar assinatura'}
            </button>
          </div>
        )}
      </div>

      {/* Usage */}
      {usage && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Uso do mês</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <UsageCard
              label="Vídeos gerados"
              value={usage.videos_gerados || 0}
              limit={currentPlan.limite_videos_mes}
            />
            <UsageCard
              label="Negócios"
              value={usage.negocios_count || 0}
              limit={currentPlan.limite_negocios}
            />
            <UsageCard
              label="Tokens IA"
              value={formatNumber(usage.tokens_ia || 0)}
              limit={currentPlan.limite_tokens_ia ? formatNumber(currentPlan.limite_tokens_ia) : null}
            />
            <UsageCard
              label="Armazenamento"
              value={formatSize(usage.storage_bytes || 0)}
              limit={currentPlan.limite_storage_gb ? `${currentPlan.limite_storage_gb} GB` : null}
            />
          </div>
        </div>
      )}

      {/* Plans Grid */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Planos disponíveis</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map((plan) => {
            const isCurrent = plan.slug === subscription?.plan_slug
            const color = PLAN_COLORS[plan.slug] || 'gray'

            return (
              <div
                key={plan.slug}
                className={`rounded-xl border-2 p-5 transition ${
                  isCurrent
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <h3 className="text-sm font-semibold text-gray-900 mb-1">{plan.nome}</h3>
                <p className="text-2xl font-bold text-gray-900 mb-3">
                  {plan.preco_mensal ? `R$ ${plan.preco_mensal}` : 'Grátis'}
                  {plan.preco_mensal > 0 && (
                    <span className="text-sm font-normal text-gray-400">/mês</span>
                  )}
                </p>

                <ul className="text-sm text-gray-600 space-y-1 mb-4">
                  <li>{plan.limite_videos_mes ?? 'Ilimitados'} vídeos/mês</li>
                  <li>{plan.limite_negocios ?? 'Ilimitados'} negócios</li>
                  {plan.modulos_disponiveis?.map((mod) => (
                    <li key={mod} className="capitalize">{mod.replace('_', ' ')}</li>
                  ))}
                </ul>

                {isCurrent ? (
                  <span className="block text-center text-sm text-indigo-600 font-medium py-2">
                    Plano atual
                  </span>
                ) : plan.slug === 'enterprise' ? (
                  <a
                    href="mailto:contato@usinadotempo.com.br"
                    className="block text-center text-sm bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 rounded-lg transition"
                  >
                    Falar com vendas
                  </a>
                ) : plan.slug !== 'free' ? (
                  <button
                    onClick={() => handleCheckout(plan.slug)}
                    disabled={checkoutLoading === plan.slug}
                    className="w-full text-sm bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium py-2 rounded-lg transition"
                  >
                    {checkoutLoading === plan.slug ? 'Gerando...' : 'Assinar'}
                  </button>
                ) : null}
              </div>
            )
          })}
        </div>
      </div>

      {/* Invoices */}
      {invoices.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Faturas</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-2 font-medium">Data</th>
                  <th className="pb-2 font-medium">Plano</th>
                  <th className="pb-2 font-medium">Valor</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td className="py-3 text-gray-900">{formatDate(inv.data_vencimento)}</td>
                    <td className="py-3 text-gray-600">{inv.plan_slug || '-'}</td>
                    <td className="py-3 text-gray-900">R$ {inv.valor}</td>
                    <td className="py-3">
                      <InvoiceStatusBadge status={inv.status} />
                    </td>
                    <td className="py-3">
                      {inv.url_boleto && (
                        <a
                          href={inv.url_boleto}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 hover:text-indigo-700"
                        >
                          Ver fatura
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

/* --- Helper Components --- */

function PlanBadge({ status }) {
  const map = {
    trial: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Trial' },
    ativa: { bg: 'bg-green-100', text: 'text-green-800', label: 'Ativa' },
    cancelada: { bg: 'bg-red-100', text: 'text-red-800', label: 'Cancelada' },
    inadimplente: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Inadimplente' },
  }
  const badge = map[status] || { bg: 'bg-gray-100', text: 'text-gray-600', label: status || '-' }

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
      {badge.label}
    </span>
  )
}

function InvoiceStatusBadge({ status }) {
  const map = {
    paga: { bg: 'bg-green-100', text: 'text-green-800' },
    pendente: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    vencida: { bg: 'bg-red-100', text: 'text-red-800' },
  }
  const badge = map[status] || { bg: 'bg-gray-100', text: 'text-gray-600' }

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${badge.bg} ${badge.text}`}>
      {status || '-'}
    </span>
  )
}

function UsageCard({ label, value, limit }) {
  return (
    <div className="p-3 bg-gray-50 rounded-lg">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-gray-900">
        {value}
        {limit && <span className="text-sm font-normal text-gray-400"> / {limit}</span>}
      </p>
    </div>
  )
}

/* --- Helpers --- */

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('pt-BR')
}

function formatNumber(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`
  return String(n)
}

function formatSize(bytes) {
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(1)} GB`
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(0)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}

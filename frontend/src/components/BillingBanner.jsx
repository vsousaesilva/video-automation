import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

export default function BillingBanner() {
  const [subscription, setSubscription] = useState(null)
  const [usage, setUsage] = useState(null)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    const fetchBillingData = async () => {
      try {
        const [subRes, usageRes] = await Promise.all([
          api.get('/billing/subscription'),
          api.get('/billing/usage'),
        ])
        setSubscription(subRes.data)
        setUsage(usageRes.data)
      } catch {
        // Silently fail — billing may not be configured
      }
    }
    fetchBillingData()
  }, [])

  if (dismissed || !subscription) return null

  const plan = subscription.plans
  const status = subscription.status

  // Banner de plano expirado/inadimplente
  if (status === 'past_due') {
    return (
      <div className="bg-red-600 text-white px-4 py-3 flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <WarningIcon />
          <span>
            <strong>Pagamento pendente.</strong> Regularize sua assinatura para evitar restrição de acesso.
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/settings/billing" className="underline font-medium hover:text-red-100">
            Ver fatura
          </Link>
          <button onClick={() => setDismissed(true)} className="text-red-200 hover:text-white">
            <CloseIcon />
          </button>
        </div>
      </div>
    )
  }

  if (status === 'canceled' || status === 'expired') {
    return (
      <div className="bg-orange-500 text-white px-4 py-3 flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <WarningIcon />
          <span>
            <strong>Assinatura cancelada.</strong> Você está no plano gratuito com funcionalidades limitadas.
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/settings/billing" className="underline font-medium hover:text-orange-100">
            Reativar plano
          </Link>
          <button onClick={() => setDismissed(true)} className="text-orange-200 hover:text-white">
            <CloseIcon />
          </button>
        </div>
      </div>
    )
  }

  // Aviso de trial expirando
  if (status === 'trial' && subscription.trial_ends_at) {
    const trialEnd = new Date(subscription.trial_ends_at)
    const daysLeft = Math.ceil((trialEnd - Date.now()) / (1000 * 60 * 60 * 24))
    if (daysLeft <= 3 && daysLeft > 0) {
      return (
        <div className="bg-amber-500 text-white px-4 py-3 flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <InfoIcon />
            <span>
              Seu período de teste expira em <strong>{daysLeft} {daysLeft === 1 ? 'dia' : 'dias'}</strong>.
              Escolha um plano para continuar usando todos os recursos.
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/settings/billing" className="underline font-medium hover:text-amber-100">
              Ver planos
            </Link>
            <button onClick={() => setDismissed(true)} className="text-amber-200 hover:text-white">
              <CloseIcon />
            </button>
          </div>
        </div>
      )
    }
  }

  // Aviso de proximidade do limite de uso
  if (plan && usage) {
    const limits = [
      { usage: usage.videos_gerados, max: plan.max_videos_mes, label: 'videos' },
    ]

    for (const { usage: used, max, label } of limits) {
      if (max && used >= max * 0.8 && used < max) {
        return (
          <div className="bg-blue-600 text-white px-4 py-3 flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <InfoIcon />
              <span>
                Você usou <strong>{used}/{max}</strong> {label} do seu plano este mês.
                Considere fazer upgrade para mais capacidade.
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/settings/billing" className="underline font-medium hover:text-blue-100">
                Upgrade
              </Link>
              <button onClick={() => setDismissed(true)} className="text-blue-200 hover:text-white">
                <CloseIcon />
              </button>
            </div>
          </div>
        )
      }
      if (max && used >= max) {
        return (
          <div className="bg-red-600 text-white px-4 py-3 flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <WarningIcon />
              <span>
                <strong>Limite atingido:</strong> {used}/{max} {label} usados.
                Faça upgrade para continuar gerando conteúdo.
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/settings/billing" className="underline font-medium hover:text-red-100">
                Upgrade
              </Link>
              <button onClick={() => setDismissed(true)} className="text-red-200 hover:text-white">
                <CloseIcon />
              </button>
            </div>
          </div>
        )
      }
    }
  }

  return null
}

function WarningIcon() {
  return (
    <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
    </svg>
  )
}

function InfoIcon() {
  return (
    <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}
